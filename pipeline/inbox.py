"""Pull update bundles from the Google Drive inbox into the repo (runs before publishing, once a day).

Claude's scheduled sessions put .zip bundles into the Drive folder named in config/inbox.json. Each bundle holds
repo-relative files (content/<channel>/<slug>/*.json, content/<channel>/queue.json, pipeline/*.py, assets/...).
Optional DELETE.txt inside a bundle lists repo paths to remove (one per line).

Safety rules, so a bad bundle can never break publishing:
- only these paths are accepted: content/ pipeline/ assets/ channels/ music/ config/ practice/ and a few root files;
  never .github/ or state/; no absolute paths, no "..", no links; at most 40 MB unpacked.
- content/<channel>/queue.json is MERGED (new scripts added, unpublished dates updated), never overwritten.
- after applying: every JSON must parse, every Python file must compile, every queued script must exist and
  `publish.py --check` must run for every channel. Otherwise the bundle is rolled back and marked rejected.
- every file is processed once (state/inbox.json keeps its id + checksum); a rejected bundle turns the run red once,
  so GitHub emails the owner, and is not retried until a fixed copy is uploaded.

Env: GDRIVE_SA_JSON (service account key; the inbox folder is shared with its email), or the fallback
GDRIVE_REFRESH_TOKEN with YT_CLIENT_ID and YT_CLIENT_SECRET. See pipeline/drive_auth.py.
Without either it prints a note and exits 0.
Usage: python pipeline/inbox.py [--dry-run] [--local some.zip]
"""
import argparse
import datetime as dt
import io
import json
import os
import py_compile
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

import requests

sys.path.insert(0, str(Path(__file__).parent))
import drive_auth  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config" / "inbox.json"
STATE = ROOT / "state" / "inbox.json"
ALLOWED_DIRS = ("content/", "pipeline/", "assets/", "channels/", "music/", "config/", "practice/")
ALLOWED_FILES = {"README.md", "QUALITY.md", "RUNBOOK.md", "requirements.txt", "package.json", "package-lock.json"}
MAX_BYTES = 40 * 1024 * 1024


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True).stdout


def allowed(path):
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        return False
    s = str(p)
    return s in ALLOWED_FILES or s.startswith(ALLOWED_DIRS)


def drive_token():
    return drive_auth.access_token()


def list_bundles(token, folder):
    h = {"Authorization": f"Bearer {token}"}
    files, page = [], None
    while True:
        r = requests.get("https://www.googleapis.com/drive/v3/files", headers=h, timeout=30, params={
            "q": f"'{folder}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,md5Checksum,mimeType,createdTime,size)",
            "orderBy": "createdTime", "pageSize": 100, **({"pageToken": page} if page else {})})
        r.raise_for_status()
        js = r.json()
        files += js.get("files", [])
        page = js.get("nextPageToken")
        if not page:
            return [f for f in files if f["name"].lower().endswith(".zip")]


def download(token, fid):
    r = requests.get(f"https://www.googleapis.com/drive/v3/files/{fid}", params={"alt": "media"},
                     headers={"Authorization": f"Bearer {token}"}, timeout=300)
    r.raise_for_status()
    return r.content


def merge_queue(path, incoming):
    """Union by script path; the bundle's date wins for items not published yet."""
    published = set()
    sp = ROOT / "state" / "published.json"
    if sp.exists():
        published = {x["id"] for x in json.loads(sp.read_text())}
    cur = json.loads(path.read_text()) if path.exists() else []
    by = {q["script"]: q for q in cur}
    for q in incoming:
        old = by.get(q["script"])
        sid = None
        try:
            sid = json.loads((ROOT / q["script"]).read_text())["id"]
        except Exception:  # noqa: BLE001 - checked later by validate()
            pass
        if old is None:
            by[q["script"]] = q
        elif sid not in published:
            old.update(q)
    out = sorted(by.values(), key=lambda q: (q["date"], q["kind"] != "long"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n")


def apply(data):
    """Write the bundle into the work tree. Returns the list of touched paths. Raises on a rule violation."""
    z = zipfile.ZipFile(io.BytesIO(data))
    members = [m for m in z.infolist() if not m.is_dir() and not m.filename.startswith("__MACOSX/")]
    if sum(m.file_size for m in members) > MAX_BYTES:
        raise ValueError("bundle is larger than 40 MB unpacked")
    deletes = []
    for m in members:
        if stat.S_ISLNK(m.external_attr >> 16):
            raise ValueError(f"link not allowed: {m.filename}")
        if m.filename == "DELETE.txt":
            deletes = [ln.strip() for ln in z.read(m).decode().splitlines() if ln.strip() and not ln.startswith("#")]
            continue
        if not allowed(m.filename):
            raise ValueError(f"path not allowed: {m.filename}")
    for d in deletes:
        if not allowed(d):
            raise ValueError(f"delete not allowed: {d}")
    touched, queues = [], []
    for m in members:
        if m.filename == "DELETE.txt":
            continue
        if PurePosixPath(m.filename).name == "queue.json" and m.filename.startswith("content/"):
            queues.append(m)
            continue
        dst = ROOT / m.filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(z.read(m))
        touched.append(m.filename)
    for q in queues:  # after the scripts, so merge_queue can read their ids
        merge_queue(ROOT / q.filename, json.loads(z.read(q)))
        touched.append(q.filename)
    for d in deletes:
        p = ROOT / d
        if p.is_file():
            p.unlink()
            touched.append(d)
    return touched


def validate(touched):
    errs = []
    for t in touched:
        p = ROOT / t
        if not p.exists():
            continue
        if t.endswith(".json"):
            try:
                json.loads(p.read_text())
            except Exception as e:  # noqa: BLE001
                errs.append(f"{t}: bad JSON ({e})")
        elif t.endswith(".py"):
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                errs.append(f"{t}: does not compile ({e.msg.strip()[:200]})")
    for qp in (ROOT / "content").glob("*/queue.json"):
        try:
            for q in json.loads(qp.read_text()):
                s = ROOT / q["script"]
                if not s.exists():
                    errs.append(f"{qp.relative_to(ROOT)}: script missing {q['script']}")
                else:
                    js = json.loads(s.read_text())
                    if not js.get("id") or not js.get("channel"):
                        errs.append(f"{q['script']}: needs id and channel")
                dt.date.fromisoformat(q["date"])
                if q["kind"] not in ("long", "short"):
                    errs.append(f"{q['script']}: kind must be long or short")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{qp.relative_to(ROOT)}: {e}")
    if not errs:
        env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
        for cfg in sorted((ROOT / "channels").glob("*.json")):
            r = subprocess.run([sys.executable, "pipeline/publish.py", "--channel", cfg.stem, "--check"], cwd=ROOT,
                               capture_output=True, text=True, env=env)
            if r.returncode:
                errs.append(f"publish.py --check {cfg.stem} failed: {(r.stderr or r.stdout).strip()[-300:]}")
    return errs


def rollback(touched):
    tracked = set(git("ls-files").split("\n"))
    for t in touched:
        if t in tracked:
            git("checkout", "--", t, check=False)
        else:
            (ROOT / t).unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="apply and validate, then roll back; no commit")
    ap.add_argument("--local", help="test a local .zip instead of reading Drive")
    a = ap.parse_args()

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if a.local:
        bundles = [{"id": "local", "name": Path(a.local).name, "md5Checksum": "local", "data": Path(a.local).read_bytes()}]
        token = None
    else:
        if not drive_auth.configured():
            print("inbox: no Drive key set (GDRIVE_SA_JSON), skipping (scripts arrive by manual upload)")
            return 0
        folder = json.loads(CFG.read_text())["folder_id"]
        token = drive_token()
        bundles = list_bundles(token, folder)
    failed = []
    for b in bundles:
        seen = state.get(b["id"])
        if seen and seen.get("md5") == b.get("md5Checksum"):
            continue
        data = b.get("data") or download(token, b["id"])
        touched = []
        try:
            touched = apply(data)
            errs = validate(touched)
        except Exception as e:  # noqa: BLE001
            errs = [str(e)]
        if errs or a.dry_run:
            rollback(touched)
        if errs:
            failed.append(b["name"])
            result = "rejected: " + "; ".join(errs)[:900]
        else:
            result = "applied" if not a.dry_run else "ok (dry run, rolled back)"
        print(f"inbox: {b['name']}: {result}")
        if a.dry_run or a.local:
            continue
        if not errs:
            git("add", "-A", "--", *touched)
            git("commit", "-q", "-m", f"Inbox: {b['name']}")
        state[b["id"]] = {"name": b["name"], "md5": b.get("md5Checksum"), "result": result,
                          "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1) + "\n")
        git("add", str(STATE.relative_to(ROOT)))
        git("commit", "-q", "-m", f"Inbox log: {b['name']}", check=False)
    if failed:
        print("inbox: rejected " + ", ".join(failed) + " (see state/inbox.json)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

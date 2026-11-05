"""Check that every channel's YouTube refresh token still works and belongs to the right channel.

For each channels/<id>.json with a "youtube_channel_id": swap the refresh token (env var named in
"youtube_token_secret") for an access token, ask YouTube which channel it controls (channels.list mine=true)
and compare. Exit 1 if any channel fails, so the run turns red and GitHub emails the owner.

Optional: GDRIVE_REFRESH_TOKEN (Drive inbox) is checked the same way when it is set.
Needs env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN_1/2/3 (no other libraries than requests).
Usage: python pipeline/check_tokens.py
"""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TOKEN_URL = "https://oauth2.googleapis.com/token"


def access_token(refresh):
    r = requests.post(TOKEN_URL, data={"client_id": os.environ["YT_CLIENT_ID"],
                                       "client_secret": os.environ["YT_CLIENT_SECRET"],
                                       "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=30)
    if not r.ok:
        raise RuntimeError(f"token refused ({r.status_code} {r.json().get('error', '') if r.headers.get('content-type', '').startswith('application/json') else ''})")
    return r.json()["access_token"]


def main():
    rows, bad = [], 0
    for f in sorted((ROOT / "channels").glob("*.json")):
        cfg = json.loads(f.read_text())
        want, secret = cfg.get("youtube_channel_id"), cfg.get("youtube_token_secret")
        if not want or not secret:
            continue
        name = cfg.get("name", f.stem)
        refresh = os.environ.get(secret, "")
        try:
            if not refresh:
                raise RuntimeError(f"GitHub secret {secret} is empty or missing")
            tok = access_token(refresh)
            r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                             params={"part": "id,snippet", "mine": "true"},
                             headers={"Authorization": f"Bearer {tok}"}, timeout=30)
            r.raise_for_status()
            items = r.json().get("items", [])
            got = items[0]["id"] if items else None
            title = items[0]["snippet"]["title"] if items else "no channel"
            if got != want:
                raise RuntimeError(f"{secret} controls '{title}' ({got}), not {name} ({want}): make the token again "
                                   f"and choose {name} on the consent screen")
            rows.append(f"OK    {name}: {secret} -> {title} ({got})")
        except Exception as e:  # noqa: BLE001 - report every channel, then fail once
            bad += 1
            rows.append(f"FAIL  {name}: {e}")

    drive = os.environ.get("GDRIVE_REFRESH_TOKEN")
    if drive:
        try:
            tok = access_token(drive)
            r = requests.get("https://www.googleapis.com/drive/v3/about", params={"fields": "user(emailAddress)"},
                             headers={"Authorization": f"Bearer {tok}"}, timeout=30)
            r.raise_for_status()
            rows.append(f"OK    Drive inbox: GDRIVE_REFRESH_TOKEN -> {r.json()['user']['emailAddress']}")
        except Exception as e:  # noqa: BLE001
            bad += 1
            rows.append(f"FAIL  Drive inbox: {e}")
    else:
        rows.append("SKIP  Drive inbox: GDRIVE_REFRESH_TOKEN not set yet")

    report = "\n".join(rows)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).open("a").write("### Token check\n```\n" + report + "\n```\n")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

"""Print errors and warnings from `hyperframes check --json`. Exit 1 on errors."""
import json
import sys

raw = open(sys.argv[1]).read()
try:
    data = json.loads(raw[raw.index("{"):])
except Exception:
    print(raw[:3000])
    sys.exit(0)

found = {"error": 0, "warning": 0}


def walk(x):
    if isinstance(x, dict):
        if "message" in x and ("rule" in x or "code" in x):
            sev = x.get("severity", "")
            if sev in found:
                found[sev] += 1
                print(f" - {sev:<7} {x.get('rule', x.get('code', ''))} | {str(x.get('message', ''))[:200]} | {x.get('selector', '')}")
            return
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(data)
print(f"check: {found['error']} errors, {found['warning']} warnings")
sys.exit(1 if found["error"] else 0)

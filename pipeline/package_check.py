"""Lint a title + thumbnail pair (rules from the faceless-channel-playbook skill).
Usage: python package_check.py "Title" "THUMB WORDS" ["Title 2" "THUMB 2" ...]"""
import re
import sys

STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "for", "its", "it", "is", "why", "how", "what", "never", "s"}


def check(title, thumb):
    issues, score = [], 100
    n = len(title)
    if n > 60:
        issues.append(f"title {n} chars > 60 (cut on desktop search)"); score -= 25
    elif n > 40:
        issues.append(f"title {n} chars > 40 (tail cut on mobile feed)"); score -= 8
    caps = [w for w in re.findall(r"[A-Za-z']+", title) if len(w) > 1 and w.isupper()]
    if len(caps) > 2:
        issues.append(f"{len(caps)} all-caps words (max 2)"); score -= 15
    if not re.search(r"\d|\$|\b[A-Z][A-Za-z]+'s\b|\b[A-Z]{2,}\b|\b(19|20)\d\d\b", title):
        issues.append("no number, name or date"); score -= 15
    tw = [w for w in re.findall(r"[A-Za-z0-9$.']+", thumb) if w]
    if len(tw) > 3:
        issues.append(f"thumbnail has {len(tw)} words (max 3)"); score -= 20
    tset = {w.lower().strip(".'") for w in tw} - STOP
    ttitle = {w.lower().strip(".'").removesuffix("'s") for w in re.findall(r"[A-Za-z0-9$.']+", title)} - STOP
    rep = tset & ttitle
    if rep:
        issues.append(f"thumbnail repeats the title: {', '.join(sorted(rep))}"); score -= 20
    return max(score, 0), issues


if __name__ == "__main__":
    args = sys.argv[1:]
    rows = [(args[i], args[i + 1]) for i in range(0, len(args) - 1, 2)]
    for t, th in sorted(rows, key=lambda r: -check(*r)[0]):
        s, iss = check(t, th)
        print(f"{s:3d}  {t!r} + [{th}]  {'; '.join(iss) or 'clean'}")

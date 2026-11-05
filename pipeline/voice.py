"""Voiceover: script JSON -> assets/voice.wav + timeline.json.

Narration markup: plain words are shown and spoken as-is.
"{display|spoken}" shows `display` in captions/visual cues but speaks `spoken`.
Example: "It costs {$1.50|a dollar fifty} since {1985|nineteen eighty-five}."

Each sentence is synthesised separately (natural prosody, exact sentence
boundaries). Word times inside a sentence are estimated from spoken length,
with extra weight for commas and full stops.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
LEAD_IN = 0.12        # silence before the first word (the hook starts at once)
SENT_GAP = 0.12       # breath between sentences
SCENE_GAP = 0.18      # breath between scenes
# extra hold after a scene's last word. Kept short (v2): the owner heard the old 1-2.7 s holds as
# "voids". Visual payoffs land on their cue word instead of waiting for silence.
TAIL = {"counter": 0.12, "compare": 0.18, "bars": 0.18, "share": 0.12, "dots": 0.12, "cards": 0.12,
        "pricetag": 0.08, "years": 0.1, "flow": 0.12, "quote": 0.6, "statement": 0.05, "lines": 0.12,
        "chapter": 0.3, "end": 1.1, "cta": 0.08, "shot": 0.05}
FADE_IN, FADE_OUT = 0.008, 0.03   # seconds; no clicks, no chopped word endings
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"

TOKEN_RE = re.compile(r"\{([^|}]+)\|([^}]+)\}|(\S+)")


def tokenize(narration):
    """-> list of (display, spoken) word tokens."""
    out = []
    for m in TOKEN_RE.finditer(narration):
        if m.group(3) is not None:
            w = m.group(3)
            out.append((w, w))
        else:
            disp, spoken = m.group(1).strip(), m.group(2).strip()
            # trailing punctuation right after the braces belongs to display
            out.append((disp, spoken))
    # glue punctuation that followed a {..} token, e.g. "{$1.50|...}."
    fixed = []
    for disp, spoken in out:
        if fixed and re.fullmatch(r"[.,!?;:]+", disp):
            d0, s0 = fixed[-1]
            fixed[-1] = (d0 + disp, s0 + disp)
        else:
            fixed.append((disp, spoken))
    return fixed


def split_sentences(tokens):
    sents, cur = [], []
    for tok in tokens:
        cur.append(tok)
        if re.search(r"[.!?][\"')\]]*$", tok[0]):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    return sents


def trim(samples, thresh=0.004, pad=0.06):
    """Gentle trim: only true silence goes, soft word endings stay (the old 0.012 cut them)."""
    idx = np.where(np.abs(samples) > thresh)[0]
    if len(idx) == 0:
        return samples
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(samples), idx[-1] + int(pad * SR))
    out = samples[a:b].copy()
    fi, fo = int(FADE_IN * SR), int(FADE_OUT * SR)
    if len(out) > fi + fo:
        out[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
        out[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    return out


def squeeze_pauses(samples, max_pause=0.42, thresh=0.004):
    """Shorten any pause inside a sentence that is longer than max_pause (model hesitations)."""
    quiet = np.abs(samples) < thresh
    out, i, n = [], 0, len(samples)
    lim = int(max_pause * SR)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            seg = samples[i:j]
            out.append(seg if len(seg) <= lim else np.concatenate([seg[:lim // 2], seg[-lim // 2:]]))
            i = j
        else:
            j = i
            while j < n and not quiet[j]:
                j += 1
            out.append(samples[i:j])
            i = j
    return np.concatenate(out) if out else samples


def _norm(w):
    return re.sub(r"[^a-z0-9$%.]", "", w.lower()).strip(".")


def read_holds(data, words, delay=0.0):
    """(cue time, seconds needed to read the text it reveals) for every cued text in the scene data.
    Rule from the lint: about 0.5 s + 0.3 s a word, capped at 2.6 s."""
    pairs = []

    def walk(o):
        if isinstance(o, dict):
            txt = o.get("text") or o.get("label") or o.get("title") or o.get("big") or o.get("price") or o.get("display")
            if o.get("cue") and isinstance(txt, str):
                pairs.append((o["cue"], txt))
            if o.get("label_cue") and isinstance(o.get("label"), str):
                pairs.append((o["label_cue"], o["label"]))
            if o.get("sub_cue") and isinstance(o.get("sub"), str):
                pairs.append((o["sub_cue"], o["sub"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data or {})
    out = []
    for cue, txt in pairs:
        n = _norm(cue)
        for w in words:
            wn = _norm(w["text"])
            if wn and (wn.startswith(n) or n in wn):
                nw = len(re.sub(r"[*]", "", txt).split())
                out.append((w["start"] + delay, min(2.6, 0.5 + 0.3 * nw)))
                break
    return out


def word_weights(tokens):
    ws = []
    for disp, spoken in tokens:
        w = len(re.sub(r"[^A-Za-z0-9]", "", spoken)) + 2.0
        if re.search(r"[,;:]$", spoken):
            w += 5.0
        ws.append(w)
    return ws


def main(script_path, out_dir):
    from kokoro_onnx import Kokoro

    script = json.loads(Path(script_path).read_text())
    out_dir = Path(out_dir)
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    voice = script.get("voice", "am_michael")
    speed = float(script.get("speed", 1.0))

    pieces = [np.zeros(int(LEAD_IN * SR), dtype=np.float32)]
    t = LEAD_IN
    scenes_out = []
    for i, scene in enumerate(script["scenes"]):
        sid = f"s{i + 1:02d}"
        scene_start = t if i else 0.0
        words = []
        tokens = tokenize(scene["narration"])
        sents = split_sentences(tokens)
        for k, sent in enumerate(sents):
            text = " ".join(s for _, s in sent)
            audio, sr = kokoro.create(text, voice=voice, speed=speed, lang="en-us", trim=True,
                                      sentence_pause=0.2, clause_pause=0.08)
            assert sr == SR
            audio = trim(squeeze_pauses(np.asarray(audio, dtype=np.float32)))
            dur = len(audio) / SR
            ws = word_weights(sent)
            total = sum(ws)
            acc = 0.0
            for (disp, _), w in zip(sent, ws):
                ws_t = t + dur * acc / total
                acc += w
                we_t = t + dur * acc / total
                words.append({"text": disp, "start": round(ws_t - scene_start, 3),
                              "end": round(we_t - scene_start, 3)})
            pieces.append(audio)
            t += dur
            if k < len(sents) - 1:
                pieces.append(np.zeros(int(SENT_GAP * SR), dtype=np.float32))
                t += SENT_GAP
        min_d = float(scene.get("min_duration", 0))
        pad = SCENE_GAP + float(scene.get("hold", TAIL.get(scene["type"], 0.4)))
        # hold just long enough for the last revealed text to be read (no fixed long tails)
        for cue_t, need in read_holds(scene.get("data"), words, .7 if scene["type"] == "lines" else 0.0):
            short = (cue_t + need) - (t - scene_start + pad)
            if short > 0:
                pad += min(short, 1.6)
        if t + pad - scene_start < min_d:
            pad = min_d - (t - scene_start)
        pieces.append(np.zeros(int(pad * SR), dtype=np.float32))
        t += pad
        scenes_out.append({"id": sid, "type": scene["type"], "start": round(scene_start, 3),
                           "duration": round(t - scene_start, 3), "words": words})
        print(f"{sid} {scene['type']:<10} {t - scene_start:6.2f}s", flush=True)

    voice_wav = np.concatenate(pieces)
    peak = float(np.max(np.abs(voice_wav))) or 1.0
    voice_wav = voice_wav * (0.89 / peak)  # about -1 dBFS peak
    sf.write(out_dir / "assets" / "voice.wav", voice_wav, SR)
    timeline = {"total": round(t, 3), "scenes": scenes_out}
    (out_dir / "timeline.json").write_text(json.dumps(timeline, indent=1))
    print(f"total {t:.2f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

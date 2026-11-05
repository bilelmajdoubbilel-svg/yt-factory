# Quality scorecard

Scored by Claude against the faceless-channel-playbook and cinematic-explainer rules, by reading
frames and measuring audio (the model cannot watch or listen). 1 = poor, 5 = top channel level.
Re-score after every batch; real retention and click-through data replace guesses once videos are live.

## Batch 1: Costco (1 long + 5 Shorts), 5 Nov 2026

| # | Area | v1 (4 Nov) | v2 (5 Nov) | What v2 does / what's missing |
|---|------|-----------:|-----------:|------------------------------|
| 1 | Hook, first 15 s | 3 | 4 | Before/after hook + statistic, open loop to "$5B business"; Shorts readable on frame 0 |
| 2 | Visual interest | 1 | 4 | Host in every scene, 4 worlds, moving multiplane camera, depth of field, grade, grain. Missing: more story shots (host doing things), secondary characters |
| 3 | Pacing / interrupts | 2 | 3.5 | World change or camera change every 7-10 s, 5 transition types. Some scenes still 10-13 s on one idea |
| 4 | Accuracy and sources | 5 | 5 | Every number sourced (10-K first), estimates labelled, sources in description |
| 5 | Sound | 1 | 3.5 | CC0 music ducked under voice (music ~13 dB under), effects on cuts and landings, master -14 LUFS. Synthetic voice |
| 6 | Readability | 4 | 4 | Dark backdrop behind text in busy worlds; source lines enlarged |
| 7 | Consistency / brand | 2 | 4 | Same host, palette, worlds; profile picture and banner made |
| 8 | Packaging | 3 | 4 | Title linted (32 chars), thumbnail with host, no repeated words. No CTR data yet |
| 9 | Shorts | 2 | 4 | 18-25 s, hook frame 0, burned captions, host, each with a new first line |
| 10 | Production speed | 4 | 3 | Backgrounds now pre-rendered (baked): Short 7m44s -> 2m49s (2.75x faster, PSNR 42.6 dB vs the live version = no visible change) |

**Overall: v1 2.7 / 5 → v2 3.9 / 5.** Publishable as episode 1; still below the top animated channels.

### Review of the final render (5 Nov, 01:30)
Found and fixed before delivery: chart labels and on-screen source lines were hidden under the stage
floor in every stage scene (layer order), source lines were cut at the left edge when the host stood
on the right, a 4-step flow ran off the left edge, small labels were under the 28 px phone floor.
Loudness -14.2 LUFS, true peak -1.2 dBFS. Lint: 0 errors.

## Next improvements, in order

1. **Story shots**: 30-40% of scenes should be the host doing something in a place (buying, carrying,
   walking past shelves, a crowd of members), not "host beside a chart".
2. ~~Pre-rendered blurred backgrounds~~ done 5 Nov: 2.75x faster.
3. **Split long scenes**: no single beat over ~8 s without a new visual event.
4. **Secondary characters**: cashier, crowd silhouettes, a second host colour for "the company".
5. **Data loop**: after 3 uploads, read retention and click-through (needs the YouTube Analytics
   read-only permission) and tune hooks, length and pacing from real numbers.
6. **Voice**: test the 5 narrator samples with the owner; keep one per channel.
7. **Shorts framing**: the lower ~40% of each Short is empty floor; make the host bigger and lower
   (keep the bottom 20% clear for YouTube's buttons).

## Batch 2: Popcorn (scripts only so far), 5 Nov 2026

- Long script 608 words (~4.3 min), 30 scenes, 4 chapters; 3 primary sources (AMC FY2025 and FY2019
  releases, Cinemark FY2025 release) plus Smithsonian for the history chapter.
- Applied from batch 1: a "turn" line at 0:15 that promises three payoffs, an open loop paid off in
  chapter 3 (why cinemas once refused popcorn), an ending that rhymes with the history, a second
  company (Cinemark) so the point is not one company's quirk.
- Packaging: "Why AMC Needs Your Popcorn Money" + thumbnail "48% TO HOLLYWOOD" (lint 100).
- Still to do before render: 2 more story shots (host in a queue at the counter, host with a ticket).

## v3 (5 Nov, after owner feedback: "no real hook, mostly black, voids in the voice")

| Area | v2 | v3 | Change |
|------|---:|---:|--------|
| Hook | 4 | 4.5 | Story cold open (2013 CEO / co-founder threat, sourced), open loop, ending pays it off; frame 0 moves |
| Visual interest | 4 | 4.5 | Lit worlds (mean luma 58 -> 114 of 255), live background motion, secondary characters (passers-by) |
| Sound | 3.5 | 4 | Pauses > 1 s: 30 -> 0; silence 22% -> 15%; no clipped word endings |
| Readability | 4 | 4.5 | Light screen panel in the studio, glass card in Shorts, captions in their own band |
| Production speed | 3 | 2.5 | Moving backgrounds: ~9x real time (long ~36 min) |

Competitor data (vidIQ public pages, 5 Nov): story-led videos on famous everyday businesses are the
outliers (4-20x channel median); cinema economics under-performed (0.4x) -> popcorn moved to week 4 (proposed).

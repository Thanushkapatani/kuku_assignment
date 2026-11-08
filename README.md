# Kuku Promo Finder

A small prototype for **Problem 1: Find the Promos (Ads)**.

## Run
1. Install Python 3.10+.
2. `pip install -r requirements.txt`
3. `streamlit run app.py`
4. Upload the supplied screenplay ZIP. Download JSON/CSV results.

## Method
- Parses timestamped screenplay beats (dialogue, action and camera descriptions).
- Scans overlapping 25–60 second windows.
- Scores windows using explicit lexical signals for an opening hook, emotional intensity and unresolved ending, plus beat density.
- Returns up to three non-near-duplicate candidates per episode, ranked by score.

## Assumptions and limitations
- Timestamps are assumed to be episode-relative seconds in `MM:SS.xx` format.
- A lexical score is a transparent baseline, not a semantic understanding of story context.
- It may miss visual hooks, sarcasm, context-dependent reveals and cross-episode story arcs; it may also over-rank keyword-heavy but weak scenes.
- Human editor review is required before publishing. No claim is made that these candidates are proven high-performing ads.

## AI/tool use
This prototype was developed with ChatGPT assistance for code scaffolding and analysis. The scoring itself is deterministic Python and can be replaced with an LLM-based evaluator behind the same `analyze_episode` interface. One known weakness: keyword matching can mistake words like “why” or “secret” for a strong cliffhanger without understanding the scene.

#!/usr/bin/env python3
"""Splits demo.html into one standalone page per screenshot section.

Chrome's --screenshot captures the viewport, so each page has to be exactly the
size of its section. Heights are measured from the rendered content, which we
can't do without a browser — so they're declared here and checked visually.
Adjust a number if a capture clips.
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
TMP = BASE / "_tmp"
TMP.mkdir(exist_ok=True)

WIDTH = 920                       # 880 content + 20 px margin each side
HEIGHTS = {                       # measured on the rendered page
    "tabs-bar": 78,
    "observations": 585,
    "volume": 400,
    "efficiency": 790,
    "recovery": 1085,
    "shoes": 350,
}

html = (BASE / "demo.html").read_text(encoding="utf-8")
css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)

for m in re.finditer(r'<section id="([\w-]+)" class="shot">(.*?)</section>', html, re.S):
    name, body = m.group(1), m.group(2)
    h = HEIGHTS.get(name, 700)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>{css}
html,body {{ margin:0; padding:0; background:var(--bg-primary); }}
.wrap {{ max-width:{WIDTH - 40}px; margin:0 auto; padding:20px; }}
</style></head><body><!--size:{WIDTH}x{h}--><div class="wrap">{body}</div></body></html>"""
    (TMP / f"{name}.html").write_text(page, encoding="utf-8")

print(f"{len(list(TMP.glob('*.html')))} sections written to {TMP}")

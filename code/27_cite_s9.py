#!/usr/bin/env python3
"""Cite Supplementary Figure S9, which no sentence pointed at.

S9 gives each named proxy's validation rate one by one. The sentence that reports those rates having
no relation to prominence is where a reader would look for them, so the pointer goes there.
"""
import sys, zipfile
from importlib import import_module
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[3])
M = import_module("13_apply_revisions")
W = M.W

NEEDLE = "bootstrap interval −0.37 to 0.09; Figure 7a)."
PAYLOAD = ("bootstrap interval −0.37 to 0.09; Figure 7a), and the rate for each named proxy is "
           "plotted separately in Supplementary Figure S9.")

src, out, track = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[4] == "track"
M.TRACK["on"] = track
M.TRACK["author"] = "Handsome Nyoni"
M.TRACK["date"] = "2026-11-08T00:00:00Z"

with zipfile.ZipFile(src) as z:
    root = ET.fromstring(z.read("word/document.xml"))
body = root.find(W + "body")
hits = [p for p in body.iter(W + "p")
        if NEEDLE in "".join(t.text or "" for t in p.iter(W + "t"))]
if len(hits) != 1:
    sys.exit(f"expected exactly one match, found {len(hits)}")
M.replace_substring(hits[0], NEEDLE, PAYLOAD)
new = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
    for it in zin.infolist():
        zout.writestr(it, new if it.filename == "word/document.xml" else zin.read(it.filename))
print(f"cited S9 in {out.name}")

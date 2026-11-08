#!/usr/bin/env python3
"""Make the manuscript's figures legible, and split the over-crowded Figure 10.

Three things:

1. Every main-text figure is placed at the full 6.30 in text width.  Most were
   sitting at 2.4 to 4.3 in although the column is 6.30 in wide, which shrank
   9 pt artwork to 4-6 pt.
2. Figure 10 is replaced by the version re-authored at 6.30 in (two panels:
   the evidence map, and bootstrap stability), and its caption is updated.
3. The old middle panel -- validation rate for all 34 proxies, never cited in
   the body -- is appended as Supplementary Figure S9.
"""
from __future__ import annotations
import copy, io, itertools, re, sys, zipfile
from pathlib import Path
from lxml import etree
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
IMG_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
EMU = 914400
COL = int(6.30 * EMU)                 # text width
MAXH = int(8.60 * EMU)                # leave room for a caption on the page

SRC, OUT = sys.argv[1], sys.argv[2]
TRACK = "--no-track" not in sys.argv
AUTHOR, DATE = "Handsome Nyoni", "2026-11-03T00:00:00Z"
V2 = Path(__file__).resolve().parents[1]
FIGS = V2 / "figs"
_ids = itertools.count(9700)


def rev():
    return {W + "id": str(next(_ids)), W + "author": AUTHOR, W + "date": DATE}


z = zipfile.ZipFile(SRC)
parts = {n: z.read(n) for n in z.namelist()}
infos = {i.filename: i for i in z.infolist()}
order = list(z.namelist())
z.close()

doc = etree.fromstring(parts["word/document.xml"])
body = doc.find(W + "body")
rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
rel_target = {r.get("Id"): r.get("Target") for r in rels}


def text_of(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def native_in(blob):
    im = Image.open(io.BytesIO(blob))
    dpi = (im.info.get("dpi") or (600, 600))[0] or 600
    return im.size[0] / dpi, im.size[1] / dpi


def set_extent(p, cx, cy):
    for ext in p.iter(WP + "extent"):
        ext.set("cx", str(int(cx))); ext.set("cy", str(int(cy)))
    for ext in p.iter(A + "ext"):
        if ext.getparent().tag == A + "xfrm":
            ext.set("cx", str(int(cx))); ext.set("cy", str(int(cy)))


# ---------------------------------------------------------------- 1. Figure 10
new_fig = (FIGS / "Fig11_evidence_map_print.png").read_bytes()
fig10_para = None
for p in body.iter(W + "p"):
    blip = p.find(f".//{A}blip")
    if blip is not None and rel_target[blip.get(R + "embed")] == "media/image12.png":
        fig10_para = p
assert fig10_para is not None, "Figure 10 paragraph not found"
parts["word/media/image12.png"] = new_fig
nw, nh = native_in(new_fig)
set_extent(fig10_para, COL, COL * nh / nw)
for cnv in fig10_para.iter(PIC + "cNvPr"):
    cnv.set("name", "Fig11_evidence_map_print.png")
print(f"Figure 10 replaced: {nw:.2f} x {nh:.2f} in artwork placed at "
      f"6.30 x {6.30 * nh / nw:.2f} in (1:1)")

# ------------------------------------------- 2. widen every other main figure
MAIN = {f"media/image{i}.png" for i in range(1, 13)}
print("\nresized to the full text column:")
for p in body.iter(W + "p"):
    blip = p.find(f".//{A}blip")
    if blip is None:
        continue
    tgt = rel_target[blip.get(R + "embed")]
    if tgt not in MAIN or p is fig10_para:
        continue
    ext = p.find(f".//{WP}extent")
    old_w, old_h = int(ext.get("cx")), int(ext.get("cy"))
    nw, nh = native_in(parts["word/" + tgt])
    cy = COL * nh / nw
    if cy > MAXH:                       # a very tall figure keeps its aspect
        cy, cx = MAXH, MAXH * nw / nh
    else:
        cx = COL
    if abs(cx - old_w) < EMU * 0.02:
        continue
    set_extent(p, cx, cy)
    print(f"  {tgt:18s} {old_w/EMU:4.2f} -> {cx/EMU:4.2f} in wide "
          f"(shrink {nw/(cx/EMU):4.2f}x was {nw/(old_w/EMU):4.2f}x)")

# ------------------------------------------- 3. caption and cross-reference
OLD_B = ("(b) The same validation rates with their counts, denominators and intervals "
         "shown separately, ordered by rate; filled symbols mark proxies with at least "
         "one spatial, blocked or external validation. (c) The proportion")
NEW_B = "(b) The proportion"
TAIL_OLD = ("only proxies reaching a top-eight place in at least one resample are shown.")
TAIL_NEW = ("only proxies reaching a top-eight place in at least one resample are shown. "
            "The validation rate of every named proxy, with its count, denominator and "
            "interval shown separately, is Supplementary Figure S9.")

edits = 0
for p in body.iter(W + "p"):
    for t in p.iter(W + "t"):
        if t.text and OLD_B in t.text:
            t.text = t.text.replace(OLD_B, NEW_B); edits += 1
        if t.text and TAIL_OLD in t.text and "Supplementary Figure S9" not in t.text:
            t.text = t.text.replace(TAIL_OLD, TAIL_NEW); edits += 1
        if t.text and "Figure 10c" in t.text:
            t.text = t.text.replace("Figure 10c", "Figure 10b"); edits += 1
print(f"\ncaption and cross-reference edits: {edits}")
assert edits >= 3, "expected the caption split and the Figure 10c reference"

# ------------------------------------- 4. Supplementary Figure S9 at the end
s9 = (FIGS / "FigS09_validation_rates.png").read_bytes()
nw, nh = native_in(s9)
next_img = max(int(re.search(r"image(\d+)", n).group(1))
               for n in parts if n.startswith("word/media/")) + 1
next_rid = max(int(m.group(1)) for m in
               (re.match(r"rId(\d+)$", r.get("Id")) for r in rels) if m) + 1
new_name = f"media/image{next_img}.png"
parts["word/" + new_name] = s9
order.append("word/" + new_name)
etree.SubElement(rels, PKG + "Relationship",
                 {"Id": f"rId{next_rid}", "Type": IMG_REL, "Target": new_name})

# model the new pair on the last supplementary image and its caption
img_paras, cap_para = [], None
for p in body.iter(W + "p"):
    if p.find(f".//{A}blip") is not None:
        img_paras.append(p)
    if text_of(p).strip().startswith("Supplementary Figure S8."):
        cap_para = p
assert cap_para is not None
model_img = img_paras[-1]

new_img = copy.deepcopy(model_img)
for b in new_img.iter(A + "blip"):
    b.set(R + "embed", f"rId{next_rid}")
for cnv in new_img.iter(PIC + "cNvPr"):
    cnv.set("name", "FigS09_validation_rates.png")
for dp in new_img.iter(WP + "docPr"):
    dp.set("id", "201")
set_extent(new_img, COL, COL * nh / nw)

new_cap = copy.deepcopy(cap_para)
CAPTION = ("Supplementary Figure S9. The share of each named proxy's studies that report a "
           "validation, with the count, the denominator and the 95% Wilson interval shown "
           "separately, ordered by rate. Filled symbols mark the proxies with at least one "
           "spatial, blocked or external validation design. The dashed line is the median "
           "rate across the 34 named proxies. This panel was part of Figure 10 in the "
           "submitted version and is reported here because the body text draws on its rates "
           "through Table 3 rather than on the panel itself.")
ts = [t for t in new_cap.iter(W + "t")]
ts[0].text = CAPTION
ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
for extra in ts[1:]:
    extra.text = ""

if TRACK:
    for el in (new_img, new_cap):
        pPr = el.find(W + "pPr")
        if pPr is None:
            pPr = etree.Element(W + "pPr"); el.insert(0, pPr)
        rPr = pPr.find(W + "rPr")
        if rPr is None:
            rPr = etree.SubElement(pPr, W + "rPr")
        if rPr.find(W + "ins") is None:
            rPr.insert(0, etree.Element(W + "ins", rev()))
    for run in new_cap.findall(W + "r"):
        if run.find(W + "t") is None:
            continue
        ins = etree.Element(W + "ins", rev())
        run.addprevious(ins); ins.append(run)

sect = body.find(W + "sectPr")
sect.addprevious(new_img)
sect.addprevious(new_cap)
print(f"Supplementary Figure S9 appended as {new_name} "
      f"(6.30 x {6.30 * nh / nw:.2f} in)")

# ------------------------------------------------------------------- write out
parts["word/document.xml"] = etree.tostring(doc, xml_declaration=True,
                                            encoding="UTF-8", standalone=True)
parts["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True,
                                                       encoding="UTF-8", standalone=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zo:
    for name in order:
        info = infos.get(name)
        zi = zipfile.ZipInfo(name, date_time=info.date_time if info else (2026, 11, 3, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zo.writestr(zi, parts[name])
print(f"\nwrote {OUT}")

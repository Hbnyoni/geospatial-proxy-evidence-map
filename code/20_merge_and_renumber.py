#!/usr/bin/env python3
"""Merge the repeated 'change by period' charts, swap in the re-authored figures,
renumber the supplementary series, and give Figure 9 its own landscape page.

Figure 7, Supplementary Figure S6 and Supplementary Figure S7 were the same
chart three times over the same four periods.  They become one three-panel
Figure 7, so the supplementary series loses two entries and S8, S9 move up to
S6, S7.
"""
from __future__ import annotations
import copy, io, os, re, sys, zipfile
from pathlib import Path
from lxml import etree
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"
EMU = 914400
COL = int(6.30 * EMU)
LAND_COL = int(9.70 * EMU)          # text width of the landscape page
PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
             "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs",
             "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
             "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
             "suppressOverlap", "jc", "textDirection", "textAlignment",
             "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
             "pPrChange"]

SRC, OUT, FIGS = sys.argv[1], sys.argv[2], sys.argv[3]

# caption text -> the re-authored artwork that replaces it
SWAP = {"Figure 7.": "Fig08_trends_print.png",
        "Figure 6a.": "Fig07_proxy_families_a_print.png",
        "Supplementary Figure S2.": "Fig03_collaboration_print.png"}
DROP = ("Supplementary Figure S6.", "Supplementary Figure S7.")
FIG7_CAPTION = (
    "Figure 7. Change by period. (a) Share of studies using static proxies only, at "
    "least one dynamic proxy family, machine learning, or targeting personal exposure. "
    "(b) Share of all studies reporting any empirical validation. (c) Among validated "
    "studies, the share whose only stated design is random or k-fold cross-validation, "
    "and the share reporting a spatial, external or temporal hold-out. Ribbons are 95% "
    "Wilson confidence intervals; n is shown under each period.")
# applied in this order, after the merged panels have been removed
RENUMBER = [("Supplementary Figure S6", "Figure 7b"),
            ("Supplementary Figure S7", "Figure 7c"),
            # via placeholders, so S8 -> S6 cannot be re-matched by the next rule
            ("Supplementary Figure S8", "@@RENUM-S6@@"),
            ("Supplementary Figure S9", "@@RENUM-S7@@"),
            ("@@RENUM-S6@@", "Supplementary Figure S6"),
            ("@@RENUM-S7@@", "Supplementary Figure S7")]

z = zipfile.ZipFile(SRC)
parts = {n: z.read(n) for n in z.namelist()}
infos = {i.filename: i for i in z.infolist()}
order = list(z.namelist())
z.close()
doc = etree.fromstring(parts["word/document.xml"])
body = doc.find(W + "body")
rel_target = {r.get("Id"): r.get("Target")
              for r in etree.fromstring(parts["word/_rels/document.xml.rels"])}


def text_of(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def get_pPr(p):
    pPr = p.find(W + "pPr")
    if pPr is None:
        pPr = etree.Element(W + "pPr"); p.insert(0, pPr)
    return pPr


def put_in_pPr(pPr, el):
    want = PPR_ORDER.index(etree.QName(el).localname)
    for child in pPr:
        nm = etree.QName(child).localname
        if nm in PPR_ORDER and PPR_ORDER.index(nm) > want:
            child.addprevious(el); return
    pPr.append(el)


def set_extent(p, cx, cy):
    for e in p.iter(WP + "extent"):
        e.set("cx", str(int(cx))); e.set("cy", str(int(cy)))
    for e in p.iter(A + "ext"):
        if e.getparent().tag == A + "xfrm":
            e.set("cx", str(int(cx))); e.set("cy", str(int(cy)))


def fit(p, blob, width=COL):
    im = Image.open(io.BytesIO(blob))
    dpi = (im.info.get("dpi") or (600, 600))[0] or 600
    nw, nh = im.size[0] / dpi, im.size[1] / dpi
    set_extent(p, width, width * nh / nw)
    return width / EMU, width / EMU * nh / nw


kids = list(body)
# index every image paragraph by the caption that follows it
pairs = []                                   # (image paragraph, caption paragraph)
for i, el in enumerate(kids):
    if etree.QName(el).localname != "p" or el.find(f".//{A}blip") is None:
        continue
    cap = next((kids[j] for j in range(i + 1, min(i + 4, len(kids)))
                if etree.QName(kids[j]).localname == "p" and text_of(kids[j]).strip()), None)
    pairs.append((el, cap))

# ---------------------------------------------------- 1. swap re-authored artwork
for img, cap in pairs:
    label = text_of(cap).strip().split(")")[0]
    for key, fname in SWAP.items():
        if text_of(cap).strip().startswith(key):
            blob = (Path(FIGS) / fname).read_bytes()
            tgt = "word/" + rel_target[img.find(f".//{A}blip").get(R + "embed")]
            parts[tgt] = blob
            for c in img.iter(PIC + "cNvPr"):
                c.set("name", fname)
            w_, h_ = fit(img, blob)
            print(f"  {key:26s} <- {fname:34s} {w_:.2f} x {h_:.2f} in")

# ------------------------------------- 2. drop the two merged supplementary panels
dropped = 0
for img, cap in pairs:
    if cap is not None and text_of(cap).strip().startswith(DROP):
        body.remove(img); body.remove(cap); dropped += 1
print(f"  removed {dropped} supplementary figures now merged into Figure 7")
assert dropped == 2

# ------------------------------------------------- 3. Figure 7's caption, renumber
edits = 0
for p in body.iter(W + "p"):
    ts = [t for t in p.iter(W + "t")]
    if ts and text_of(p).strip().startswith("Figure 7."):
        ts[0].text = FIG7_CAPTION
        ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for extra in ts[1:]:
            extra.text = ""
        edits += 1
for old, new in RENUMBER:
    for t in body.iter(W + "t"):
        if t.text and old in t.text:
            t.text = t.text.replace(old, new); edits += 1
print(f"  caption and cross-reference edits: {edits}")

# ------------------------------------------- 4. Figure 9 onto its own landscape page
kids = list(body)
fig9_img = fig9_cap = None
for i, el in enumerate(kids):
    if etree.QName(el).localname == "p" and text_of(el).strip().startswith("Figure 9."):
        fig9_cap = el
        fig9_img = next(kids[j] for j in range(i - 1, -1, -1)
                        if etree.QName(kids[j]).localname == "p"
                        and kids[j].find(f".//{A}blip") is not None)
        break
assert fig9_cap is not None and fig9_img is not None

# the portrait properties that govern this stretch: the next sectPr in document order
after = kids[kids.index(fig9_cap):]
portrait = None
for el in after:
    sp = (el.find(f"{W}pPr/{W}sectPr") if etree.QName(el).localname == "p" else None)
    if sp is None and etree.QName(el).localname == "sectPr":
        sp = el
    if sp is not None:
        portrait = copy.deepcopy(sp); break
assert portrait is not None
for junk in ("rsidR", "rsidRPr", "rsidSect"):
    portrait.attrib.pop(W + junk, None)

# close the portrait run on the paragraph before the figure
prev = kids[kids.index(fig9_img) - 1]
assert etree.QName(prev).localname == "p"
put_in_pPr(get_pPr(prev), copy.deepcopy(portrait))

# the figure's own section is the same page turned on its side, without line numbers
land = copy.deepcopy(portrait)
pg = land.find(W + "pgSz")
pw, ph = pg.get(W + "w"), pg.get(W + "h")
pg.set(W + "w", ph); pg.set(W + "h", pw); pg.set(W + "orient", "landscape")
for ln in land.findall(W + "lnNumType"):
    land.remove(ln)
put_in_pPr(get_pPr(fig9_cap), land)

blob = parts["word/" + rel_target[fig9_img.find(f".//{A}blip").get(R + 'embed')]]
w_, h_ = fit(fig9_img, blob, LAND_COL)
print(f"  Figure 9 on its own landscape page: {w_:.2f} x {h_:.2f} in")

parts["word/document.xml"] = etree.tostring(doc, xml_declaration=True,
                                            encoding="UTF-8", standalone=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zo:
    for n in order:
        i = infos.get(n)
        zi = zipfile.ZipInfo(n, date_time=i.date_time if i else (2026, 11, 3, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zo.writestr(zi, parts[n])
print(f"wrote {OUT}")

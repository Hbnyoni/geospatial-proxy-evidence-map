#!/usr/bin/env python3
"""Append the supplementary figures into the main manuscript as a new section.

The text (heading and captions) is recorded as a tracked insertion; the image
runs are left unmarked, as Word cannot mark a picture usefully -- the same
compromise already used for Figure 10 and Table 3.
"""
import copy, itertools, re, sys, zipfile
from lxml import etree

MAIN, SUP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TRACK = len(sys.argv) < 5 or sys.argv[4] != "--no-track"
AUTHOR, DATE = "Handsome Nyoni", "2026-11-03T00:00:00Z"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
IMG_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

# pPr child order (CT_PPr); rPr and sectPr sit at the end
PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
             "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs",
             "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
             "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
             "suppressOverlap", "jc", "textDirection", "textAlignment",
             "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
             "pPrChange"]
_ids = itertools.count(9500)


def rev_attrs():
    return {W + "id": str(next(_ids)), W + "author": AUTHOR, W + "date": DATE}


def get_pPr(p):
    pPr = p.find(W + "pPr")
    if pPr is None:
        pPr = etree.SubElement(p, W + "pPr")
        p.remove(pPr)
        p.insert(0, pPr)
    return pPr


def put_in_pPr(pPr, el):
    """Insert el into pPr at its schema-correct position."""
    tag = etree.QName(el).localname
    want = PPR_ORDER.index(tag)
    for child in pPr:
        name = etree.QName(child).localname
        if name in PPR_ORDER and PPR_ORDER.index(name) > want:
            child.addprevious(el)
            return
    pPr.append(el)


zmain = zipfile.ZipFile(MAIN)
parts = {n: zmain.read(n) for n in zmain.namelist()}
infos = {i.filename: i for i in zmain.infolist()}
order = list(zmain.namelist())
zmain.close()

zsup = zipfile.ZipFile(SUP)
sup_doc = etree.fromstring(zsup.read("word/document.xml"))
sup_rels = etree.fromstring(zsup.read("word/_rels/document.xml.rels"))

# ---- map the supplementary image rIds onto fresh ones in the main package ----
sup_img = {r.get("Id"): r.get("Target") for r in sup_rels
           if r.get("Type") == IMG_REL}
main_rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
used_rid = {int(re.match(r"rId(\d+)$", r.get("Id")).group(1))
            for r in main_rels if re.match(r"rId(\d+)$", r.get("Id"))}
next_rid = max(used_rid) + 1
used_media = {n for n in parts if n.startswith("word/media/")}
next_img = max(int(re.search(r"image(\d+)", n).group(1))
               for n in used_media) + 1

rid_map, media_add = {}, {}
for old_id, target in sorted(sup_img.items(), key=lambda kv: kv[1]):
    ext = target.rsplit(".", 1)[1]
    new_target = f"media/image{next_img}.{ext}"
    rid_map[old_id] = f"rId{next_rid}"
    media_add["word/" + new_target] = zsup.read("word/" + target)
    etree.SubElement(main_rels, PKG + "Relationship",
                     {"Id": f"rId{next_rid}", "Type": IMG_REL, "Target": new_target})
    next_rid += 1
    next_img += 1
zsup.close()

# ---------------------------- build the appended block ----------------------
main_doc = etree.fromstring(parts["word/document.xml"])
body = main_doc.find(W + "body")
body_sectPr = body.find(W + "sectPr")
assert body_sectPr is not None

sup_body = sup_doc.find(W + "body")
blocks = [c for c in sup_body if etree.QName(c).localname != "sectPr"]
assert blocks, "supplementary body is empty"

docpr_id = itertools.count(101)
appended, n_ins_runs, n_img_runs = [], 0, 0
for src in blocks:
    el = copy.deepcopy(src)
    # remap image references and give every picture a unique id
    for blip in el.iter():
        if R + "embed" in blip.attrib:
            old = blip.get(R + "embed")
            assert old in rid_map, f"unmapped image rId {old}"
            blip.set(R + "embed", rid_map[old])
    for dp in el.iter(WP + "docPr"):
        dp.set("id", str(next(docpr_id)))
    if etree.QName(el).localname == "p":
        # the supplementary title style becomes a main-document section heading
        for ps in el.iter(W + "pStyle"):
            if ps.get(W + "val") == "Title":
                ps.set(W + "val", "Heading1")
        if TRACK:
            pPr = get_pPr(el)
            rPr = pPr.find(W + "rPr")
            if rPr is None:
                rPr = etree.Element(W + "rPr")
                put_in_pPr(pPr, rPr)
            rPr.insert(0, etree.Element(W + "ins", rev_attrs()))
            for run in el.findall(W + "r"):
                if run.find(f".//{W}drawing") is not None:
                    n_img_runs += 1
                    continue
                if run.find(W + "t") is None:
                    continue
                ins = etree.Element(W + "ins", rev_attrs())
                run.addprevious(ins)
                ins.append(run)
                n_ins_runs += 1
    appended.append(el)

# ---- close the manuscript's own section on its last paragraph, so the -------
# ---- supplementary block starts a new section (and a new page) --------------
last_p = None
for child in body:
    if etree.QName(child).localname == "p":
        last_p = child
assert last_p is not None
moved = copy.deepcopy(body_sectPr)
for junk in ("rsidR", "rsidRPr", "rsidSect"):
    moved.attrib.pop(W + junk, None)
put_in_pPr(get_pPr(last_p), moved)

for el in appended:
    body_sectPr.addprevious(el)

# the final section governs the supplementary pages: no line numbering there
for ln in body_sectPr.findall(W + "lnNumType"):
    body_sectPr.remove(ln)

parts["word/document.xml"] = etree.tostring(main_doc, xml_declaration=True,
                                            encoding="UTF-8", standalone=True)
parts["word/_rels/document.xml.rels"] = etree.tostring(
    main_rels, xml_declaration=True, encoding="UTF-8", standalone=True)
parts.update(media_add)
for name in media_add:
    if name not in order:
        order.append(name)

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zo:
    for name in order:
        info = infos.get(name)
        zi = zipfile.ZipInfo(name, date_time=info.date_time if info
                             else (2026, 11, 3, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zo.writestr(zi, parts[name])

print(f"wrote {OUT}")
print(f"  appended {len(appended)} blocks, {len(media_add)} images "
      f"({', '.join(sorted(media_add))[:0] or ''}image{next_img - len(media_add)}"
      f"..image{next_img - 1})")
print(f"  tracked text runs: {n_ins_runs}; untracked image runs: {n_img_runs}")

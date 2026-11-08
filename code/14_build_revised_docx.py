#!/usr/bin/env python3
"""Rebuild a complete, shareable .docx from the recovered parts of the reviewed manuscript.

The copy of Geospatial_Proxy_Bibliometric_Review_DRAFT_HBN_131026.docx that reached this machine was
truncated at 1,280 KiB. word/document.xml and word/comments.xml survived intact, so the author's text
and the supervisor's markup are complete; the lost parts are styles, settings, numbering, theme,
fontTable and media/image5-12. This script restores them and produces a clean revised manuscript:

  * Siphiwe Mphuthi's tracked changes are accepted (w:ins unwrapped, w:del dropped, *Change records
    removed), because every one of them is an editorial correction we are adopting.
  * her comment anchors are removed; the four comments are answered in the response letter instead.
  * styles.xml comes from the Oct 4 build, which shares its lineage, with Bibliography, PlainTable2
    and Hyperlink injected from the author's own Chapter 2 document.
  * numId 10 (the five research questions) is redefined; numId 11 belonged to guidance paragraphs
    that this revision deletes.
  * media/image1-4 are the recovered originals; image5-12 are re-inserted from figs/ using the
    figure order in 06_build_manuscript.py. image12, Figure 10, becomes the new evidence map.
  * Table 3 is rebuilt with 13 columns from T3_evidence_map_top20.csv, in its own landscape section.

Reference paragraphs are never touched: the Bibliography-styled block and the citation fields live in
document.xml, which is carried over as the author left it.

Usage: python3 14_build_revised_docx.py [-o out.docx]
"""
from __future__ import annotations

import argparse
import copy
import csv
import re
import shutil
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

ROOT = Path(__file__).resolve().parent.parent
REC = Path("/tmp/claude-1002/-PALS-CHEAQI-Composite-Indicator/"
           "d700fc5e-4fa8-4b92-aa96-715ca7c7b00b/scratchpad/biblio_docx/recovered")
OCT4 = ROOT / "manuscript" / "Geospatial_Proxy_Bibliometric_Review_DRAFT.docx"
DONOR = Path("/home/bongani/PhD_Thesis/UCT PHD 2026/Chapter 2 Literature Review/"
             "HBN Chapter_2_ Literature Review_26_03_2026.docx")
DONOR_COMMENTS = Path("/home/bongani/PhD_Thesis/UCT PHD 2026/Chapter 3 Research Methodology/"
                      "Segmentation Manuscript/"
                      "Segmentation Manuscript HB10122025 UPDATED_GeoHealth_AGU_Submission_withFigures.docx")
FIGS = ROOT / "figs"
T3CSV = ROOT / "review" / "revision_2026-10-27" / "T3_evidence_map_top20.csv"

# media slot -> source figure, from MAIN in 06_build_manuscript.py
MEDIA = {
    5: "Fig05_themes_bursts_b.png",
    6: "Fig06_cocitation.png",
    7: "Fig07_proxy_families_a.png",
    8: "Fig07_proxy_families_b.png",
    9: "Fig08_trends_a.png",
    10: "Fig09_geography_a.png",
    11: "Fig10_three_field.png",
    12: "Fig11_evidence_map.png",      # the revised Figure 10
}

ET.register_namespace("w", NS_W)


# --------------------------------------------------------------------------- tracked changes
def accept_tracked_changes(root):
    """Accept every insertion, reject every deletion, keep the resulting formatting."""
    counts = {"ins": 0, "del": 0, "fmt": 0}
    parents = {c: p for p in root.iter() for c in p}
    # deletions first, so an inserted-then-deleted run does not survive
    for el in [e for e in root.iter(W + "del")]:
        p = parents.get(el)
        if p is not None:
            p.remove(el)
            counts["del"] += 1
    parents = {c: p for p in root.iter() for c in p}
    for el in [e for e in root.iter(W + "ins")]:
        p = parents.get(el)
        if p is None:
            continue
        i = list(p).index(el)
        for j, child in enumerate(list(el)):
            p.insert(i + j, child)
        p.remove(el)
        counts["ins"] += 1
    for tag in ("pPrChange", "rPrChange", "tblPrChange", "tcPrChange", "trPrChange",
                "sectPrChange", "tblGridChange"):
        parents = {c: p for p in root.iter() for c in p}
        for el in [e for e in root.iter(W + tag)]:
            p = parents.get(el)
            if p is not None:
                p.remove(el)
                counts["fmt"] += 1
    # a rejected deletion can leave an empty w:p wrapper behind; drop stray w:delText
    for t in [e for e in root.iter(W + "delText")]:
        p = {c: q for q in root.iter() for c in q}.get(t)
        if p is not None:
            p.remove(t)
    return counts


def strip_comments(root):
    """Remove comment anchors and the runs that carry a comment reference."""
    n = 0
    for _ in range(2):
        parents = {c: p for p in root.iter() for c in p}
        drop = []
        for el in root.iter():
            tag = el.tag
            if tag in (W + "commentRangeStart", W + "commentRangeEnd"):
                drop.append(el)
            elif tag == W + "r" and el.find(W + "commentReference") is not None:
                drop.append(el)
        for el in drop:
            p = parents.get(el)
            if p is not None:
                p.remove(el)
                n += 1
        if not drop:
            break
    return n


# --------------------------------------------------------------------------- table 3
def _tc(text, *, bold=False, size=16, align=None, width=None):
    tc = ET.Element(W + "tc")
    pr = ET.SubElement(tc, W + "tcPr")
    if width:
        ET.SubElement(pr, W + "tcW", {W + "w": str(width), W + "type": "dxa"})
    ET.SubElement(pr, W + "vAlign", {W + "val": "center"})
    p = ET.SubElement(tc, W + "p")
    ppr = ET.SubElement(p, W + "pPr")
    ET.SubElement(ppr, W + "spacing", {W + "before": "20", W + "after": "20", W + "line": "240",
                                       W + "lineRule": "auto"})
    if align:
        ET.SubElement(ppr, W + "jc", {W + "val": align})
    prpr = ET.SubElement(ppr, W + "rPr")
    ET.SubElement(prpr, W + "sz", {W + "val": str(size)})
    r = ET.SubElement(p, W + "r")
    rpr = ET.SubElement(r, W + "rPr")
    if bold:
        ET.SubElement(rpr, W + "b")
    ET.SubElement(rpr, W + "sz", {W + "val": str(size)})
    ET.SubElement(rpr, W + "szCs", {W + "val": str(size)})
    t = ET.SubElement(r, W + "t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return tc


def build_table3(csv_path):
    rows = list(csv.reader(open(csv_path)))
    head, body = rows[0], rows[1:]
    # landscape A4 less 2 cm margins = 16838 - 2268 = 14570 twips
    widths = [2500, 2150, 760, 820, 1080, 1000, 950, 1500, 820, 760, 560, 1680, 760]
    assert len(widths) == len(head), (len(widths), len(head))
    tbl = ET.Element(W + "tbl")
    pr = ET.SubElement(tbl, W + "tblPr")
    ET.SubElement(pr, W + "tblStyle", {W + "val": "PlainTable2"})
    ET.SubElement(pr, W + "tblW", {W + "w": str(sum(widths)), W + "type": "dxa"})
    ET.SubElement(pr, W + "tblLayout", {W + "type": "fixed"})
    look = ET.SubElement(pr, W + "tblLook", {W + "val": "04A0", W + "firstRow": "1",
                                             W + "lastRow": "0", W + "firstColumn": "1",
                                             W + "lastColumn": "0", W + "noHBand": "0",
                                             W + "noVBand": "1"})
    grid = ET.SubElement(tbl, W + "tblGrid")
    for wd in widths:
        ET.SubElement(grid, W + "gridCol", {W + "w": str(wd)})
    tr = ET.SubElement(tbl, W + "tr")
    trpr = ET.SubElement(tr, W + "trPr")
    ET.SubElement(trpr, W + "tblHeader")
    for h, wd in zip(head, widths):
        tr.append(_tc(h, bold=True, width=wd))
    for row in body:
        tr = ET.SubElement(tbl, W + "tr")
        for i, (cell, wd) in enumerate(zip(row, widths)):
            tr.append(_tc(cell, width=wd, align=None if i < 3 or i == 11 else "right"))
    return tbl, len(body)


def sect_pr(landscape, template):
    """A sectPr cloned from the body's, switched to landscape if asked."""
    sp = copy.deepcopy(template)
    for t in ("rsidR", "rsidRPr", "rsidSect"):
        sp.attrib.pop(W + t, None)
    pg = sp.find(W + "pgSz")
    mar = sp.find(W + "pgMar")
    if landscape:
        pg.set(W + "w", "16838")
        pg.set(W + "h", "11906")
        pg.set(W + "orient", "landscape")
        for side in ("left", "right"):
            mar.set(W + side, "1134")
    else:
        pg.set(W + "w", "11906")
        pg.set(W + "h", "16838")
        pg.attrib.pop(W + "orient", None)
    return sp


def empty_para_with_sect(sp):
    p = ET.Element(W + "p")
    ppr = ET.SubElement(p, W + "pPr")
    ppr.append(sp)
    rpr = ET.SubElement(ppr, W + "rPr")
    ET.SubElement(rpr, W + "sz", {W + "val": "24"})
    return p


def ptext(p):
    return re.sub(r"\s+", " ", "".join(t.text or "" for t in p.iter(W + "t"))).strip()


def replace_table3(root):
    body = root.find(W + "body")
    kids = list(body)
    cap = next((i for i, c in enumerate(kids)
                if c.tag == W + "p" and ptext(c).startswith("Table 3.")), None)
    if cap is None:
        raise SystemExit("Table 3 caption not found")
    tbl_i = next((i for i in range(cap, len(kids)) if kids[i].tag == W + "tbl"), None)
    if tbl_i is None:
        raise SystemExit("Table 3 body not found")
    old_rows = len(kids[tbl_i].findall(W + "tr"))
    new_tbl, n = build_table3(T3CSV)
    body.remove(kids[tbl_i])
    body.insert(tbl_i, new_tbl)

    # the footnote paragraph immediately after the table closes the landscape block
    kids = list(body)
    end = tbl_i
    for i in range(tbl_i + 1, min(tbl_i + 4, len(kids))):
        if kids[i].tag == W + "p" and ptext(kids[i]).startswith("Records:"):
            end = i
            break
    else:
        end = tbl_i
    tmpl = body.find(W + "sectPr")
    body.insert(end + 1, empty_para_with_sect(sect_pr(True, tmpl)))
    body.insert(cap, empty_para_with_sect(sect_pr(False, tmpl)))
    return old_rows, n


# --------------------------------------------------------------------------- parts
def reanchor_comment(root, cid, prefix):
    """Re-attach an orphaned comment to the paragraph that now answers it.

    Comment 36 was anchored inside the old Table 3, which this script replaces wholesale, so its
    anchor would be lost and Word would simply not show the comment. It is re-attached to the
    revised caption instead, where the reconciled temporal labels are described.
    """
    body = root.find(f"{W}body")
    for para in body.iter(f"{W}p"):
        if ptext(para).startswith(prefix):
            if para.find(f"{W}commentRangeStart") is not None:
                return False
            para.insert(1 if para.find(f"{W}pPr") is not None else 0,
                        ET.Element(f"{W}commentRangeStart", {f"{W}id": str(cid)}))
            ET.SubElement(para, f"{W}commentRangeEnd", {f"{W}id": str(cid)})
            r = ET.SubElement(para, f"{W}r")
            rpr = ET.SubElement(r, f"{W}rPr")
            ET.SubElement(rpr, f"{W}rStyle", {f"{W}val": "CommentReference"})
            ET.SubElement(r, f"{W}commentReference", {f"{W}id": str(cid)})
            return True
    return False


def inject_styles(oct4_styles, donors):
    """Oct 4 styles.xml plus Bibliography, PlainTable2 and Hyperlink from the author's Chapter 2.

    Dependencies are pulled transitively: a style that is basedOn, linked to or followed by another
    style drags that one in too, or Word reports the styles part as damaged.
    """
    base = oct4_styles.decode("utf8")
    donors = [d.decode("utf8") if isinstance(d, bytes) else d for d in donors]
    have = set(re.findall(r'w:styleId="([^"]+)"', base))

    def find(sid):
        for donor in donors:
            m = re.search(r'<w:style [^>]*w:styleId="%s".*?</w:style>' % re.escape(sid), donor, re.S)
            if m:
                return m
        return None

    add, order, queue = {}, [], list(WANTED_STYLES)
    while queue:
        sid = queue.pop(0)
        if sid in have or sid in add:
            continue
        m = find(sid)
        if not m:
            print(f"  ! style {sid} not in donor", file=sys.stderr)
            continue
        add[sid] = m.group(0)
        order.append(sid)
        queue += re.findall(r'<w:(?:basedOn|link|next) w:val="([^"]+)"', m.group(0))
    if add:
        base = base.replace("</w:styles>", "".join(add[s] for s in order) + "</w:styles>")
    return base.encode("utf8"), order


WANTED_STYLES = ["Bibliography", "PlainTable2", "Hyperlink"]

NUMDEFS = """<w:abstractNum w:abstractNumId="910"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/>
<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="911"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="\uf0b7"/>
<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr></w:lvl></w:abstractNum>
<w:num w:numId="10"><w:abstractNumId w:val="910"/></w:num>
<w:num w:numId="11"><w:abstractNumId w:val="911"/></w:num>"""


def inject_numbering(oct4_numbering):
    """Define numId 10, the five research questions, and numId 11, the reviewer's guidance bullets.

    numId 11 is only reached by paragraphs this revision strikes out, so it matters in the marked-up
    copy and not in the clean one; it is defined in both, because an undefined numId makes Word
    report the numbering part as damaged.
    """
    t = oct4_numbering.decode("utf8")
    if 'w:numId="10"' in t and 'w:numId="11"' in t:
        return oct4_numbering
    body = re.sub(r">\s+<", "><", NUMDEFS)
    # every abstractNum must precede every num
    abstracts = "".join(m.group(0) for m in re.finditer(r"<w:abstractNum\b.*?</w:abstractNum>", body, re.S))
    nums = "".join(m.group(0) for m in re.finditer(r"<w:num\b.*?</w:num>", body, re.S))
    t = t.replace("</w:numbering>", abstracts + nums + "</w:numbering>")
    return t.encode("utf8")


CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>Geospatial Proxy Indicators for Air-Pollution Exposure Assessment: A Bibliometric and Validation Evidence Map with Implications for Sub-Saharan Africa</dc:title>
<dc:creator>Handsome Nyoni</dc:creator><cp:lastModifiedBy>Handsome Nyoni</cp:lastModifiedBy>
<cp:revision>2</cp:revision><dcterms:created xsi:type="dcterms:W3CDTF">2026-10-28T00:00:00Z</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-28T00:00:00Z</dcterms:modified>
</cp:coreProperties>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/webSettings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"/>
<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
<Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

COMMENTS_CT = ('<Override PartName="/word/comments.xml" ContentType="application/vnd.openxml'
               'formats-officedocument.wordprocessingml.comments+xml"/>')

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def filter_rels(src, keep_comments=False):
    """Keep styles, numbering, settings, webSettings, fontTable, theme, hyperlinks and images."""
    drop = ["commentsExtended", "commentsIds", "commentsExtensible", "people",
            "customXml", "customXmlProps"]
    if not keep_comments:
        drop.append("comments")
    out, kept = [], []
    for m in re.finditer(r"<Relationship\b[^>]*/>", src):
        tag = m.group(0)
        typ = re.search(r'Type="[^"]*/(\w+)"', tag)
        if typ and typ.group(1) in drop:
            continue
        out.append(tag)
        kept.append(typ.group(1) if typ else "?")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(out) + "</Relationships>"), kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ROOT / "manuscript" /
                                               "Geospatial_Proxy_Bibliometric_Review_REVISED_HBN_281026.docx"))
    ap.add_argument("--keep-comments", action="store_true",
                    help="carry the supervisor's four comments over, for a marked-up copy")
    args = ap.parse_args()

    for p in (REC / "word__document.xml", OCT4, DONOR, T3CSV):
        if not Path(p).exists():
            raise SystemExit(f"missing input: {p}")

    root = ET.parse(REC / "word__document.xml").getroot()

    tc = accept_tracked_changes(root)
    nc = 0 if args.keep_comments else strip_comments(root)
    old_rows, new_rows = replace_table3(root)
    if args.keep_comments and reanchor_comment(root, 36, "Table 3."):
        print("comment 36 re-anchored to the Table 3 caption")
    print(f"tracked changes: accepted {tc['ins']} insertions, rejected {tc['del']} deletions, "
          f"cleared {tc['fmt']} format-change records")
    print("comments: kept" if args.keep_comments else f"comment anchors removed: {nc}")
    print(f"Table 3: {old_rows} rows x 9 cols  ->  {new_rows} rows x 13 cols, landscape section")

    z4 = zipfile.ZipFile(OCT4)
    donors = [zipfile.ZipFile(DONOR).read("word/styles.xml")]
    if args.keep_comments:
        WANTED_STYLES.extend(["CommentReference", "CommentText"])
        donors.append(zipfile.ZipFile(DONOR_COMMENTS).read("word/styles.xml"))
    styles, added = inject_styles(z4.read("word/styles.xml"), donors)
    numbering = inject_numbering(z4.read("word/numbering.xml"))
    print(f"styles injected from Chapter 2: {', '.join(added) or 'none needed'}")

    rels, kept = filter_rels((REC / "word___rels__document.xml.rels").read_text(),
                             keep_comments=args.keep_comments)
    print(f"relationships kept: {len(kept)} ({sorted(set(kept))})")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        ct = CONTENT_TYPES.replace("</Types>", COMMENTS_CT + "</Types>") if args.keep_comments \
            else CONTENT_TYPES
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("word/document.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                   + ET.tostring(root, encoding="unicode"))
        z.writestr("word/_rels/document.xml.rels", rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/numbering.xml", numbering)
        for part in ("word/settings.xml", "word/webSettings.xml", "word/fontTable.xml",
                     "word/theme/theme1.xml", "docProps/app.xml"):
            z.writestr(part, z4.read(part))
        z.writestr("docProps/core.xml", CORE)
        if args.keep_comments:
            z.writestr("word/comments.xml", (REC / "word__comments.xml").read_bytes())
        for i in (1, 2, 3, 4):
            z.writestr(f"word/media/image{i}.png", (REC / f"word__media__image{i}.png").read_bytes())
        for slot, name in MEDIA.items():
            src = FIGS / name
            if not src.exists():
                raise SystemExit(f"missing figure: {src}")
            z.writestr(f"word/media/image{slot}.png", src.read_bytes())
    print(f"\nwrote {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    return out


if __name__ == "__main__":
    main()

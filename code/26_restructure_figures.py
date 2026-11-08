#!/usr/bin/env python3
"""Move the four descriptive science-mapping figures to supplementary and renumber everything.

Each of old Figures 2b, 3, 4 and 5 is cited exactly once in the body and none carries the paper's
argument, which is the evidence map. Moving them leaves seven main figures, each cited more than
once or required by PRISMA.

Two pairs merge rather than add, because each pair is the same material twice:
    old Figure 2b joins old S1  -> S1(a) Bradford curve, S1(b) the twelve most productive sources
    old Figure 3  joins old S3  -> S3(a) the keyword network, S3(b) the same network by year
So supplementary ends at S9, not S11.

Image moves are not tracked changes: Word cannot mark a moved picture usefully. Caption rewrites for
the two merged figures are tracked. Figure-number renumbering is a direct text edit, as in
20_merge_and_renumber.py, because twenty tracked marks on mechanical renumbering would bury the
substantive edits. All three categories are disclosed in the response letter.

    python3 scripts/26_restructure_figures.py --check <file.docx>
    python3 scripts/26_restructure_figures.py --apply <file.docx> -o out.docx [--track]
"""
from __future__ import annotations
import argparse, re, sys, zipfile
from importlib import import_module
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = import_module("13_apply_revisions")
W = M.W

# old label -> new label, for every reference and caption prefix in the document
RENUMBER = {
    "1": "1", "2a": "2", "2b": "S1b", "3": "S3a", "4": "S5", "5": "S6",
    "6a": "3a", "6b": "3b", "7": "4", "7a": "4a", "7b": "4b", "7c": "4c",
    "8": "5", "9": "6", "10": "7", "10a": "7a", "10b": "7b", "10c": "7c",
    "S1": "S1a", "S2": "S2", "S3": "S3b", "S4": "S4",
    "S5": "S7", "S6": "S8", "S7": "S9",
}

S1_MERGED = (
    "Supplementary Figure S1. Sources. (a) Bradford distribution of sources: cumulative studies "
    "against source rank, with the zone boundaries marked. (b) The twelve most productive sources, "
    "coloured by Bradford zone."
)
S3_MERGED = (
    "Supplementary Figure S3. The author-keyword co-occurrence network. (a) Co-occurrence map of "
    "normalised author keywords used in at least five studies; bubble size and label size are "
    "proportional to occurrences and colour marks the detected cluster. (b) The same network "
    "coloured by the average publication year of each keyword's studies, so that older and newer "
    "vocabulary can be told apart."
)

LABEL = re.compile(r"\b(Supplementary\s+)?Figure\s+(S?\d+)([a-c])?\b")


def relabel(text: str) -> str:
    """Rewrite every figure reference in one pass, so no rule can rematch another's output."""
    def sub(m):
        supp, num, panel = m.group(1), m.group(2), m.group(3) or ""
        new = RENUMBER.get(num + panel)
        if new is None:
            new = RENUMBER.get(num)
            if new is None:
                return m.group(0)
            new += panel
        prefix = "Supplementary Figure " if (supp or new.startswith("S")) else "Figure "
        if supp and not new.startswith("S"):
            prefix = "Figure "
        return prefix + new
    return LABEL.sub(sub, text)


def caption_of(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()


def has_image(p) -> bool:
    return next(p.iter(W + "drawing"), None) is not None


def find_blocks(body):
    """Every figure as (caption_element, [image elements immediately above it])."""
    kids = list(body)
    out = {}
    for i, p in enumerate(kids):
        if p.tag != W + "p":
            continue
        t = caption_of(p)
        m = re.match(r"^(?:Supplementary )?Figure (S?\d+[a-c]?)\.", t)
        if not m or has_image(p):
            continue
        imgs, j = [], i - 1
        while j >= 0 and kids[j].tag == W + "p" and has_image(kids[j]) and not caption_of(kids[j]):
            imgs.insert(0, kids[j])
            j -= 1
        out[m.group(1)] = (p, imgs)
    return out


def move_after(body, anchor, elements):
    for el in elements:
        body.remove(el)
    at = list(body).index(anchor) + 1
    for k, el in enumerate(elements):
        body.insert(at + k, el)


def move_before(body, anchor, elements):
    for el in elements:
        body.remove(el)
    at = list(body).index(anchor)
    for k, el in enumerate(elements):
        body.insert(at + k, el)


def run(root, apply: bool):
    body = root.find(W + "body")
    blocks = find_blocks(body)
    need = ["2b", "3", "4", "5", "S1", "S3", "S4"]
    report = [(k, "OK" if k in blocks else "NOT FOUND") for k in need]
    if not apply or any(s != "OK" for _, s in report):
        return report, blocks

    # 1. physical moves into the supplementary section
    move_after(body, blocks["S1"][1][-1], blocks["2b"][1])          # S1 image, then 2b image
    move_before(body, blocks["S3"][1][0], blocks["3"][1])           # 3 image, then S3 image
    anchor = blocks["S4"][0]
    for key in ("4", "5"):                                          # these keep their own captions
        cap, imgs = blocks[key]
        move_after(body, anchor, imgs + [cap])
        anchor = cap

    # 2. the two absorbed captions
    for key in ("2b", "3"):
        cap = blocks[key][0]
        if M.TRACK["on"]:
            M.mark_para_deleted(cap)
        else:
            body.remove(cap)

    # 3. the two merged captions, as tracked rewrites
    M.set_paragraph_text(blocks["S1"][0], S1_MERGED)
    M.set_paragraph_text(blocks["S3"][0], S3_MERGED)

    # 4. renumber every remaining reference and caption prefix, skipping the two just rewritten
    #    and never touching a citation field or a Bibliography paragraph
    done = {id(blocks["S1"][0]), id(blocks["S3"][0])}
    seen_refs = 0
    for p in body.iter(W + "p"):
        if id(p) in done or M.style_of(p) == "Bibliography":
            continue
        for t in p.iter(W + "t"):
            if not t.text:
                continue
            new = relabel(t.text)
            if new != t.text:
                t.text = new
                seen_refs += 1
    report.append(("relabel", f"{seen_refs} text nodes"))
    return report, blocks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-o", "--out")
    ap.add_argument("--track", action="store_true")
    a = ap.parse_args()
    M.TRACK["on"] = a.track
    M.TRACK["author"] = "Handsome Nyoni"
    M.TRACK["date"] = "2026-11-08T00:00:00Z"

    tgt = Path(a.target)
    with zipfile.ZipFile(tgt) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    rep, _ = run(root, apply=a.apply)
    if a.apply:
        out = Path(a.out) if a.out else tgt.with_name(tgt.stem + "_RS.docx")
        new_xml = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
        with zipfile.ZipFile(tgt) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for it in zin.infolist():
                zout.writestr(it, new_xml if it.filename == "word/document.xml"
                              else zin.read(it.filename))
        print(f"wrote {out}")
    for k, s in rep:
        print(f"  {k:10s} {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

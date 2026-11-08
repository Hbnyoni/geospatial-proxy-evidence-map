#!/usr/bin/env python3
"""Add the declarations and contribution language a REF assessor looks for.

UCT does not submit to the Research Excellence Framework, but the third affiliation on this paper is
the Liverpool School of Tropical Medicine, a UK institution that does. For the output to be
submittable and to be judged on its merits rather than fail on paperwork, four things have to be on
the page: a deposit that can be verified, a funding statement, the open-access rights-retention
wording, and a contribution statement that names originality, significance and rigour against
evidence an assessor can trace.

Every edit here is plain prose. Nothing touches a citation field or a Bibliography paragraph, so the
reference list keeps its formatting. The tracked-change and field-safety machinery is reused from
13_apply_revisions.py rather than rewritten.

    python3 scripts/21_ref_declarations.py --check <file.docx>
    python3 scripts/21_ref_declarations.py --apply <file.docx> -o out.docx [--track]
"""
from __future__ import annotations
import argparse, shutil, sys, zipfile
from importlib import import_module
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = import_module("13_apply_revisions")

# The deposit DOI does not exist until the archive is uploaded. It is left as an unmistakable
# placeholder so that it cannot be mistaken for a real identifier if the deposit is forgotten.
DOI = "10.5281/zenodo.XXXXXXX"

DATA_CODE = (
    "Data and code availability. The screened corpus of 692 included studies with their proxy, "
    "pollutant, method, setting and validation coding; the title-abstract and full-text screening "
    "workbooks recording every decision and exclusion reason; the blinded audit and inter-coder "
    "agreement records; the co-occurrence network node and edge files; the Boolean search strings "
    "for both databases with the date each was executed; and the six analysis scripts that "
    "reproduce every number, table and figure from the four raw exports are archived at Zenodo "
    f"under a Creative Commons Attribution 4.0 International licence (DOI: {DOI}). Bibliographic "
    "records retrieved from Scopus and Web of Science are redistributed only as the derived fields "
    "their licence terms permit; because the search strings and retrieval dates are archived in "
    "full, any licence holder can re-execute the searches and rebuild the corpus independently. No "
    "other restrictions apply to the data or the code."
)

FUNDING = (
    "Funding. This review was conducted within a doctoral programme supported by the National "
    "Institute of Environmental Health Sciences and the Office of Strategic Coordination of the "
    "National Institutes of Health under Award Number U01ES036146-0, and by the Fogarty "
    "International Center of the National Institutes of Health under Award Number U54TW012083 "
    "through the HE2AT Centre. No funder had any role in the design of "
    "the review, in the screening, coding or analysis, in the writing of the manuscript, or in the "
    "decision to submit it for publication. The content is solely the responsibility of the "
    "authors and does not necessarily represent the official views of the National Institutes of "
    "Health."
)

OPEN_ACCESS = (
    "Open access. For the purpose of open access, the authors have applied a Creative Commons "
    "Attribution (CC BY 4.0) licence to the Author Accepted Manuscript arising from this "
    "submission. The Author Accepted Manuscript will be deposited, with no embargo, in the "
    "institutional repositories of the Liverpool School of Tropical Medicine and the University of "
    "Cape Town within three months of acceptance, and each repository record will carry the "
    "article's digital object identifier, its date of acceptance and the author identifiers listed "
    "on the title page."
)

CONTRIBUTION = (
    "Contribution of this review. The originality of this review is that it places each named "
    "proxy on two independent axes, its prominence in the literature and the evidence that it has "
    "been validated, instead of ranking proxies by how often they are published, and that it then "
    "tests whether that placement survives resampling. Its significance is that of 37 coded "
    "proxies only six hold a leading place in at least 93% of 2,000 bootstrap resamples, that the "
    "share of a proxy's studies reporting any validation is unrelated to its prominence "
    "(ρ = −0.06), and that Sub-Saharan Africa is the setting of 12 studies (1.7%) with no "
    "named proxy tested in more than 4, so the regions whose exposure is least characterised are "
    "also those whose proxies are least tested. Its rigour rests on a dual-database corpus of "
    "2,217 unique records reduced to 692 under screening rules published in full, a blinded audit "
    "of those rules at a precision of 0.75 and a negative predictive value of 0.91, three-pass "
    "deduplication, bootstrap intervals on every reported rate, and the explicit finding that the "
    "review's own headline rank correlation (ρ = 0.93) is largely constructional rather than "
    "empirical. The evidence map is offered as a reference point for proxy selection and for the "
    "design of personal outdoor exposure indicators."
)

PATHWAY = (
    "Pathway to application. This evidence map was assembled to inform a specific downstream use "
    "and is already serving it: the selection of candidate predictors for a geospatial composite "
    "indicator of personal outdoor exposure to fine particulate matter, now being developed and "
    "validated against measured personal exposure in the Gambia, Kenya and Mozambique. Two "
    "findings transfer directly. Proxies whose standing does not survive resampling are not "
    "treated as primary predictors, and the scarcity of Sub-Saharan validation is treated as a "
    "reason to validate locally rather than as grounds for assuming that performance reported "
    "elsewhere carries over. Beyond that programme, the coded corpus and the evidence map are "
    "released so that other groups can reuse the validation ledger for their own regions and proxy "
    "sets, and so that the map can be extended as new validation studies appear."
)

SEARCH_NEEDLE = "and the sensitivity search 1,483 and 211."
SEARCH_PAYLOAD = (
    SEARCH_NEEDLE[:-1] + ". The Boolean search string used in each database, the date on which it "
    "was executed and the count it returned are archived in full in the public deposit, so that "
    "the identification step can be repeated independently."
)

REVISIONS = [
    ("D1", "replace_para", "Data and code availability.", DATA_CODE),
    ("D2", "replace_para", "Funding. No funding was acquired for this study", FUNDING, [OPEN_ACCESS]),
    ("D3", "insert_before", "2. Materials and methods", [CONTRIBUTION]),
    ("D4", "replace_text", SEARCH_NEEDLE, SEARCH_PAYLOAD),
    # placed at the end of the conclusions, immediately before the Declarations heading,
    # so the pathway closes the argument instead of interrupting it
    ("D5", "insert_before", "Declarations", [PATHWAY]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-o", "--out")
    ap.add_argument("--track", action="store_true")
    ap.add_argument("--author", default="Handsome Nyoni")
    a = ap.parse_args()

    M.REVISIONS = REVISIONS
    M.TRACK["on"] = a.track
    M.TRACK["author"] = a.author
    M.TRACK["date"] = "2026-11-08T00:00:00Z"
    if a.track:
        print(f'recording changes as tracked, author "{a.author}"\n')

    tgt = Path(a.target)
    with zipfile.ZipFile(tgt) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    rep = M.run(root, apply=a.apply)
    if a.apply:
        out = Path(a.out) if a.out else tgt.with_name(tgt.stem + "_REF.docx")
        new_xml = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
        with zipfile.ZipFile(tgt) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    data = new_xml
                zout.writestr(item, data)
        print(f"wrote {out}")
    ok = sum(1 for r in rep if r[2] == "OK")
    print(f"\n{'id':4s} {'kind':14s} {'status':14s} needle")
    for rid, kind, status, nn in rep:
        print(f"{rid:4s} {kind:14s} {status:14s} {nn}")
    print(f"\n{ok}/{len(rep)} matched")
    return 0 if ok == len(rep) else 1


if __name__ == "__main__":
    sys.exit(main())

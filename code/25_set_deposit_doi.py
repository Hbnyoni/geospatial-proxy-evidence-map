#!/usr/bin/env python3
"""Replace the deposit DOI placeholder with the real one, everywhere it appears.

    python3 scripts/25_set_deposit_doi.py 10.5281/zenodo.1234567
"""
from __future__ import annotations
import re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "10.5281/zenodo.XXXXXXX"
DOCX = [ROOT / "manuscript/Geospatial_Proxy_Bibliometric_Review_REVISED_TRACKED_HBN_281026.docx",
        ROOT / "manuscript/Geospatial_Proxy_Bibliometric_Review_REVISED_HBN_281026.docx"]
SEND = ROOT / "review/revision_2026-10-27/TO_SEND"
PLAIN = [ROOT / "scripts/21_ref_declarations.py", ROOT / "review/zenodo_deposit/README.md"]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    doi = sys.argv[1].strip().replace("https://doi.org/", "")
    if not re.fullmatch(r"10\.5281/zenodo\.\d+", doi):
        print(f"error: {doi!r} is not a Zenodo DOI of the form 10.5281/zenodo.1234567")
        return 1

    n = 0
    for f in DOCX:
        with zipfile.ZipFile(f) as z:
            d = z.read("word/document.xml").decode("utf8")
        if PLACEHOLDER not in d:
            print(f"  {f.name}: placeholder not present, skipped")
            continue
        new = d.replace(PLACEHOLDER, doi)
        tmp = f.with_suffix(".tmp")
        with zipfile.ZipFile(f) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for it in zin.infolist():
                zout.writestr(it, new.encode("utf8") if it.filename == "word/document.xml"
                              else zin.read(it.filename))
        tmp.replace(f)
        print(f"  {f.name}: set")
        n += 1
    for f in PLAIN:
        if f.exists() and PLACEHOLDER in f.read_text():
            f.write_text(f.read_text().replace(PLACEHOLDER, doi))
            print(f"  {f.name}: set")
            n += 1
    tracked = DOCX[0]
    if (SEND / tracked.name).exists():
        (SEND / tracked.name).write_bytes(tracked.read_bytes())
        print(f"  TO_SEND/{tracked.name}: refreshed")
    print(f"\n{n} files updated to {doi}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

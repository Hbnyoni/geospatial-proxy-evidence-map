#!/usr/bin/env python3
"""Upload review/zenodo_deposit to Zenodo as a DRAFT and reserve its DOI.

This never publishes. Publishing a deposit is irreversible: the DOI is minted, the files become
public and Zenodo does not allow deletion afterwards. So this script stops at a draft with a
reserved DOI, which is enough to put the real DOI in the manuscript, and leaves the publish button
to you in the web interface once you have looked at what was uploaded.

The token is read from the environment and never written to disk or echoed:

    export ZENODO_TOKEN=...                     # from zenodo.org/account/settings/applications
    python3 scripts/24_zenodo_upload.py --sandbox   # rehearse on sandbox.zenodo.org first
    python3 scripts/24_zenodo_upload.py             # the real thing, still a draft

Create the token with the deposit:write and deposit:actions scopes. Sandbox needs its own, separate
token from sandbox.zenodo.org.
"""
from __future__ import annotations
import argparse, json, os, sys, zipfile
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
DEP = ROOT / "review" / "zenodo_deposit"
# browsable at the top of the record; the bulk goes up as one archive
TOP = ["README.md", "LICENSE.txt", "SEARCH_STRATEGY.md", "WITHHELD_FIELDS.md", "CITATION.cff"]
BUNDLE_DIRS = ["corpus", "tables", "code", "networks"]
BUNDLE = "bibliometric_evidence_map_data_and_code.zip"


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def make_bundle(out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for d in BUNDLE_DIRS:
            for p in sorted((DEP / d).rglob("*")):
                if p.is_file():
                    z.write(p, p.relative_to(DEP).as_posix())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", action="store_true", help="use sandbox.zenodo.org")
    ap.add_argument("--deposition", help="add files to an existing draft id instead of creating one")
    a = ap.parse_args()

    token = os.environ.get("ZENODO_TOKEN", "").strip()
    if not token:
        die("ZENODO_TOKEN is not set. Create one at zenodo.org/account/settings/applications "
            "with the deposit:write and deposit:actions scopes, then export it.")
    base = "https://sandbox.zenodo.org" if a.sandbox else "https://zenodo.org"
    if not DEP.exists():
        die(f"{DEP} does not exist; run scripts/22_build_deposit.py first")
    meta = json.loads((DEP / "zenodo.json").read_text())

    s = requests.Session()
    s.params = {"access_token": token}

    if a.deposition:
        r = s.get(f"{base}/api/deposit/depositions/{a.deposition}", timeout=60)
    else:
        r = s.post(f"{base}/api/deposit/depositions", json={}, timeout=60)
    if r.status_code in (401, 403):
        die(f"Zenodo rejected the token ({r.status_code}). Two usual causes: the token is for the "
            "other site (a sandbox.zenodo.org token does not work on zenodo.org, or vice versa), "
            "or it lacks the deposit:write and deposit:actions scopes. Create a fresh one at "
            f"{base}/account/settings/applications.")
    if r.status_code not in (200, 201):
        die(f"creating the draft failed: {r.status_code} {r.text[:300]}")
    dep = r.json()
    dep_id, bucket = dep["id"], dep["links"]["bucket"]
    print(f"draft {dep_id} on {base}")

    bundle = make_bundle(Path(os.environ.get("TMPDIR", "/tmp")) / BUNDLE)
    uploads = [(n, DEP / n) for n in TOP if (DEP / n).exists()] + [(BUNDLE, bundle)]
    for name, path in uploads:
        with open(path, "rb") as fh:
            u = s.put(f"{bucket}/{name}", data=fh, timeout=1800)
        if u.status_code not in (200, 201):
            die(f"uploading {name} failed: {u.status_code} {u.text[:200]}")
        print(f"  uploaded {name} ({path.stat().st_size/1e6:.2f} MB)")

    payload = {"metadata": {
        "title": meta["title"],
        "upload_type": meta["upload_type"],
        "description": meta["description"],
        "creators": meta["creators"],
        "keywords": meta["keywords"],
        "access_right": meta["access_right"],
        "license": meta["license"],
        "prereserve_doi": True,
    }}
    m = s.put(f"{base}/api/deposit/depositions/{dep_id}", json=payload, timeout=120)
    if m.status_code != 200:
        die(f"setting metadata failed: {m.status_code} {m.text[:300]}")
    pre = m.json()["metadata"].get("prereserve_doi") or {}
    doi = pre.get("doi", "")

    print("\nDRAFT ONLY, nothing is public yet.")
    print(f"  reserved DOI : {doi or '(none returned; open the draft and reserve it there)'}")
    print(f"  review draft : {base}/deposit/{dep_id}")
    if doi:
        print(f"\nPut it in the manuscript:\n  python3 scripts/25_set_deposit_doi.py {doi}")
    print("\nThen publish from the web page above once you are satisfied. Publishing cannot be "
          "undone: the DOI is minted and the files cannot be withdrawn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

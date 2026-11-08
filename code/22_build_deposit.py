#!/usr/bin/env python3
"""Assemble the public deposit the Data and code availability statement promises.

The statement in the manuscript is only honest if the archive exists and contains what it claims.
This builds that archive.

One constraint shapes the whole package. The corpus was retrieved from Scopus and Web of Science
under licences that permit redistributing factual bibliographic fields and our own coding, but not
the abstracts, the database index keywords or the cited-reference lists. Those three columns are
dropped from the record-level export and the reason is recorded in the deposit, so a reader can see
what was withheld and why rather than wondering whether the corpus is complete.

    python3 scripts/22_build_deposit.py            # build into review/zenodo_deposit
"""
from __future__ import annotations
import json, pickle, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _search_strings as SS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review" / "zenodo_deposit"

# Scopus and Web of Science licence terms cover these: they are the databases' own content, not ours.
WITHHELD = {
    "abstract": "Publisher abstract. Covered by the Scopus and Web of Science licence terms.",
    "kw_index": "Database index keywords. Proprietary indexing, not author-supplied.",
    "ref_keys": "Cited-reference lists. The most licence-restricted field in either export.",
    "affiliations": "Raw affiliation strings; the derived aff_countries field is published instead.",
    "corresp": "Corresponding-author contact string; the derived corr_country is published instead.",
    "kw_author": "Author keywords, redistributed only as the aggregate counts in tables/.",
}

TITLE = ("Geospatial proxy indicators for air-pollution exposure assessment: "
         "screened corpus, coding, evidence map and analysis code")

AUTHORS = [
    ("Nyoni", "Handsome Bongani", "Midlands State University; University of Cape Town"),
    ("Mphuthi", "Siphiwe", "University of Cape Town"),
    ("Makanga", "Prestige Tatenda",
     "Midlands State University; Liverpool School of Tropical Medicine; CeSHHAR Zimbabwe"),
]


def build_corpus_csv(dest: Path) -> tuple[int, int]:
    with open(ROOT / "data" / "records_coded.pkl", "rb") as f:
        df = pickle.load(f)
    keep = [c for c in df.columns if c not in WITHHELD]
    missing = [c for c in WITHHELD if c not in df.columns]
    if missing:
        print(f"note: columns already absent, nothing to withhold: {missing}")
    df[keep].to_csv(dest, index=False)
    return len(df), len(keep)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "corpus").mkdir(parents=True)
    (OUT / "tables").mkdir()
    (OUT / "code").mkdir()
    (OUT / "networks").mkdir()

    n_rec, n_col = build_corpus_csv(OUT / "corpus" / "screened_corpus_coded.csv")

    # screening workbooks, as actually filled in during screening
    wb = ROOT.parent / "Scopus"
    for name in ("screening_main_corpus.xlsx", "screening_sensitivity_unique.xlsx"):
        if (wb / name).exists():
            shutil.copy(wb / name, OUT / "corpus" / name)

    # the small JSON records behind the reported numbers; the .pkl caches are deliberately
    # excluded, because unpickling executes code and an archive should be safe to open
    for j in sorted((ROOT / "data").glob("*.json")):
        shutil.copy(j, OUT / "corpus" / j.name)

    for t in sorted((ROOT / "tables").glob("*.csv")):
        shutil.copy(t, OUT / "tables" / t.name)
    if (ROOT / "manuscript" / "Supplementary_Tables.xlsx").exists():
        shutil.copy(ROOT / "manuscript" / "Supplementary_Tables.xlsx", OUT / "tables")

    for p in sorted((ROOT / "scripts").glob("*.py")):
        shutil.copy(p, OUT / "code" / p.name)
    for p in sorted((ROOT / "vosviewer").glob("*")):
        if p.is_file():
            shutil.copy(p, OUT / "networks" / p.name)

    flow = json.loads((ROOT / "data" / "flow_identification.json").read_text())

    (OUT / "LICENSE.txt").write_text(
        "Creative Commons Attribution 4.0 International (CC BY 4.0)\n"
        "https://creativecommons.org/licenses/by/4.0/legalcode\n\n"
        "This licence covers the coding, the derived tables, the networks and the code in this\n"
        "deposit, which are the authors' own work. It does not and cannot extend to bibliographic\n"
        "records owned by Scopus or Web of Science; the fields those licences cover have been\n"
        "withheld and are listed in WITHHELD_FIELDS.md.\n"
    )

    (OUT / "WITHHELD_FIELDS.md").write_text(
        "# Fields withheld from the record-level export\n\n"
        "The corpus was retrieved from Scopus and Web of Science. Their licences permit\n"
        "redistribution of factual bibliographic fields and of our own coding, but not of the\n"
        "databases' own content. The following columns are therefore absent from\n"
        "`corpus/screened_corpus_coded.csv`. Every one can be restored by any licence holder who\n"
        "re-executes the searches in `SEARCH_STRATEGY.md`.\n\n"
        + "".join(f"- **{k}** — {v}\n" for k, v in WITHHELD.items())
        + f"\n{n_rec} records and {n_col} columns are published.\n"
    )

    screened = {"primary": 892, "sensitivity": 1325}
    included = {"primary": 263, "sensitivity": 429}
    body = [
        "# Search strategy\n",
        "Four searches were run across two databases. The term blocks are those recorded in",
        "Table 1 of the manuscript; what follows writes them out in each database's own syntax.",
        "Read the provenance note under each one: they are not all of equal standing, and the",
        "difference is stated rather than smoothed over.\n",
        "## Execution dates\n",
        SS.DATES + "\n",
        "## Filters\n",
        SS.FILTERS + "\n",
    ]
    for name, query, prov, key in SS.SEARCHES:
        body += [f"## {name}\n", "```", query, "```\n",
                 f"**Provenance.** {prov}\n",
                 (f"**Records returned.** {flow[key]}\n" if key else
                  "**Records returned.** Not recorded separately; included in the combined "
                  "sensitivity counts.\n")]
    body += [
        "## What each stage contributed\n",
        "| Stage | Scopus | Web of Science | Unique after de-duplication | Included after screening |",
        "|---|---|---|---|---|",
        f"| Primary | {flow['scopus_primary']} | {flow['wos_primary']} | "
        f"{screened['primary']} | {included['primary']} |",
        f"| Sensitivity | {flow['scopus_sens']} | {flow['wos_sens']} | "
        f"{screened['sensitivity']} | {included['sensitivity']} |",
        f"| Combined | {flow['scopus_primary'] + flow['scopus_sens']} | "
        f"{flow['wos_primary'] + flow['wos_sens']} | "
        f"{screened['primary'] + screened['sensitivity']} | "
        f"{included['primary'] + included['sensitivity']} |\n",
        "The sensitivity searches contributed 429 of the 692 included studies, 62%, which is why",
        "the review reports that a proxy-worded search alone misses most of the field.\n",
        "## Identification counts\n",
        "Machine-generated from `corpus/flow_identification.json`; these match the PRISMA flow",
        "reported in the manuscript.\n",
    ]
    body += [f"- `{k}`: {v}" for k, v in flow.items()]
    (OUT / "SEARCH_STRATEGY.md").write_text("\n".join(body) + "\n")

    (OUT / "CITATION.cff").write_text(
        "cff-version: 1.2.0\n"
        "message: If you use this deposit, please cite it and the article it supports.\n"
        f'title: "{TITLE}"\n'
        "type: dataset\n"
        "license: CC-BY-4.0\n"
        "authors:\n"
        + "".join(f'  - family-names: "{f}"\n    given-names: "{g}"\n    affiliation: "{a}"\n'
                  f"    # orcid: https://orcid.org/0000-0000-0000-0000  # TODO add\n"
                  for f, g, a in AUTHORS)
        + "keywords:\n"
        + "".join(f"  - {k}\n" for k in ("air pollution", "exposure assessment",
                                         "geospatial proxy", "bibliometrics", "evidence map",
                                         "validation", "sub-Saharan Africa"))
    )

    (OUT / "zenodo.json").write_text(json.dumps({
        "title": TITLE,
        "upload_type": "dataset",
        "license": "cc-by-4.0",
        "access_right": "open",
        "creators": [{"name": f"{g} {f}", "affiliation": a} for f, g, a in AUTHORS],
        "description": (
            "Screened corpus, study-level coding, derived tables, co-occurrence networks and "
            "analysis code for a bibliometric and validation evidence map of geospatial proxy "
            f"indicators used in air-pollution exposure assessment. {n_rec} unique records were "
            "screened and 692 included. Fields owned by Scopus and Web of Science are withheld "
            "and listed in WITHHELD_FIELDS.md."),
        "keywords": ["air pollution", "exposure assessment", "geospatial proxy",
                     "bibliometrics", "evidence map", "validation", "sub-Saharan Africa"],
    }, indent=2) + "\n")

    counts = {d.name: sum(1 for _ in d.rglob("*") if _.is_file())
              for d in sorted(OUT.iterdir()) if d.is_dir()}
    (OUT / "README.md").write_text(
        f"# {TITLE}\n\n"
        "This deposit is the archive referenced by the Data and code availability statement of the\n"
        "article. It is released under CC BY 4.0.\n\n"
        "## What is here\n\n"
        f"- `corpus/screened_corpus_coded.csv` — {n_rec} unique screened records, {n_col} columns:\n"
        "  bibliographic identifiers, the screening decision and its reason, and the full study-level\n"
        "  coding (proxy families and named proxies, pollutants, methods, validation designs,\n"
        "  personal-exposure target, study countries and regions, inclusion flags).\n"
        "- `corpus/screening_*.xlsx` — the screening workbooks as completed, with per-record\n"
        "  title-abstract and full-text decisions.\n"
        "- `corpus/*.json` — the identification flow, agreement, audit, robustness and evidence-map\n"
        "  records behind every number reported in the article.\n"
        f"- `tables/` — {counts.get('tables', 0)} derived tables, one per reported table or figure.\n"
        f"- `code/` — {counts.get('code', 0)} scripts that rebuild every number, table and figure\n"
        "  from the raw exports.\n"
        f"- `networks/` — {counts.get('networks', 0)} node and edge files for the co-occurrence and\n"
        "  co-citation networks, readable in VOSviewer.\n"
        "- `SEARCH_STRATEGY.md` — the search strings, execution dates and returned counts.\n"
        "- `WITHHELD_FIELDS.md` — what was withheld under database licence terms, and why.\n\n"
        "## What is not here\n\n"
        "Abstracts, database index keywords and cited-reference lists are the property of Scopus and\n"
        "Web of Science and are withheld. The `.pkl` caches in the working tree are also excluded:\n"
        "unpickling executes code, and an archive should be safe for a stranger to open. Everything\n"
        "they held is published here as CSV or JSON.\n\n"
        "## Reproducing the analysis\n\n"
        "Re-execute the four searches in `SEARCH_STRATEGY.md`, export them, then run the scripts in\n"
        "`code/` in numerical order. The identification counts in `corpus/flow_identification.json`\n"
        "are the check that the corpus was rebuilt correctly.\n"
    )

    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT}")
    print(f"  {files} files, {size/1e6:.1f} MB")
    print(f"  corpus: {n_rec} records x {n_col} published columns "
          f"({len(WITHHELD)} fields withheld under database licence)")
    for d, c in counts.items():
        print(f"  {d}/: {c} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

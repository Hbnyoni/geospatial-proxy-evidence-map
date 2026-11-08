# Geospatial proxy indicators for air-pollution exposure assessment: screened corpus, coding, evidence map and analysis code

This repository is the data and code archive referenced by the Data and code availability
statement of the article, submitted to *Atmospheric Pollution Research* as a Review.
It is released under CC BY 4.0.

**Article.** Nyoni HB, Mphuthi S, Makanga PT. Geospatial proxy indicators for air-pollution
exposure assessment: a bibliometric and validation evidence map with implications for
Sub-Saharan Africa. Under review.

**Archive DOI.** [10.5281/zenodo.24053000](https://doi.org/10.5281/zenodo.24053000)

## What is here

- `corpus/screened_corpus_coded.csv` — 2217 unique screened records, 43 columns:
  bibliographic identifiers, the screening decision and its reason, and the full study-level
  coding (proxy families and named proxies, pollutants, methods, validation designs,
  personal-exposure target, study countries and regions, inclusion flags).
- `corpus/screening_*.xlsx` — the screening workbooks as completed, with per-record
  title-abstract and full-text decisions.
- `corpus/*.json` — the identification flow, agreement, audit, robustness and evidence-map
  records behind every number reported in the article.
- `tables/` — 32 derived tables, one per reported table or figure.
- `code/` — 31 scripts that rebuild every number, table and figure
  from the raw exports.
- `networks/` — 6 node and edge files for the co-occurrence and
  co-citation networks, readable in VOSviewer.
- `SEARCH_STRATEGY.md` — the search strings, execution dates and returned counts.
- `WITHHELD_FIELDS.md` — what was withheld under database licence terms, and why.

## What is not here

Abstracts, database index keywords and cited-reference lists are the property of Scopus and
Web of Science and are withheld. The `.pkl` caches in the working tree are also excluded:
unpickling executes code, and an archive should be safe for a stranger to open. Everything
they held is published here as CSV or JSON.

## Reproducing the analysis

Re-execute the four searches in `SEARCH_STRATEGY.md`, export them, then run the scripts in
`code/` in numerical order. The identification counts in `corpus/flow_identification.json`
are the check that the corpus was rebuilt correctly.

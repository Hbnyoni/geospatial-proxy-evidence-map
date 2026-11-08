# Fields withheld from the record-level export

The corpus was retrieved from Scopus and Web of Science. Their licences permit
redistribution of factual bibliographic fields and of our own coding, but not of the
databases' own content. The following columns are therefore absent from
`corpus/screened_corpus_coded.csv`. Every one can be restored by any licence holder who
re-executes the searches in `SEARCH_STRATEGY.md`.

- **abstract** — Publisher abstract. Covered by the Scopus and Web of Science licence terms.
- **kw_index** — Database index keywords. Proprietary indexing, not author-supplied.
- **ref_keys** — Cited-reference lists. The most licence-restricted field in either export.
- **affiliations** — Raw affiliation strings; the derived aff_countries field is published instead.
- **corresp** — Corresponding-author contact string; the derived corr_country is published instead.
- **kw_author** — Author keywords, redistributed only as the aggregate counts in tables/.

2217 records and 43 columns are published.

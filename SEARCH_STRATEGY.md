# Search strategy

Four searches were run across two databases. The term blocks are those recorded in
Table 1 of the manuscript; what follows writes them out in each database's own syntax.
Read the provenance note under each one: they are not all of equal standing, and the
difference is stated rather than smoothed over.

## Execution dates

The exports were processed into the corpus summary dated 1 April 2026, which is the latest date the searches can have been run. The exact execution date of each search is NOT recorded and must be read off the Scopus and Web of Science search histories before this deposit is published.

## Filters

Document types were restricted to Article and Review in both databases. No language or date restriction was applied at the database stage. Web of Science searches used the topic field TS= in place of TITLE-ABS-KEY.

## Primary search, Scopus

```
TITLE-ABS-KEY(
    ("air pollution" OR "air quality" OR PM2.5
     OR PM10 OR NO2 OR ozone OR "black carbon")

    AND

    ("proxy indicator*" OR "proxy measure*"
     OR "proxy variable*" OR surrogate*
     OR "exposure proxy*" OR "pollution proxy*"
     OR "geospatial proxy*")

    AND

    (geospatial OR spatial OR satellite
     OR "remote sensing" OR GIS
     OR "land use regression" OR AOD OR NDVI
     OR VIIRS OR LST OR "road density"
     OR "distance to road*" OR "population density"
     OR meteorolog* OR ERA5)

    AND

    (assess* OR measur* OR monitor*
     OR estimat* OR model* OR predict*
     OR validate*)
)
```

**Provenance.** Written out in database syntax from the four term blocks recorded in Table 1 of the manuscript. The strategy is documented; the database search-history entry was not retained, so confirm against the search history before relying on it as a verbatim export.

**Records returned.** 729

## Primary search, Web of Science

```
TS=(
    ("air pollution" OR "air quality" OR PM2.5
     OR PM10 OR NO2 OR ozone OR "black carbon")

    AND

    ("proxy indicator*" OR "proxy measure*"
     OR "proxy variable*" OR surrogate*
     OR "exposure proxy*" OR "pollution proxy*"
     OR "geospatial proxy*")

    AND

    (geospatial OR spatial OR satellite
     OR "remote sensing" OR GIS
     OR "land use regression" OR AOD OR NDVI
     OR VIIRS OR LST OR "road density"
     OR "distance to road*" OR "population density"
     OR meteorolog* OR ERA5)

    AND

    (assess* OR measur* OR monitor*
     OR estimat* OR model* OR predict*
     OR validate*)
)
```

**Provenance.** Written out in database syntax from the four term blocks recorded in Table 1 of the manuscript. The strategy is documented; the database search-history entry was not retained, so confirm against the search history before relying on it as a verbatim export.

**Records returned.** 645

## Sensitivity search, expanded proxy terminology, Scopus

```
TITLE-ABS-KEY(
    ("air pollution" OR "air quality" OR PM2.5
     OR PM10 OR NO2 OR ozone OR "black carbon")

    AND

    (predictor* OR "spatial predictor*"
     OR "environmental predictor*"
     OR covariate* OR "geospatial covariate*"
     OR indicator* OR "environmental indicator*")

    AND

    (geospatial OR spatial OR satellite
     OR "remote sensing" OR GIS
     OR "land use regression" OR AOD OR NDVI
     OR VIIRS OR LST OR "road density"
     OR "distance to road*" OR "population density"
     OR meteorolog* OR ERA5)

    AND

    (assess* OR measur* OR monitor*
     OR estimat* OR model* OR predict*
     OR validate*)
)
```

**Provenance.** Reconstructs the sensitivity logic described in Table 1, whose proxy block adds predictor, covariate and indicator terminology. Not a verbatim search-history export.

**Records returned.** 1483

## Sensitivity search, expanded proxy terminology, Web of Science

```
TS=(
    ("air pollution" OR "air quality" OR PM2.5
     OR PM10 OR NO2 OR ozone OR "black carbon")

    AND

    (predictor* OR "spatial predictor*"
     OR "environmental predictor*"
     OR covariate* OR "geospatial covariate*"
     OR indicator* OR "environmental indicator*")

    AND

    (geospatial OR spatial OR satellite
     OR "remote sensing" OR GIS
     OR "land use regression" OR AOD OR NDVI
     OR VIIRS OR LST OR "road density"
     OR "distance to road*" OR "population density"
     OR meteorolog* OR ERA5)

    AND

    (assess* OR measur* OR monitor*
     OR estimat* OR model* OR predict*
     OR validate*)
)
```

**Provenance.** Reconstructs the sensitivity logic described in Table 1, whose proxy block adds predictor, covariate and indicator terminology. Not a verbatim search-history export.

**Records returned.** 211

## Supplementary sensitivity search, named geospatial proxies, both databases

```
TITLE-ABS-KEY(
    ("air pollution" OR "air quality" OR PM2.5
     OR PM10 OR NO2 OR ozone OR "black carbon")

    AND

    ("Aerosol Optical Depth" OR AOD
     OR NDVI OR VIIRS
     OR "land surface temperature" OR LST
     OR "road density" OR "distance to road*"
     OR "Sentinel-5P" OR TROPOMI)

    AND

    (geospatial OR spatial OR satellite
     OR "remote sensing" OR GIS
     OR "land use regression" OR AOD OR NDVI
     OR VIIRS OR LST OR "road density"
     OR "distance to road*" OR "population density"
     OR meteorolog* OR ERA5)

    AND

    (assess* OR measur* OR monitor*
     OR estimat* OR model* OR predict*
     OR validate*)
)
```

**Provenance.** An additional supplementary search for named geospatial proxies. This one is NOT in Table 1, and its separate return is not recorded: its records are inside the combined sensitivity counts below. Treat it as documented intent, not as a reproducible count.

**Records returned.** Not recorded separately; included in the combined sensitivity counts.

## What each stage contributed

| Stage | Scopus | Web of Science | Unique after de-duplication | Included after screening |
|---|---|---|---|---|
| Primary | 729 | 645 | 892 | 263 |
| Sensitivity | 1483 | 211 | 1325 | 429 |
| Combined | 2212 | 856 | 2217 | 692 |

The sensitivity searches contributed 429 of the 692 included studies, 62%, which is why
the review reports that a proxy-worded search alone misses most of the field.

## Identification counts

Machine-generated from `corpus/flow_identification.json`; these match the PRISMA flow
reported in the manuscript.

- `scopus_primary`: 729
- `wos_primary`: 645
- `scopus_sens`: 1483
- `wos_sens`: 211
- `primary_identified`: 1374
- `primary_doctype_excluded`: 0
- `primary_after_doctype`: 1374
- `primary_dup_doi`: 468
- `primary_dup_title`: 13
- `primary_dup_fuzzy`: 1
- `primary_unique`: 892
- `primary_both_db`: 480
- `primary_scopus_only`: 247
- `primary_wos_only`: 165
- `sens_identified`: 1694
- `sens_doctype_excluded`: 142
- `sens_after_doctype`: 1552
- `sens_dup_within`: 4
- `sens_unique_within`: 1548
- `sens_overlap_primary`: 223
- `sens_unique`: 1325
- `near_pairs_for_review`: 2

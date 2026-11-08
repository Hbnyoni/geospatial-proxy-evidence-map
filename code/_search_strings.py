"""The four database queries behind the corpus, with their provenance stated.

Provenance matters more than the strings here. Table 1 of the manuscript records the four term
blocks and what the sensitivity search changed, so the primary queries can be written out in
database syntax with confidence. The database search-history entries themselves were not kept, so
these are faithful renderings of a documented strategy rather than verbatim exports, and the
supplementary named-proxy query is not in Table 1 at all. Each string below says which it is. An
assessor who is told that is reading a reproducible method; one who is told nothing and later finds
out is reading an overclaim.
"""

POLLUTANT = '"air pollution" OR "air quality" OR PM2.5\n     OR PM10 OR NO2 OR ozone OR "black carbon"'
GEOSPATIAL = ('geospatial OR spatial OR satellite\n     OR "remote sensing" OR GIS\n'
              '     OR "land use regression" OR AOD OR NDVI\n     OR VIIRS OR LST OR "road density"\n'
              '     OR "distance to road*" OR "population density"\n     OR meteorolog* OR ERA5')
PURPOSE = ('assess* OR measur* OR monitor*\n     OR estimat* OR model* OR predict*\n     OR validate*')
PROXY = ('"proxy indicator*" OR "proxy measure*"\n     OR "proxy variable*" OR surrogate*\n'
         '     OR "exposure proxy*" OR "pollution proxy*"\n     OR "geospatial proxy*"')
EXPANDED = ('predictor* OR "spatial predictor*"\n     OR "environmental predictor*"\n'
            '     OR covariate* OR "geospatial covariate*"\n     OR indicator* OR "environmental indicator*"')
NAMED = ('"Aerosol Optical Depth" OR AOD\n     OR NDVI OR VIIRS\n'
         '     OR "land surface temperature" OR LST\n     OR "road density" OR "distance to road*"\n'
         '     OR "Sentinel-5P" OR TROPOMI')


def _q(field: str, block2: str) -> str:
    return (f"{field}(\n    ({POLLUTANT})\n\n    AND\n\n    ({block2})\n\n    AND\n\n"
            f"    ({GEOSPATIAL})\n\n    AND\n\n    ({PURPOSE})\n)")


DOCUMENTED = ("Written out in database syntax from the four term blocks recorded in Table 1 of the "
              "manuscript. The strategy is documented; the database search-history entry was not "
              "retained, so confirm against the search history before relying on it as a verbatim "
              "export.")
RECONSTRUCTED = ("Reconstructs the sensitivity logic described in Table 1, whose proxy block adds "
                 "predictor, covariate and indicator terminology. Not a verbatim search-history "
                 "export.")
SUPPLEMENTARY = ("An additional supplementary search for named geospatial proxies. This one is NOT "
                 "in Table 1, and its separate return is not recorded: its records are inside the "
                 "combined sensitivity counts below. Treat it as documented intent, not as a "
                 "reproducible count.")

SEARCHES = [
    ("Primary search, Scopus", _q("TITLE-ABS-KEY", PROXY), DOCUMENTED, "scopus_primary"),
    ("Primary search, Web of Science", _q("TS=", PROXY), DOCUMENTED, "wos_primary"),
    ("Sensitivity search, expanded proxy terminology, Scopus",
     _q("TITLE-ABS-KEY", EXPANDED), RECONSTRUCTED, "scopus_sens"),
    ("Sensitivity search, expanded proxy terminology, Web of Science",
     _q("TS=", EXPANDED), RECONSTRUCTED, "wos_sens"),
    ("Supplementary sensitivity search, named geospatial proxies, both databases",
     _q("TITLE-ABS-KEY", NAMED), SUPPLEMENTARY, None),
]

FILTERS = ("Document types were restricted to Article and Review in both databases. No language or "
           "date restriction was applied at the database stage. Web of Science searches used the "
           "topic field TS= in place of TITLE-ABS-KEY.")

DATES = ("The exports were processed into the corpus summary dated 1 April 2026, which is the latest "
         "date the searches can have been run. The exact execution date of each search is NOT "
         "recorded and must be read off the Scopus and Web of Science search histories before this "
         "deposit is published.")

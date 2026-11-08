"""Step 9 -- map the Objective 1 candidate set onto the literature ranking.

The 60 candidates searched in the Objective 1 forward selection (three road variables forced in, 57
searched) are taken from output/iterative/forward/forward_candidates_allproxies.csv; the variables
the selection kept from forward_selected_allproxies.csv. Each is matched by hand to the named proxy
of the bibliometric dictionary that it measures.

    python scripts/09_objective1_mapping.py -> tables/T_obj1_mapping.csv, tables/T_obj1_coverage.csv,
                                               data/obj1_mapping.json
"""
from __future__ import annotations
import json, re
from pathlib import Path
import pandas as pd

V2 = Path(__file__).resolve().parents[1]
FWD = Path("/PALS/CHEAQI_Composite_Indicator/output/iterative/forward")
FORCED = ["WRND_km_km2", "EH_m", "EM_m"]

# thesis variable -> literature named proxy (None: no counterpart in the dictionary)
MAP = {
    "WRND_km_km2": "Road density or length", "EH_m": "Distance or proximity to roads", "EM_m": "Distance or proximity to roads",
    "road_access_min_mean": "Distance or proximity to roads", "road_access_min_stdDev": "Distance or proximity to roads",
    "road_friction_mean": "Road density or length", "road_friction_stdDev": "Road density or length",
    "BuiltUp_mean": "Built-up or impervious surface", "BuiltUp_stdDev": "Built-up or impervious surface",
    "BuiltVol_mean": "Built-up or impervious surface", "BuiltVol_stdDev": "Built-up or impervious surface",
    "BuiltVol_nres_mean": "Industrial, commercial or port land", "BuiltVol_nres_stdDev": "Industrial, commercial or port land",
    "NDBI_mean": "Built-up or impervious surface", "NDBI_stdDev": "Built-up or impervious surface",
    "LandCover_mode": "Land use or land cover class", "LandCover_ndistinct": "Land use or land cover class",
    "SMOD_mean": "Settlement and socio-economic status", "SMOD_stdDev": "Settlement and socio-economic status",
    "POP_mean": "Population density", "POP_stdDev": "Population density",
    "VIIRS_NTL_mean": "Night-time lights", "VIIRS_NTL_stdDev": "Night-time lights",
    "Elevation_mean": "Elevation and terrain", "Elevation_stdDev": "Elevation and terrain",
    "Slope_mean": "Elevation and terrain", "Slope_stdDev": "Elevation and terrain",
    "NDVI_mean": "Vegetation index (NDVI, EVI)", "NDVI_stdDev": "Vegetation index (NDVI, EVI)",
    "NDWI_mean": "Other land-surface state", "NDWI_stdDev": "Other land-surface state", "Soil_Moist": "Other land-surface state",
    "LST_C": "Land surface temperature", "LSTN_C": "Land surface temperature",
    "AOD_MAIAC": "Aerosol optical depth", "AOD_S5P": "Aerosol optical depth",
    "NO2": "Tropospheric NO2 column", "CO": "Other satellite trace gas", "HCHO": "Other satellite trace gas", "SO2": "Other satellite trace gas",
    "BLH": "Boundary-layer height", "BLH_max": "Boundary-layer height", "BLH_min": "Boundary-layer height", "BLH_range": "Boundary-layer height",
    "WS": "Wind", "U10": "Wind", "V10": "Wind",
    "T2M": "Temperature", "T2M_MAX": "Temperature", "T2M_MIN": "Temperature", "DEW": "Humidity and precipitation",
    "RH": "Humidity and precipitation", "TP": "Humidity and precipitation", "EVAP": "Humidity and precipitation",
    "MSLP": "Stability, inversion, radiation", "SP": "Stability, inversion, radiation", "SSR": "Stability, inversion, radiation",
    "fire_5km": "Fire activity and burned area", "fire_10km": "Fire activity and burned area", "fire_25km": "Fire activity and burned area",
}


# ERA5 / ERA5-Land fields also count as the literature's 'reanalysis or NWP fields' proxy
REANALYSIS = {"BLH", "BLH_max", "BLH_min", "BLH_range", "WS", "U10", "V10", "T2M", "T2M_MAX", "T2M_MIN", "DEW", "RH", "TP", "EVAP",
              "MSLP", "SP", "SSR", "Soil_Moist"}


def main():
    cand = sorted(set(pd.read_csv(FWD / "forward_candidates_allproxies.csv")["var"]) | set(FORCED))
    sel = pd.read_csv(FWD / "forward_selected_allproxies.csv")
    pooled = sel[(sel.res == "raw") & (sel.pool == "KGM")]["vars"].iloc[0].split(" + ")
    any_pool = {v for s in sel[sel.res == "raw"]["vars"] for v in s.split(" + ")}
    missing = [c for c in cand if c not in MAP]
    assert not missing, f"unmapped candidates: {missing}"
    rk = pd.read_csv(V2 / "tables/T_proxy_ranking.csv").set_index("proxy")
    m = pd.DataFrame({"variable": cand})
    m["literature_proxy"] = m.variable.map(MAP)
    for c in ("family", "rank", "records", "validation_records", "spatial_or_external_val", "ssa_records", "priority", "dynamic"):
        m[c] = m.literature_proxy.map(rk[c])
    m["selected_pooled_KGM"] = m.variable.isin(pooled)
    m["selected_any_pool"] = m.variable.isin(any_pool)
    m.sort_values(["rank", "variable"]).to_csv(V2 / "tables/T_obj1_mapping.csv", index=False)

    named = rk[~rk["aggregate"]].reset_index()
    cov = pd.DataFrame({"literature_proxy": named.proxy, "rank": named["rank"], "family": named.family, "records": named.records,
                        "validated": named.validation_records, "ssa": named.ssa_records})
    cov["n_candidates"] = cov.literature_proxy.map(m.groupby("literature_proxy").size()).fillna(0).astype(int)
    cov.loc[cov.literature_proxy == "Reanalysis or NWP fields", "n_candidates"] = len(REANALYSIS & set(cand))
    cov["selected_any_pool"] = cov.literature_proxy.map(m.groupby("literature_proxy").selected_any_pool.any()).astype("boolean").fillna(False).astype(bool)
    cov.loc[cov.literature_proxy == "Reanalysis or NWP fields", "selected_any_pool"] = bool(REANALYSIS & any_pool)
    cov.to_csv(V2 / "tables/T_obj1_coverage.csv", index=False)

    top20 = cov.head(20)
    out = dict(
        n_candidates=len(cand), n_literature_proxies_covered=int((cov.n_candidates > 0).sum()), n_named=len(cov),
        top20_covered=int((top20.n_candidates > 0).sum()), top10_covered=int((cov.head(10).n_candidates > 0).sum()),
        top20_missing=top20[top20.n_candidates == 0].literature_proxy.tolist(),
        covered_low_ranked=cov[(cov.n_candidates > 0) & (cov["rank"] > cov.head(20)["rank"].max())].literature_proxy.tolist(),
        pooled_selected=[(v, MAP[v]) for v in pooled],
        selected_literature_proxies=sorted({MAP[v] for v in any_pool if v in MAP}),
        # the three road variables were forced into every set, so they are left out of this comparison
        selected_median_rank=float(m[m.selected_any_pool & ~m.variable.isin(FORCED)]["rank"].median()),
        unselected_median_rank=float(m[~m.selected_any_pool]["rank"].median()),
        n_selected_unforced=int((m.selected_any_pool & ~m.variable.isin(FORCED)).sum()),
        selected_dynamic_share=float(m[m.selected_any_pool & ~m.variable.isin(FORCED)].dynamic.mean()),
        unselected_dynamic_share=float(m[~m.selected_any_pool].dynamic.mean()),
    )
    (V2 / "data/obj1_mapping.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()

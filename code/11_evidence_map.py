#!/usr/bin/env python3
"""Two-dimensional evidence map, replacing the single priority score.

Written in response to the October 2026 supervisory review, which observed that
the validation-evidence score is built from counts that rise with a proxy's
frequency, so the prominence-validation correlation is partly constructional.
This script separates the two axes, reports validation as a rate with a
denominator and a Wilson interval, and tests the rank ordering for stability.
"""
import collections, itertools, json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("SC", ROOT / "scripts" / "02_screen_code.py")
SC = importlib.util.module_from_spec(spec)
SC.__name__ = "SC"
try:
    spec.loader.exec_module(SC)
except SystemExit:
    pass

TAB, DATA = ROOT / "tables", ROOT / "data"
inc = pickle.load(open(DATA / "records_coded.pkl", "rb"))
inc = inc[inc.included] if "included" in inc.columns else inc
print(f"corpus: {len(inc)} records")
val = inc[inc.validation & ~inc.is_review]
print(f"validation sub-corpus: {len(val)}")

# ---------------------------------------------------------------- the two axes
prox_list = sorted({p for L in inc.proxies for p in L})
pc = collections.Counter(p for L in inc.proxies for p in L)
P = nx.Graph()
for p in prox_list:
    P.add_node(p, n=pc[p])
for L in inc.proxies:
    for a, b in itertools.combinations(sorted(set(L)), 2):
        P.add_edge(a, b, weight=P[a][b]["weight"] + 1 if P.has_edge(a, b) else 1)
cent = nx.eigenvector_centrality_numpy(P, weight="weight")
vcount = collections.Counter(p for L in val.proxies for p in L)
STRONG = {"Spatial or blocked CV", "Independent or external validation"}
vstrong = collections.Counter(p for L, T in zip(val.proxies, val.val_types) for p in L if STRONG & set(T))
ssa_c = collections.Counter(p for L in inc[inc.ssa].proxies for p in L)
pers_c = collections.Counter(p for L in inc[inc.personal].proxies for p in L)
fam_of = {n: f for f, n, *_ in SC.PROXIES}

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return (max(0.0, c - h), min(1.0, c + h))

AGG = {"Land-use regression predictors", "Traffic (unspecified)", "Satellite remote sensing (general)"}
DYN_PROXY = {"Land surface temperature", "Vegetation index (NDVI, EVI)", "Traffic volume or intensity"}
rows = []
for p in prox_list:
    n, k, ks = pc[p], vcount.get(p, 0), vstrong.get(p, 0)
    lo, hi = wilson(k, n)
    slo, shi = wilson(ks, n)
    rows.append(dict(proxy=p, family=SC.FAM_LABEL[fam_of[p]], records=n, centrality=round(cent[p], 4),
                     validated=k, validation_rate=round(k / n, 3), val_lo=round(lo, 3), val_hi=round(hi, 3),
                     val_ci_width=round(hi - lo, 3), spatial_or_external=ks,
                     strong_rate=round(ks / n, 3), strong_lo=round(slo, 3), strong_hi=round(shi, 3),
                     personal=pers_c.get(p, 0), ssa=ssa_c.get(p, 0),
                     is_aggregate=p in AGG,
                     dynamic_family=fam_of[p] in SC.DYNAMIC_FAM,
                     dynamic_proxy=fam_of[p] in SC.DYNAMIC_FAM or p in DYN_PROXY))
R = pd.DataFrame(rows)
pr = lambda s: s.rank(pct=True)
R["prom_freq_pct"] = pr(R.records).round(3)
R["prom_cent_pct"] = pr(R.centrality).round(3)
R["prominence"] = ((R.prom_freq_pct + R.prom_cent_pct) / 2).round(3)
# the published composite, kept for comparability
R["validation_score_counts"] = ((pr(R.validated) + pr(R.spatial_or_external)) / 2).round(3)
R["priority_published"] = ((R.prominence + R.validation_score_counts) / 2).round(3)

# ------------------------------------------------- is the 0.93 constructional?
out = {}
rho = lambda a, b: (round(float(stats.spearmanr(a, b).statistic), 3), float(stats.spearmanr(a, b).pvalue))
out["rho_prominence_vs_validation_counts"] = rho(R.prominence, R.validation_score_counts)
out["rho_records_vs_validated_counts"] = rho(R.records, R.validated)
out["rho_prominence_vs_validation_rate"] = rho(R.prominence, R.validation_rate)
out["rho_records_vs_validation_rate"] = rho(R.records, R.validation_rate)
out["rho_prominence_vs_strong_rate"] = rho(R.prominence, R.strong_rate)
# Kendall partial: prominence vs validation counts, holding records
res_v = stats.rankdata(R.validated) - np.polyval(np.polyfit(stats.rankdata(R.records), stats.rankdata(R.validated), 1), stats.rankdata(R.records))
res_p = stats.rankdata(R.prominence) - np.polyval(np.polyfit(stats.rankdata(R.records), stats.rankdata(R.prominence), 1), stats.rankdata(R.records))
out["partial_rho_prom_val_given_records"] = rho(res_p, res_v)

# well-measured subset (>=20 records), as reported in the manuscript
W = R[(R.records >= 20) & ~R["is_aggregate"]]
out["n_wellmeasured"] = int(len(W))
out["wellmeasured_rate_min"] = [W.loc[W.validation_rate.idxmin(), "proxy"], float(W.validation_rate.min())]
out["wellmeasured_rate_max"] = [W.loc[W.validation_rate.idxmax(), "proxy"], float(W.validation_rate.max())]
out["wellmeasured_rate_median"] = round(float(W.validation_rate.median()), 3)
out["wellmeasured_rho_records_vs_rate"] = rho(W.records, W.validation_rate)
out["wellmeasured_strong_rate_median"] = round(float(W.strong_rate.median()), 3)
out["wellmeasured_strong_rate_max"] = [W.loc[W.strong_rate.idxmax(), "proxy"], float(W.strong_rate.max())]
out["wellmeasured_n_zero_strong"] = int((W.spatial_or_external == 0).sum())

# ----------------------------------------------------------------- quadrants
named = R[~R["is_aggregate"]].copy()
pm, vm = named.prominence.median(), named.validation_rate.median()
out["median_prominence"] = round(float(pm), 3)
out["median_validation_rate"] = round(float(vm), 3)
def quad(r):
    hi_p, hi_v = r.prominence >= pm, r.validation_rate >= vm
    return ("Established" if hi_p and hi_v else "Prominent but weakly validated" if hi_p
            else "Validated but peripheral" if hi_v else "Under-studied")
named["quadrant"] = named.apply(quad, axis=1)
R["quadrant"] = R.proxy.map(dict(zip(named.proxy, named.quadrant))).fillna("Aggregate (not mapped)")
out["quadrant_counts"] = named.quadrant.value_counts().to_dict()
for q in sorted(named.quadrant.unique()):
    sub = named[named.quadrant == q].sort_values("prominence", ascending=False)
    out[f"quad::{q}"] = sub.proxy.tolist()

# --------------------------------------------- bootstrap stability of the axes
rng = np.random.default_rng(20261027)
B = 2000
idx = np.arange(len(inc))
proxies_col = inc.proxies.tolist()
val_mask = (inc.validation & ~inc.is_review).to_numpy()
vtypes_col = inc.val_types.tolist()
keep = [p for p in prox_list if p not in AGG]
top_q = {p: 0 for p in keep}
in_top8 = {p: 0 for p in keep}
rho_boot_counts, rho_boot_rate = [], []
pub_top8 = set(R[~R["is_aggregate"]].nlargest(8, "priority_published").proxy)
for _ in range(B):
    s = rng.choice(idx, size=len(idx), replace=True)
    bc = collections.Counter()
    bv = collections.Counter()
    for i in s:
        for p in set(proxies_col[i]):
            bc[p] += 1
            if val_mask[i]: bv[p] += 1
    sub = [p for p in keep if bc[p] > 0]
    if len(sub) < 10: continue
    recs = np.array([bc[p] for p in sub], float)
    vals = np.array([bv.get(p, 0) for p in sub], float)
    rate = vals / recs
    prom = stats.rankdata(recs) / len(sub)
    rho_boot_counts.append(stats.spearmanr(prom, stats.rankdata(vals) / len(sub)).statistic)
    rho_boot_rate.append(stats.spearmanr(prom, rate).statistic)
    comp = (prom + stats.rankdata(vals) / len(sub)) / 2
    order = [p for _, p in sorted(zip(-comp, sub))][:8]
    for p in order: in_top8[p] += 1
out["bootstrap_B"] = len(rho_boot_counts)
out["rho_counts_boot_ci"] = [round(float(np.percentile(rho_boot_counts, 2.5)), 3), round(float(np.percentile(rho_boot_counts, 97.5)), 3)]
out["rho_rate_boot_ci"] = [round(float(np.percentile(rho_boot_rate, 2.5)), 3), round(float(np.percentile(rho_boot_rate, 97.5)), 3)]
R["top8_stability"] = R.proxy.map({p: round(c / max(out["bootstrap_B"], 1), 3) for p, c in in_top8.items()})
out["published_top8"] = sorted(pub_top8)
out["published_top8_stability"] = {p: float(R.loc[R.proxy == p, "top8_stability"].iloc[0]) for p in sorted(pub_top8)}
out["stability_min_in_published_top8"] = round(float(min(out["published_top8_stability"].values())), 3)

# ------------------------------------- sensitivity to the weighting of the axes
for w in (0.0, 0.25, 0.5, 0.75, 1.0):
    comp = (1 - w) * R.prominence + w * R.validation_score_counts
    t8 = set(R[~R["is_aggregate"]].assign(c=comp).nlargest(8, "c").proxy)
    out[f"top8_weight_validation_{w:.2f}"] = sorted(t8)
    out[f"top8_overlap_with_published_w{w:.2f}"] = len(t8 & pub_top8)

# ----------------------------------- static/dynamic label reconciliation check
conflict = R[R.dynamic_proxy & ~R.dynamic_family]
out["label_conflicts"] = conflict[["proxy", "family"]].values.tolist()
out["label_conflicts_in_published_top20"] = R[R.dynamic_proxy & ~R.dynamic_family].nlargest(20, "priority_published").proxy.tolist()

R = R.sort_values("priority_published", ascending=False).reset_index(drop=True)
R.insert(0, "rank_published", range(1, len(R) + 1))
R.to_csv(TAB / "T_evidence_map.csv", index=False)
json.dump(out, open(DATA / "evidence_map.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))

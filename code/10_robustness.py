"""Step 10 -- do the headline findings survive removing the likeliest false positives?

The core corpus drops every included record with a checklist risk score of 3 or more (titles with no
exposure, proxy or spatial-modelling vocabulary, or with an off-core topic, a single proxy family and no
validation). The headline indicators are recomputed on the core and compared with the full corpus.

    python scripts/10_robustness.py -> tables/T_robustness.csv, data/robustness.json
"""
from __future__ import annotations
import json, pickle, sys, collections, itertools
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
CK = import_module("08_checklist")
SC = import_module("02_screen_code")
V2 = Path(__file__).resolve().parents[1]

df = pickle.load(open(V2 / "data/records_coded.pkl", "rb"))
inc = df[df.included].copy()
inc["risk"] = inc.apply(CK.risk, axis=1)
core = inc[inc.risk < 3]
bins, lab = [0, 2014, 2019, 2026], ["≤2014", "2015–2019", "2020–2026"]


def per(d, col):
    d = d[d.year >= 2010].copy()
    d["p"] = pd.cut(d.year, [2009, 2014, 2026], labels=["2010–2014", "2020–2026"]) if False else pd.cut(d.year, [2009, 2014, 2019, 2026], labels=["2010–2014", "2015–2019", "2020–2026"])
    return d.groupby("p", observed=False)[col].mean()


def rho(d):
    """Spearman correlation of prominence and validation evidence among named proxies, recomputed on d."""
    pc = collections.Counter(p for L in d.proxies for p in L)
    v = d[d.val_subcorpus]
    vc = collections.Counter(p for L in v.proxies for p in L)
    vs = collections.Counter(p for L, T in zip(v.proxies, v.val_types) for p in L if {"Spatial or blocked CV", "Independent or external validation"} & set(T))
    g = nx.Graph()
    for p in pc: g.add_node(p)
    for L in d.proxies:
        for a, b in itertools.combinations(sorted(set(L)), 2):
            g.add_edge(a, b, weight=g[a][b]["weight"] + 1 if g.has_edge(a, b) else 1)
    cen = nx.eigenvector_centrality_numpy(g, weight="weight")
    r = pd.DataFrame({"p": list(pc)}); r["n"] = r.p.map(pc); r["c"] = r.p.map(cen); r["v"] = r.p.map(lambda p: vc.get(p, 0)); r["s"] = r.p.map(lambda p: vs.get(p, 0))
    prom = (r.n.rank(pct=True) + r.c.rank(pct=True)) / 2; val = (r.v.rank(pct=True) + r.s.rank(pct=True)) / 2
    return stats.spearmanr(prom, val).statistic


def indicators(d):
    dyn = per(d, "has_dynamic"); ml = per(d.assign(ml=d.methods.map(lambda L: "Machine learning" in L)), "ml")
    v = d[d.val_subcorpus]
    fam = {f: d.families.map(lambda L: f in L).mean() for f in ("landuse", "road", "satellite")}
    return {
        "Studies": len(d),
        "Sub-Saharan Africa setting (%)": d.ssa.mean() * 100,
        "Reports validation (%)": d.val_subcorpus.mean() * 100,
        "Spatial or external validation (% of validated)": v.val_types.map(lambda L: bool({"Spatial or blocked CV", "Independent or external validation"} & set(L))).mean() * 100,
        "Personal exposure target (%)": d.personal.mean() * 100,
        "Dynamic proxy, 2010–2014 (%)": dyn["2010–2014"] * 100, "Dynamic proxy, 2020–2026 (%)": dyn["2020–2026"] * 100,
        "Machine learning, 2010–2014 (%)": ml["2010–2014"] * 100, "Machine learning, 2020–2026 (%)": ml["2020–2026"] * 100,
        "Land use family (%)": fam["landuse"] * 100, "Road and traffic family (%)": fam["road"] * 100, "Satellite family (%)": fam["satellite"] * 100,
        "Sensitivity-search share (%)": (d.corpus == "sensitivity").mean() * 100,
        "Prominence–validation ρ": rho(d),
    }


full, cr = indicators(inc), indicators(core)
t = pd.DataFrame({"indicator": list(full), "full corpus": list(full.values()), "core corpus (risk < 3)": [cr[k] for k in full]})
t["difference"] = t["core corpus (risk < 3)"] - t["full corpus"]
t.to_csv(V2 / "tables/T_robustness.csv", index=False)
out = dict(n_full=len(inc), n_core=len(core), n_removed=len(inc) - len(core), rows=t.round(3).to_dict("records"))
(V2 / "data/robustness.json").write_text(json.dumps(out, indent=1, default=float))
pd.set_option("display.width", 160)
print(t.round(2).to_string(index=False))

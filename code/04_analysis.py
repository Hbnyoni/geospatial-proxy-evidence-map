"""Step 4 -- performance analysis, science mapping and proxy-family mapping on the included corpus.

Performance: annual production and growth, citations, sources (Bradford zones), authors (Lotka),
countries (single- and multi-country publications), institutions.
Science mapping: author-keyword co-occurrence (association-strength normalisation, Louvain
communities), thematic map (Callon centrality and density), trend topics, reference co-citation.
Proxy mapping: families, named proxies, pollutants, methods, static vs dynamic proxies, validation
design, ambient vs personal targets, study geography.
Proxy ranking: bibliometric prominence (frequency and co-use centrality) plus validation frequency.

Outputs tables/T*.csv, data/stats.json, data/analysis.pkl, vosviewer/*.txt
"""
from __future__ import annotations
import re, json, pickle, math, sys, itertools, collections
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import gazetteer as G
from importlib import import_module
SC = import_module("02_screen_code")

V2 = Path(__file__).resolve().parents[1]
DATA, TAB, VOS = V2 / "data", V2 / "tables", V2 / "vosviewer"
SEED = 42
END_YEAR = 2025          # last complete year; 2026 is a partial year (exports of 1 April 2026)

df = pickle.load(open(DATA / "records_coded.pkl", "rb"))
inc = df[df.included].copy()
S: dict = {}

# ------------------------------------------------------------------ flow numbers
flow = json.loads((DATA / "flow_identification.json").read_text())
scr = df.groupby(["corpus", "decision"]).size().unstack(fill_value=0)
flow.update({f"screen_{c}_{d}": int(scr.loc[c, d]) for c in scr.index for d in scr.columns})
flow["included_primary"] = int(df[(df.corpus == "primary")].included.sum())
flow["included_sens"] = int(df[(df.corpus == "sensitivity")].included.sum())
flow["sens_yield"] = round(flow["included_sens"] / flow["sens_unique"], 3)
flow["included_total"] = int(len(inc))
flow["validation_subcorpus"] = int(df.val_subcorpus.sum())
flow["screened_total"] = int(len(df))
S["flow"] = flow
S["agreement_v1"] = json.loads((DATA / "agreement_v1_v2.json").read_text())
S["audit"] = json.loads((DATA / "audit_final_result.json").read_text())

# ------------------------------------------------------------------ production and growth
yr = inc.groupby(["year", "corpus"]).size().unstack(fill_value=0).reindex(range(inc.year.min(), inc.year.max() + 1), fill_value=0)
yr["total"] = yr.sum(axis=1)
yr.to_csv(TAB / "T_annual_production.csv")
def cagr(a, b):
    return (yr.loc[b, "total"] / yr.loc[a, "total"]) ** (1 / (b - a)) - 1
y_fit = yr.loc[2000:END_YEAR, "total"]
sl = stats.linregress(y_fit.index, np.log(y_fit.clip(lower=0.5)))
seg = {}
for a_, b_ in ((2000, 2009), (2010, END_YEAR)):
    yy_ = yr.loc[a_:b_, "total"]; l_ = stats.linregress(yy_.index, np.log(yy_.clip(lower=0.5)))
    seg[f"{a_}_{b_}"] = dict(rate=round(float(np.exp(l_.slope) - 1), 4), p=round(float(l_.pvalue), 4), mean=round(float(yy_.mean()), 1))
S["production"] = dict(segments=seg, first_year=int(inc.year.min()), last_year=int(inc.year.max()), n=int(len(inc)),
                       cagr_2000_2025=round(float(np.exp(sl.slope) - 1), 4), doubling_years=round(float(np.log(2) / sl.slope), 1),
                       share_since_2015=round(float((inc.year >= 2015).mean()), 3), share_since_2020=round(float((inc.year >= 2020).mean()), 3),
                       peak_year=int(yr.loc[:END_YEAR, "total"].idxmax()), peak_n=int(yr.loc[:END_YEAR, "total"].max()),
                       n_2026_partial=int(yr.loc[2026, "total"]) if 2026 in yr.index else 0,
                       articles=int((inc.doc_type_std == "Article").sum()), reviews=int((inc.doc_type_std == "Review").sum()),
                       both_db=int((inc.in_scopus & inc.in_wos).sum()), scopus_only=int((inc.in_scopus & ~inc.in_wos).sum()), wos_only=int((~inc.in_scopus & inc.in_wos).sum()))

# citations
inc["age"] = (2026 - inc.year).clip(lower=1)
S["citations"] = dict(total=int(inc.tc.sum()), mean=round(float(inc.tc.mean()), 1), median=float(inc.tc.median()),
                      mean_per_year=round(float((inc.tc / inc.age).mean()), 2), uncited=int((inc.tc == 0).sum()),
                      h_index=int(sum(1 for i, c in enumerate(sorted(inc.tc, reverse=True), 1) if c >= i)))
top_cited = inc.sort_values("tc", ascending=False).head(20)
top_cited.assign(first_author=top_cited.authors.map(lambda a: a[0] if a else ""), tc_per_year=(top_cited.tc / top_cited.age).round(1),
                 families=top_cited.families.map("; ".join))[["first_author", "year", "title", "source", "tc", "tc_per_year", "families", "doi"]].to_csv(TAB / "T_top_cited.csv", index=False)

# ------------------------------------------------------------------ sources and Bradford
SMALL = {"of", "the", "and", "for", "in", "on", "a", "an", "to", "at"}
def jtitle(t):
    w = re.sub(r"\s+", " ", t.strip()).split(" ")
    return " ".join(x.capitalize() if (i == 0 or x.lower() not in SMALL) else x.lower() for i, x in enumerate(w))
src = inc.source.map(jtitle)
src = src.str.replace("&", "and").str.replace(r"^The ", "", regex=True).str.replace(": A Global Access Science Source", "", regex=False)
inc["source_n"] = src
sc = inc.source_n.value_counts()
cum = sc.cumsum(); third = len(inc) / 3
zone = np.where(cum <= third, 1, np.where(cum <= 2 * third, 2, 3))
zone[0] = 1
brad = pd.DataFrame({"source": sc.index, "n": sc.values, "rank": range(1, len(sc) + 1), "cum": cum.values, "zone": zone})
# the first source that pushes a zone over its third still belongs to it
brad.to_csv(TAB / "T_bradford.csv", index=False)
src_tc = inc.groupby("source_n").tc.sum()
brad.head(15).assign(tc=lambda d: d.source.map(src_tc)).to_csv(TAB / "T_top_sources.csv", index=False)
S["sources"] = dict(n_sources=int(len(sc)), core_sources=int((brad.zone == 1).sum()), core_share=round(float(brad[brad.zone == 1].n.sum() / len(inc)), 3),
                    zone_counts=brad.groupby("zone").source.size().to_dict(), top=[(s, int(n)) for s, n in sc.head(10).items()])

# ------------------------------------------------------------------ authors and Lotka
def akey(a):
    a = SC.__dict__.get("_x", None) or a
    a = re.sub(r"\.", "", a).strip()
    a = re.sub(r"\s+", " ", a)
    parts = a.replace(",", " ").split()
    if not parts:
        return ""
    sur = [p for p in parts if not re.fullmatch(r"[A-Z]{1,3}|[A-Z]-[A-Z]", p)]
    ini = [p for p in parts if re.fullmatch(r"[A-Z]{1,3}|[A-Z]-[A-Z]", p)]
    return (" ".join(sur).title() + " " + (ini[0][0] if ini else "")).strip()
inc["akeys"] = inc.authors.map(lambda L: sorted({akey(a) for a in L if akey(a)}))
ac = collections.Counter(a for L in inc.akeys for a in L)
frac = collections.Counter()
for L in inc.akeys:
    for a in L:
        frac[a] += 1 / len(L)
auth = pd.DataFrame({"author": list(ac), "n": [ac[a] for a in ac], "fractional": [round(frac[a], 2) for a in ac]}).sort_values(["n", "fractional"], ascending=False)
auth.head(25).to_csv(TAB / "T_top_authors.csv", index=False)
lot = auth.n.value_counts().sort_index()
x, y = np.log10(lot.index.values), np.log10(lot.values / lot.values.sum())
ls = stats.linregress(x, y)
S["authors"] = dict(n_authors=int(len(ac)), single_paper_share=round(float((auth.n == 1).mean()), 3), lotka_exponent=round(float(-ls.slope), 2),
                    lotka_r2=round(float(ls.rvalue ** 2), 3), authors_per_doc=round(float(inc.akeys.map(len).mean()), 2),
                    single_authored=int((inc.akeys.map(len) == 1).sum()), top=[(a, int(n)) for a, n in ac.most_common(10)])
lot.rename("n_authors").to_csv(TAB / "T_lotka.csv")

# ------------------------------------------------------------------ countries (affiliations) and collaboration
cc = collections.Counter(c for L in inc.aff_countries for c in L)
corr = inc.corr_country.dropna()
scp = inc[inc.corr_country.notna()].groupby("corr_country").mcp.agg(["size", "sum"]).rename(columns={"size": "articles", "sum": "MCP"})
scp["SCP"] = scp.articles - scp.MCP
scp["MCP_ratio"] = (scp.MCP / scp.articles).round(3)
scp["full_count"] = scp.index.map(cc)
scp["country"] = scp.index.map(G.NAME)
scp["region"] = scp.index.map(G.REGION)
scp = scp.sort_values("articles", ascending=False)
scp.to_csv(TAB / "T_countries.csv")
ctry_full = pd.Series(cc).rename("papers").to_frame()
ctry_full["region"] = ctry_full.index.map(G.REGION)
S["countries"] = dict(n_countries=int(len(cc)), mcp_share=round(float(inc.mcp.mean()), 3),
                      top_corr=[(G.NAME.get(c, c), int(n)) for c, n in corr.value_counts().head(10).items()],
                      africa_author_papers=int(inc.aff_countries.map(lambda L: any(G.REGION.get(c) == "SSA" for c in L)).sum()),
                      africa_lead_papers=int((inc.corr_country.map(G.REGION) == "SSA").sum()),
                      author_region_share={k: round(float(v), 3) for k, v in inc.corr_country.map(G.REGION).value_counts(normalize=True).items()},
                      aff_resolved=round(float((inc.aff_countries.map(len) > 0).mean()), 3))
# collaboration network
CN = nx.Graph()
for L in inc.aff_countries:
    for a, b in itertools.combinations(sorted(L), 2):
        CN.add_edge(a, b, weight=CN[a][b]["weight"] + 1 if CN.has_edge(a, b) else 1)
for c, n in cc.items():
    if c in CN:
        CN.nodes[c]["n"] = n

# ------------------------------------------------------------------ institutions
ABBR = {"univ": "university", "inst": "institute", "natl": "national", "coll": "college", "med": "medical", "sci": "science", "sciences": "science",
        "technol": "technology", "res": "research", "environm": "environmental", "hlth": "health", "acad": "academy", "ctr": "center", "centre": "center",
        "dept": "department", "sch": "school", "publ": "public", "lab": "laboratory", "minist": "ministry", "agcy": "agency", "chinese": "chinese", "polytech": "polytechnic"}
STOP = {"of", "the", "and", "de", "for", "in", "at", "&"}
ORG = re.compile(r"(?i)universi|univ\b|institut|inst\b|college|coll\b|academ|acad\b|agency|agcy|ministry|council|school of public|hospital|centre|center|ctr\b|epa\b|laborator|lab\b|survey|museum|organi[sz]ation|cnrs|inserm|csir|nasa|noaa")
def inst_key(aff: str):
    parts = [p.strip() for p in aff.split(",")]
    cand = [p for p in parts if ORG.search(p) and not re.search(r"(?i)^(dept|department|division|faculty|school of (?!public)|unit|program|section|lab\b|laboratory of)", p)]
    if not cand:
        cand = [p for p in parts if ORG.search(p)]
    if not cand:
        return None, None
    name = next((p for p in cand if re.search(r"(?i)universi|univ\b", p)), cand[0])
    toks = [ABBR.get(t, t) for t in re.findall(r"[a-z]+", name.lower())]
    toks = [t for t in toks if t not in STOP]
    if not toks:
        return None, None
    return " ".join(sorted(set(toks))), name
ik, iname = collections.Counter(), collections.defaultdict(collections.Counter)
for L in inc.affiliations:
    seen = set()
    for a in L:
        k, n = inst_key(a)
        if k and k not in seen:
            seen.add(k); ik[k] += 1; iname[k][n] += 1
inst = pd.DataFrame([(iname[k].most_common(1)[0][0], n) for k, n in ik.most_common(25)], columns=["institution", "papers"])
inst.to_csv(TAB / "T_top_institutions.csv", index=False)
S["institutions"] = dict(top=[(r.institution, int(r.papers)) for r in inst.head(10).itertuples()])

# ------------------------------------------------------------------ keywords
SYN = [
    (r"^(pm ?2[.·,]?5|pm₂\.₅|fine particulate matter( \(pm2\.5\))?|fine particles?|pm2\.5 concentrations?|particulate matter 2\.5|fine particulate matter pm2\.5|fine pm)$", "PM2.5"),
    (r"^(pm ?10|pm₁₀|coarse particulate matter)$", "PM10"),
    (r"^(no ?2|nitrogen dioxides?|nitrogen dioxide \(no2\))$", "NO2"),
    (r"^(nox|nitrogen oxides)$", "NOx"),
    (r"^(o3|ozone|ground-level ozone|surface ozone)$", "ozone"),
    (r"^(black carbon|bc|black carbon \(bc\))$", "black carbon"),
    (r"^(ultrafine particles?|ufp|ufps|particle number concentration)$", "ultrafine particles"),
    (r"^(land[- ]use regressions?( models?)?|lur( models?)?|land use regression \(lur\)|land-use regression \(lur\)|land use regression modell?ing)$", "land use regression"),
    (r"^(gis|geographic(al)? information systems?( \(gis\))?|geographic information science)$", "GIS"),
    (r"^(aod|aerosol optical (depth|thickness)( \(aod\))?|aot|maiac( aod)?)$", "aerosol optical depth"),
    (r"^(machine[- ]learning( models?| methods?)?|ml)$", "machine learning"),
    (r"^(random forests?( models?| regression)?|rf)$", "random forest"),
    (r"^(deep learning|deep neural networks?)$", "deep learning"),
    (r"^(artificial neural networks?|neural networks?|ann)$", "neural network"),
    (r"^(remote sensing|satellite remote sensing|satellite data|satellite)$", "remote sensing"),
    (r"^(air pollution|air pollutants?|ambient air pollution|outdoor air pollution|atmospheric pollution|air pollution exposure)$", "air pollution"),
    (r"^(traffic[- ]related air pollution|trap|traffic[- ]related pollution|traffic pollution|traffic air pollution)$", "traffic-related air pollution"),
    (r"^(exposure assessment|exposure estimation|exposure modell?ing|exposure models?|exposure)$", "exposure assessment"),
    (r"^(personal exposure|personal monitoring|personal exposures)$", "personal exposure"),
    (r"^(ndvi|normali[sz]ed difference vegetation index( \(ndvi\))?)$", "NDVI"),
    (r"^(spatio-?temporal( modell?ing| models?| analysis| variation| prediction)?|space-time)$", "spatiotemporal modelling"),
    (r"^(particulate matter|pm|particulate matter \(pm\)|particles|airborne particulate matter)$", "particulate matter"),
    (r"^(tropomi|sentinel-?5p|s5p)$", "TROPOMI"),
    (r"^(google earth engine|gee)$", "Google Earth Engine"),
    (r"^(land use|land-use|land use and land cover|land cover|lulc)$", "land use"),
    (r"^(low[- ]cost sensors?|low-cost air quality sensors?|sensors)$", "low-cost sensors"),
    (r"^(kriging|geostatistics|geostatistical)$", "geostatistics"),
    (r"^(air quality|ambient air quality|urban air quality)$", "air quality"),
    (r"^(epidemiology|environmental epidemiology|air pollution epidemiology)$", "epidemiology"),
    (r"^(traffic|road traffic|vehicle traffic|traffic density)$", "traffic"),
    (r"^(dispersion models?|dispersion modell?ing|atmospheric dispersion)$", "dispersion model"),
    (r"^(health effects?|health impacts?|health)$", "health effects"),
    (r"^(spatial analysis|spatial)$", "spatial analysis"),
    (r"^(spatial variability|spatial variation|spatial distribution|intra-?urban variability|spatial heterogeneity)$", "spatial variability"),
    (r"^(green ?space|greenness|urban green space|greenspace)$", "greenness"),
    (r"^(meteorology|meteorological (factors|conditions|parameters|variables))$", "meteorology"),
    (r"^(mortality|all-cause mortality)$", "mortality"),
    (r"^(environmental justice|environmental inequality|environmental equity)$", "environmental justice"),
    (r"^(wildfires?|wildfire smoke|forest fires?)$", "wildfire"),
    (r"^(biomass burning)$", "biomass burning"),
    (r"^(volatile organic compounds?|vocs?)$", "VOCs"),
    (r"^(covid-19|sars-cov-2|coronavirus)$", "COVID-19"),
    (r"^(modell?ing|models?|model)$", "modelling"),
]
SYN = [(re.compile(p), t) for p, t in SYN]
GENERIC = {"air pollution", "modelling", "environment", "urban", "regression", "air pollutants"}       # the search term itself: kept in counts, removed from the map (it links to everything)
def norm_kw(k):
    k = re.sub(r"<[^>]+>", "", k)                       # Scopus keeps <sub>/<sup> markup in keywords
    k = re.sub(r"\s+", " ", k.strip().lower().replace("–", "-"))
    k = re.sub(r"\s*\([^)]*\)?\s*$", "", k).strip(" \"'")   # trailing acronym in brackets: 'land use regression (lur)'
    if not k:
        return ""
    for p, t in SYN:
        if p.match(k):
            return t
    if k in {c[3][0] for c in G.C.values() if c[3]} or k in {"india", "china", "africa", "europe", "united states"}:
        return k.title()
    return k
inc["kw"] = inc.kw_author.map(lambda L: sorted({norm_kw(k) for k in L if k and len(k) > 1} - {""}))
S["keywords"] = dict(coverage=round(float((inc.kw.map(len) > 0).mean()), 3), n_unique=int(len({k for L in inc.kw for k in L})))
kc = collections.Counter(k for L in inc.kw for k in L)
pd.DataFrame(kc.most_common(40), columns=["keyword", "n"]).to_csv(TAB / "T_top_keywords.csv", index=False)
S["keywords"]["top"] = kc.most_common(20)

def cooc_graph(lists, min_occ, top=None, drop=()):
    cnt = collections.Counter(k for L in lists for k in L if k not in drop)
    keep = [k for k, n in cnt.most_common(top) if n >= min_occ]
    ks = set(keep)
    g = nx.Graph()
    for k in keep:
        g.add_node(k, n=cnt[k])
    for L in lists:
        L = sorted(set(L) & ks)
        for a, b in itertools.combinations(L, 2):
            g.add_edge(a, b, weight=g[a][b]["weight"] + 1 if g.has_edge(a, b) else 1)
    # association strength: c_ij / (s_i s_j), scaled
    tot = sum(d["weight"] for *_, d in g.edges(data=True))
    for a, b, d in g.edges(data=True):
        d["assoc"] = d["weight"] * 2 * tot / (g.nodes[a]["n"] * g.nodes[b]["n"])
    return g

def merge_to(g, com, k, weight="assoc"):
    """Merge the smallest community into the one it is most strongly associated with, until k remain."""
    com = [set(c) for c in com]
    while len(com) > k:
        com.sort(key=lambda c: sum(g.nodes[n]["n"] for n in c))
        small = com.pop(0)
        link = [sum(g[a][b][weight] for a in small for b in c if g.has_edge(a, b)) for c in com]
        com[int(np.argmax(link))] |= small
    return com


def communities(g, resolution=1.0, weight="assoc", k=None):
    com = nx.community.louvain_communities(g, weight=weight, resolution=resolution, seed=SEED)
    if k:
        com = merge_to(g, com, k, weight)
    com = sorted(com, key=lambda c: -sum(g.nodes[n]["n"] for n in c))
    lab = {}
    for i, c in enumerate(com):
        for n in c:
            lab[n] = i
    return lab, com

KW = cooc_graph(inc.kw, min_occ=5, top=60, drop=GENERIC)
KW.remove_nodes_from([n for n in list(KW) if KW.degree(n) == 0])
# choose the resolution that yields four communities (the validated palette carries four hues)
# Louvain at the default resolution; communities beyond four (the validated palette) are merged
# into the community they are most strongly associated with
kres = 1.0
klab, kcom = communities(KW, kres, k=4)
for n in KW:
    KW.nodes[n]["cluster"] = klab[n]
S["kw_network"] = dict(nodes=KW.number_of_nodes(), edges=KW.number_of_edges(), min_occ=5, resolution=round(float(kres), 2),
                       clusters=[sorted(c, key=lambda n: -KW.nodes[n]["n"])[:8] for c in kcom])

# thematic map: Callon centrality (external links) and density (internal links) per cluster,
# on a finer partition so that themes, not the four broad clusters, are mapped
TM = cooc_graph(inc.kw, min_occ=4, top=150, drop=GENERIC)
TM.remove_nodes_from([n for n in list(TM) if TM.degree(n) == 0])
tlab, tcom = communities(TM, 1.3)
themes = []
for i, c in enumerate(tcom):
    if len(c) < 3:
        continue
    c = set(c)
    internal = sum(d["assoc"] for a, b, d in TM.edges(data=True) if a in c and b in c)
    external = sum(d["assoc"] for a, b, d in TM.edges(data=True) if (a in c) != (b in c))
    occ = sum(TM.nodes[n]["n"] for n in c)
    themes.append(dict(theme=i, size=len(c), occurrences=occ, centrality=external * 10, density=internal / len(c) * 100,
                       label=", ".join(sorted(c, key=lambda n: -TM.nodes[n]["n"])[:3]), members="; ".join(sorted(c, key=lambda n: -TM.nodes[n]["n"]))))
themes = pd.DataFrame(themes)
themes["quadrant"] = np.select([(themes.centrality >= themes.centrality.median()) & (themes.density >= themes.density.median()),
                                (themes.centrality >= themes.centrality.median()) & (themes.density < themes.density.median()),
                                (themes.centrality < themes.centrality.median()) & (themes.density >= themes.density.median())],
                               ["Motor", "Basic", "Niche"], "Emerging or declining")
themes.to_csv(TAB / "T_thematic_map.csv", index=False)

# trend topics: median publication year (and IQR) of each keyword, frequent keywords only
rows = []
ky = collections.defaultdict(list)
for L, y in zip(inc.kw, inc.year):
    for k in L:
        ky[k].append(y)
for k, ys in ky.items():
    if len(ys) >= 6 and k not in GENERIC:
        rows.append(dict(keyword=k, n=len(ys), q1=float(np.percentile(ys, 25)), median=float(np.median(ys)), q3=float(np.percentile(ys, 75))))
trend = pd.DataFrame(rows).sort_values("median")
trend.to_csv(TAB / "T_trend_topics.csv", index=False)

# ------------------------------------------------------------------ co-citation
labels = pickle.load(open(DATA / "ref_labels.pkl", "rb"))
rc = collections.Counter(k for L in inc.ref_keys for k in L)
S["references"] = dict(docs_with_refs=int((inc.ref_keys.map(len) > 0).sum()), unique_refs=int(len(rc)), total_cites=int(sum(rc.values())))
TOPR = 80
keep = [k for k, n in rc.most_common(TOPR)]
ks = set(keep)
CC = nx.Graph()
for k in keep:
    CC.add_node(k, n=rc[k])
for L in inc.ref_keys:
    L = sorted(set(L) & ks)
    for a, b in itertools.combinations(L, 2):
        CC.add_edge(a, b, weight=CC[a][b]["weight"] + 1 if CC.has_edge(a, b) else 1)
tot = sum(d["weight"] for *_, d in CC.edges(data=True))
for a, b, d in CC.edges(data=True):
    d["assoc"] = d["weight"] * 2 * tot / (CC.nodes[a]["n"] * CC.nodes[b]["n"])
cres = 1.0
clab, ccom = communities(CC, cres, k=4)
def _sur(k):
    l = labels.get(k, {})
    raw = l.get("first_full") or ""
    return raw or k.split("|")[0].title()
_lab0 = {k: f"{_sur(k)} ({k.split('|')[1]})" for k in keep}
_dup = collections.defaultdict(list)
for k in sorted(keep, key=lambda k: -rc[k]):
    _dup[_lab0[k]].append(k)
REF_LAB = {}
for lab0, ks_ in _dup.items():
    for i, k in enumerate(ks_):
        REF_LAB[k] = lab0 if len(ks_) == 1 else lab0[:-1] + "abcdefgh"[i] + ")"
def ref_label(k):
    return REF_LAB[k]
for n in CC:
    CC.nodes[n]["cluster"] = clab[n]; CC.nodes[n]["label"] = ref_label(n)
cocit = pd.DataFrame([dict(key=n, label=CC.nodes[n]["label"], cites=CC.nodes[n]["n"], cluster=clab[n] + 1,
                           title=labels.get(n, {}).get("title", ""), source=labels.get(n, {}).get("source", "")) for n in CC]).sort_values(["cluster", "cites"], ascending=[True, False])
cocit.to_csv(TAB / "T_cocitation.csv", index=False)
S["cocitation"] = dict(nodes=CC.number_of_nodes(), edges=CC.number_of_edges(), resolution=round(float(cres), 2),
                       clusters=[[CC.nodes[n]["label"] for n in sorted(c, key=lambda n: -CC.nodes[n]["n"])[:6]] for c in ccom])

# ------------------------------------------------------------------ proxy families, pollutants, methods
FAMS = [f for f in SC.FAM_LABEL if f != "unspecified"]
fam = pd.Series({SC.FAM_LABEL[f]: int(inc.families.map(lambda L: f in L).sum()) for f in FAMS}).sort_values(ascending=False)
fam_v = pd.Series({SC.FAM_LABEL[f]: int(inc[inc.val_subcorpus].families.map(lambda L: f in L).sum()) for f in FAMS})
famdf = pd.DataFrame({"records": fam, "share": (fam / len(inc)).round(3), "validation_records": fam_v.reindex(fam.index)})
famdf.to_csv(TAB / "T_proxy_families.csv")
S["families"] = dict(counts=fam.to_dict(), shares=(fam / len(inc)).round(3).to_dict(),
                     multi_family_share=round(float((inc.n_families >= 2).mean()), 3), median_families=float(inc.n_families.median()),
                     generic_only=int((inc.families.map(lambda L: L == ["unspecified"])).sum()))

POLLS = [p for p, _ in SC.POLL]
pol = pd.Series({p: int(inc.pollutants.map(lambda L: p in L).sum()) for p in POLLS}).sort_values(ascending=False)
S["pollutants"] = dict(counts=pol.to_dict(), none=int((inc.pollutants.map(len) == 0).sum()), multi=int((inc.pollutants.map(len) >= 2).sum()))
METH = [m for m, _ in SC.METHOD]
met = pd.Series({m: int(inc.methods.map(lambda L: m in L).sum()) for m in METH}).sort_values(ascending=False)
S["methods"] = dict(counts=met.to_dict())

fp = pd.DataFrame([[int(inc.apply(lambda r: f in r.families and p in r.pollutants, axis=1).sum()) for p in POLLS] for f in FAMS],
                  index=[SC.FAM_LABEL[f] for f in FAMS], columns=POLLS)
fp.to_csv(TAB / "T_family_x_pollutant.csv")
fm = pd.DataFrame([[int(inc.apply(lambda r: f in r.families and m in r.methods, axis=1).sum()) for m in METH] for f in FAMS],
                  index=[SC.FAM_LABEL[f] for f in FAMS], columns=METH)
fm.to_csv(TAB / "T_family_x_method.csv")
co = pd.DataFrame(0, index=[SC.FAM_LABEL[f] for f in FAMS], columns=[SC.FAM_LABEL[f] for f in FAMS])
for L in inc.families:
    L = [SC.FAM_LABEL[f] for f in L if f in FAMS]
    for a in L:
        for b in L:
            co.loc[a, b] += 1
co.to_csv(TAB / "T_family_cooccurrence.csv")

# periods
bins = [0, 1999, 2009, 2014, 2019, 2026]
plab = ["before 2000", "2000–2009", "2010–2014", "2015–2019", "2020–2026"]
inc["period"] = pd.cut(inc.year, bins=bins, labels=plab)
def share_ci(k, n):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n; z = 1.96; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)
per = []
for p_, g in inc.groupby("period", observed=False):
    n = len(g)
    for f in FAMS:
        k = int(g.families.map(lambda L: f in L).sum()); s, lo, hi = share_ci(k, n)
        per.append(dict(period=p_, family=SC.FAM_LABEL[f], k=k, n=n, share=s, lo=lo, hi=hi))
pd.DataFrame(per).to_csv(TAB / "T_family_by_period.csv", index=False)

# static vs dynamic, validation designs, personal, ML -- by period
dyn = []
for p_, g in inc.groupby("period", observed=False):
    n = len(g); v = g[g.val_subcorpus]
    for name, k, nn in [("Dynamic proxy family", g.has_dynamic.sum(), n), ("Static families only", (g.has_static & ~g.has_dynamic).sum(), n),
                        ("Machine learning", g.methods.map(lambda L: "Machine learning" in L).sum(), n),
                        ("Land-use regression", g.methods.map(lambda L: "Land-use regression" in L).sum(), n),
                        ("Satellite-to-surface estimation", g.methods.map(lambda L: "Satellite-to-surface estimation" in L).sum(), n),
                        ("Personal exposure target", g.personal.sum(), n),
                        ("Reports validation", g.val_subcorpus.sum(), n),
                        ("Spatial, external or temporal validation", v.val_types.map(lambda L: bool({"Spatial or blocked CV", "Independent or external validation", "Temporal hold-out"} & set(L))).sum(), len(v)),
                        ("Random or k-fold CV only", v.val_types.map(lambda L: "Random or k-fold CV" in L and not ({"Spatial or blocked CV", "Independent or external validation"} & set(L))).sum(), len(v))]:
        s, lo, hi = share_ci(int(k), int(nn))
        dyn.append(dict(period=p_, indicator=name, k=int(k), n=int(nn), share=s, lo=lo, hi=hi))
dyn = pd.DataFrame(dyn); dyn.to_csv(TAB / "T_trends_by_period.csv", index=False)

val = inc[inc.val_subcorpus]
vt = collections.Counter(t for L in val.val_types for t in L)
S["validation"] = dict(n=int(len(val)), share=round(len(val) / len(inc), 3), types=dict(vt),
                       spatial_or_external=int(val.val_types.map(lambda L: bool({"Spatial or blocked CV", "Independent or external validation"} & set(L))).sum()),
                       spatial_cv=int(val.val_types.map(lambda L: "Spatial or blocked CV" in L).sum()),
                       external=int(val.val_types.map(lambda L: "Independent or external validation" in L).sum()),
                       ssa=int(val.ssa.sum()), personal=int(val.personal.sum()))
S["static_dynamic"] = dict(static_only=int((inc.has_static & ~inc.has_dynamic).sum()), dynamic_only=int((~inc.has_static & inc.has_dynamic).sum()),
                           both=int((inc.has_static & inc.has_dynamic).sum()), neither=int((~inc.has_static & ~inc.has_dynamic).sum()))
S["personal"] = dict(n=int(inc.personal.sum()), share=round(float(inc.personal.mean()), 3), ssa=int((inc.personal & inc.ssa).sum()))
S["reviews"] = int(inc.is_review.sum())
_s = inc[inc.corpus == "sensitivity"]
S["vocabulary"] = dict(sens_using_proxy_word=int((_s.title + " " + _s.abstract).str.contains(r"(?i)proxy|proxies|surrogate").sum()), sens_n=int(len(_s)),
                       primary_using_predictor_word=round(float((inc[inc.corpus == "primary"].title + " " + inc[inc.corpus == "primary"].abstract).str.contains(r"(?i)predictor|covariate").mean()), 3))

# ------------------------------------------------------------------ geography of study settings
inc["n_iso"] = inc.study_iso.map(len)
sc_iso = collections.Counter(c for L in inc.study_iso for c in L)
geo = pd.DataFrame({"iso3": list(sc_iso), "studies": [sc_iso[c] for c in sc_iso]})
geo["country"] = geo.iso3.map(G.NAME); geo["region"] = geo.iso3.map(G.REGION); geo["income"] = geo.iso3.map(G.INCOME)
geo = geo.sort_values("studies", ascending=False); geo.to_csv(TAB / "T_study_countries.csv", index=False)
def study_region(r):
    if r.scope == "Global or multi-country":
        return "Global or multi-country"
    if not r.study_regions:
        return "Not stated"
    if len(r.study_regions) > 1:
        return "Multi-region"
    return G.REGION_NAME.get(r.study_regions[0], "Africa (unspecified)")
inc["region_label"] = inc.apply(study_region, axis=1)
reg = inc.region_label.value_counts()
located = inc[~inc.region_label.isin(["Not stated"])]
inc_grp = inc.study_iso.map(lambda L: sorted({G.INCOME[c] for c in L}))
S["geography"] = dict(region_counts=reg.to_dict(), located=int(len(located)), not_stated=int(reg.get("Not stated", 0)),
                      ssa_n=int(inc.ssa.sum()), ssa_share_all=round(float(inc.ssa.mean()), 4), ssa_share_located=round(float(located.ssa.mean()), 4),
                      africa_n=int(inc.africa.sum()), n_countries=int(len(sc_iso)),
                      ssa_countries=sorted({G.NAME[c] for L in inc.study_iso for c in L if G.REGION[c] == "SSA"}),
                      top_study=[(G.NAME[c], int(n)) for c, n in sc_iso.most_common(12)],
                      high_income_share_located=round(float(inc_grp[inc_grp.map(len) > 0].map(lambda L: L == ["H"]).mean()), 3),
                      lmic_any=int(inc_grp.map(lambda L: bool(set(L) & {"LM", "L"})).sum()))
ssa_recs = inc[inc.ssa][["rid", "year", "title", "source", "study_iso", "families", "pollutants", "methods", "val_types", "personal"]].copy()
for c in ("study_iso", "families", "pollutants", "methods", "val_types"):
    ssa_recs[c] = ssa_recs[c].map("; ".join)
ssa_recs.sort_values("year").to_csv(TAB / "T_ssa_records.csv", index=False)
# where SSA-based authors publish and where the studies of SSA come from
S["geography"]["ssa_studies_with_ssa_author"] = int(inc[inc.ssa].aff_countries.map(lambda L: any(G.REGION.get(c) == "SSA" for c in L)).sum())

# ------------------------------------------------------------------ proxy ranking (Objective 1)
prox_list = sorted({p for L in inc.proxies for p in L})
P = nx.Graph()
pc = collections.Counter(p for L in inc.proxies for p in L)
for p in prox_list:
    P.add_node(p, n=pc[p])
for L in inc.proxies:
    for a, b in itertools.combinations(sorted(set(L)), 2):
        P.add_edge(a, b, weight=P[a][b]["weight"] + 1 if P.has_edge(a, b) else 1)
cent = nx.eigenvector_centrality_numpy(P, weight="weight") if P.number_of_edges() else {p: 0 for p in P}
deg = dict(P.degree(weight="weight"))
fam_of = {n: f for f, n, *_ in SC.PROXIES}
vcount = collections.Counter(p for L in val.proxies for p in L)
vstrong = collections.Counter(p for L, T in zip(val.proxies, val.val_types) for p in L if {"Spatial or blocked CV", "Independent or external validation"} & set(T))
ssa_c = collections.Counter(p for L in inc[inc.ssa].proxies for p in L)
pers_c = collections.Counter(p for L in inc[inc.personal].proxies for p in L)
recent = inc[inc.year >= 2015]
rec_c = collections.Counter(p for L in recent.proxies for p in L)
rank = pd.DataFrame(dict(proxy=prox_list))
rank["family"] = rank.proxy.map(lambda p: SC.FAM_LABEL[fam_of[p]])
rank["records"] = rank.proxy.map(pc)
rank["share"] = (rank.records / len(inc)).round(3)
rank["centrality"] = rank.proxy.map(cent).round(3)
rank["validation_records"] = rank.proxy.map(lambda p: vcount.get(p, 0))
rank["validation_rate"] = (rank.validation_records / rank.records).round(3)
rank["spatial_or_external_val"] = rank.proxy.map(lambda p: vstrong.get(p, 0))
rank["personal_records"] = rank.proxy.map(lambda p: pers_c.get(p, 0))
rank["ssa_records"] = rank.proxy.map(lambda p: ssa_c.get(p, 0))
rank["share_since_2015"] = rank.proxy.map(lambda p: rec_c.get(p, 0) / max(pc[p], 1)).round(3)
rank["aggregate"] = rank.proxy.isin(["Land-use regression predictors", "Traffic (unspecified)", "Satellite remote sensing (general)"])
rank["dynamic"] = rank.proxy.map(lambda p: fam_of[p] in SC.DYNAMIC_FAM or p in {"Land surface temperature", "Vegetation index (NDVI, EVI)", "Traffic volume or intensity"})
pr = lambda s: s.rank(pct=True)
rank["prominence"] = ((pr(rank.records) + pr(rank.centrality)) / 2).round(3)
rank["validation_score"] = ((pr(rank.validation_records) + pr(rank.spatial_or_external_val)) / 2).round(3)
rank["priority"] = ((rank.prominence + rank.validation_score) / 2).round(3)
rank = rank.sort_values("priority", ascending=False).reset_index(drop=True)
rank.insert(0, "rank", range(1, len(rank) + 1))
rank.to_csv(TAB / "T_proxy_ranking.csv", index=False)
S["ranking"] = dict(n_proxies=int(len(rank)), top10=rank.head(10)[["proxy", "family", "records", "validation_records", "priority"]].values.tolist(),
                    rho_prominence_validation=round(float(stats.spearmanr(rank.prominence, rank.validation_score).statistic), 3))

# ------------------------------------------------------------------ VOSviewer exports (map + network files)
def vos_export(g, name, label_attr=None):
    ids = {n: i + 1 for i, n in enumerate(g)}
    with open(VOS / f"{name}_map.txt", "w") as f:
        f.write("id\tlabel\tcluster\tweight<Occurrences>\n")
        for n, i in ids.items():
            f.write(f"{i}\t{g.nodes[n].get(label_attr, n) if label_attr else n}\t{g.nodes[n].get('cluster', 0) + 1}\t{g.nodes[n].get('n', 1)}\n")
    with open(VOS / f"{name}_network.txt", "w") as f:
        for a, b, d in g.edges(data=True):
            f.write(f"{ids[a]}\t{ids[b]}\t{d['weight']}\n")
vos_export(KW, "keyword_cooccurrence")
vos_export(CC, "cocitation", "label")
for n in CN:
    CN.nodes[n]["label"] = G.NAME.get(n, n)
vos_export(CN, "country_collaboration", "label")

pickle.dump(dict(inc=inc, KW=KW, TM=TM, tlab=tlab, CC=CC, CN=CN, P=P, themes=themes, trend=trend, rank=rank, dyn=dyn, fp=fp, fm=fm, co=co,
                 brad=brad, yr=yr, scp=scp, geo=geo, per=pd.DataFrame(per), famdf=famdf), open(DATA / "analysis.pkl", "wb"))
(DATA / "stats.json").write_text(json.dumps(S, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
print(json.dumps({k: S[k] for k in ("flow", "production", "citations", "sources", "authors", "countries", "geography", "validation", "families", "static_dynamic", "personal")}, indent=1, default=str)[:7000])
print("KW clusters:", S["kw_network"]["clusters"])
print("Co-cit clusters:", S["cocitation"]["clusters"])
print(themes[["label", "quadrant", "occurrences"]].to_string())
print(rank.head(20).to_string())


# ================================================================== additions after reviewing published air-pollution
# bibliometric reviews: keyword overlay (mean publication year), Kleinberg burst detection, country
# collaboration map, and a three-field (Sankey) view of where, with what, and how proxies are validated.
from scipy.special import gammaln

# --- keyword mean publication year, for the overlay map
for n in KW:
    ys = ky.get(n, [])
    KW.nodes[n]["mean_year"] = float(np.mean(ys)) if ys else np.nan


# --- Kleinberg (2002) two-state burst detection on yearly keyword counts
def kleinberg(r, d, s=2.0, gamma=1.0):
    """Batched two-state automaton: r keyword documents, d all documents per year. Returns burst states and strength."""
    r, d = np.asarray(r, float), np.asarray(d, float)
    ok = d > 0
    p0 = r[ok].sum() / d[ok].sum()
    p1 = min(s * p0, 0.9999)
    def cost(p):
        with np.errstate(divide="ignore", invalid="ignore"):
            c = -(gammaln(d + 1) - gammaln(r + 1) - gammaln(d - r + 1) + r * np.log(p) + (d - r) * np.log(1 - p))
        return np.where(ok, c, 0.0)
    c0, c1 = cost(p0), cost(p1)
    n = len(r); tau = gamma * np.log(n)
    C = np.zeros((n, 2)); B = np.zeros((n, 2), int)
    C[0] = [c0[0], c1[0] + tau]
    for t in range(1, n):
        for j, ct in ((0, c0[t]), (1, c1[t])):
            stay, move = C[t - 1, j], C[t - 1, 1 - j] + (tau if j == 1 else 0)
            B[t, j] = j if stay <= move else 1 - j
            C[t, j] = min(stay, move) + ct
    q = np.zeros(n, int); q[-1] = int(np.argmin(C[-1]))
    for t in range(n - 1, 0, -1):
        q[t - 1] = B[t, q[t]]
    return q, float(np.sum((c0 - c1)[q == 1]))

YEARS = list(range(1995, END_YEAR + 1))
dper = inc.groupby("year").size().reindex(YEARS, fill_value=0).values
bursts = []
for k, n in kc.items():
    if n < 5 or k in GENERIC:
        continue
    rk_ = pd.Series([y for L, y in zip(inc.kw, inc.year) for kk in L if kk == k]).value_counts().reindex(YEARS, fill_value=0).values
    q, strength = kleinberg(rk_, dper, s=2.0, gamma=0.5)
    if q.sum() == 0:
        continue
    on = np.where(q == 1)[0]
    # report the longest contiguous burst
    runs_, start = [], on[0]
    for a, b in zip(on, list(on[1:]) + [None]):
        if b is None or b != a + 1:
            runs_.append((start, a)); start = b
    s0, e0 = max(runs_, key=lambda t: t[1] - t[0])
    if e0 - s0 < 1:          # minimum burst duration of two years
        continue
    bursts.append(dict(keyword=k, n=n, strength=round(strength, 2), begin=YEARS[s0], end=YEARS[e0]))
bursts = pd.DataFrame(bursts).sort_values("strength", ascending=False)
bursts.to_csv(TAB / "T_keyword_bursts.csv", index=False)
S["bursts"] = dict(n=int(len(bursts)), s=2.0, gamma=0.5, min_occ=5, min_years=2, top=bursts.head(10)[["keyword", "strength", "begin", "end"]].values.tolist())

# --- country collaboration links (full counting), for the map
coll = pd.DataFrame([dict(a=a, b=b, w=d["weight"]) for a, b, d in CN.edges(data=True)])
coll.to_csv(TAB / "T_country_links.csv", index=False)
ssa_links = coll[(coll.a.map(G.REGION) == "SSA") | (coll.b.map(G.REGION) == "SSA")]
S["collaboration"] = dict(n_links=int(len(coll)), n_links_w2=int((coll.w >= 2).sum()),
                          ssa_links=int(len(ssa_links)), ssa_partners=sorted({G.NAME.get(c, c) for c in pd.concat([ssa_links.a, ssa_links.b]) if G.REGION.get(c) != "SSA"}),
                          top=[(G.NAME.get(r.a, r.a), G.NAME.get(r.b, r.b), int(r.w)) for r in coll.sort_values("w", ascending=False).head(8).itertuples()])

# --- three-field flows: study region -> proxy family -> validation design (fractional weights)
def reg3(r):
    if r.ssa: return "Sub-Saharan Africa"
    if r.region_label in ("North America", "Europe & Central Asia", "East Asia & Pacific"): return r.region_label
    if r.region_label in ("Middle East & North Africa", "South Asia", "Latin America & Caribbean"): return "Other low- and middle-income regions"
    return "Global, multi-region or not stated"
def val3(r):
    T = set(r.val_types)
    if {"Spatial or blocked CV", "Independent or external validation", "Temporal hold-out"} & T: return "Spatial, external or temporal hold-out"
    if "Random or k-fold CV" in T: return "Random or k-fold cross-validation"
    if r.val_subcorpus: return "Validation, design not stated"
    return "No validation reported"
TOPF = ["landuse", "road", "meteorology", "population", "satellite", "topography"]
rows3 = []
for r in inc.itertuples():
    fams = [f for f in r.families if f in FAMS] or ["other"]
    fams = [SC.FAM_LABEL[f] if f in TOPF else "Other families" for f in fams]
    w = 1 / len(fams)
    for f in fams:
        rows3.append(dict(region=reg3(r), family=f, validation=val3(r), w=w))
flows = pd.DataFrame(rows3).groupby(["region", "family", "validation"], as_index=False).w.sum()
flows.to_csv(TAB / "T_three_field.csv", index=False)

pickle.dump(dict(inc=inc, KW=KW, TM=TM, tlab=tlab, CC=CC, CN=CN, P=P, themes=themes, trend=trend, rank=rank, dyn=dyn, fp=fp, fm=fm, co=co,
                 brad=brad, yr=yr, scp=scp, geo=geo, per=pd.DataFrame(per), famdf=famdf, bursts=bursts, coll=coll, flows=flows),
            open(DATA / "analysis.pkl", "wb"))
(DATA / "stats.json").write_text(json.dumps(S, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
print("bursts:", bursts.head(15).to_string()); print(S["collaboration"])

"""Step 7 -- the Chapter 2 bibliometric section (2.15.1-2.15.9), written from stats.json and tables.

Writes thesis/ch2_bibliometry.md, which the thesis chapter writer
(/PALS/CHEAQI_Composite_Indicator/scripts/thesis_chapter_write.py, block 'ch2-bibliometry') places
between the AUTO markers in the Chapter 2 markdown. Figures are copied into thesis/ with a 'ch2bib_'
prefix so that the bare file names the chapter uses resolve to exactly one file.

    python scripts/07_thesis_section.py
"""
from __future__ import annotations
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd

V2 = Path(__file__).resolve().parents[1]
S = json.loads((V2 / "data/stats.json").read_text())
TAB, FIG, OUT = V2 / "tables", V2 / "figs", V2 / "thesis"
OUT.mkdir(exist_ok=True)
F, P, G, V = S["flow"], S["production"], S["geography"], S["validation"]
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
n0 = lambda x: f"{int(x):,}"
tr = pd.read_csv(TAB / "T_trends_by_period.csv")
dyn = lambda ind, per: float(tr[(tr.indicator == ind) & (tr.period == per)].share.iloc[0])
rk = pd.read_csv(TAB / "T_proxy_ranking.csv")
named = rk[~rk["aggregate"]].reset_index(drop=True)
th = pd.read_csv(TAB / "T_thematic_map.csv")

FIGS = [("Fig01_search_flow", "Identification, de-duplication and screening of the primary and sensitivity searches.", 5.6),
        ("Fig02_production_sources", "(a) Annual production by search; (b) Bradford zones of sources; (c) the most productive sources.", 6.3),
        ("Fig03_collaboration", "International co-authorship; every link involving a Sub-Saharan African country is drawn in red.", 6.3),
        ("Fig04_keyword_network", "(a) Author-keyword co-occurrence network (association strength, Louvain communities); (b) the same network coloured by average publication year.", 6.3),
        ("Fig05_themes_bursts", "(a) Thematic map by Callon centrality and density; (b) keywords with the strongest bursts of use.", 6.3),
        ("Fig06_cocitation", "Co-citation network of the 80 most-cited references.", 6.0),
        ("Fig07_proxy_families", "(a) Studies per proxy family, with the validated part; (b) pollutants named by each family; (c) co-use of families (Jaccard index).", 6.3),
        ("Fig08_trends", "Change by period: (a) static and dynamic proxies, machine learning and personal-exposure targets; (b) studies reporting validation; (c) validation designs among validated studies.", 6.3),
        ("Fig09_geography", "(a) Countries in which the studies were set, with Sub-Saharan Africa outlined; (b) share of studies by region of study setting and of corresponding author.", 6.3),
        ("Fig10_three_field", "Three-field plot: study setting, proxy family and validation design.", 6.3),
        ("Fig11_proxy_priority", "(a) Bibliometric prominence against validation evidence for every named proxy; the ranked list is Table 2.1. (b) the twenty highest-priority named proxies.", 6.3)]
# panels that repeat a table are left out (the ranking bars repeat Table 2.1)
THESIS_SKIP = {("Fig11_proxy_priority", "b")}
FIGNO = {k: f"2.{i + 1}" for i, (k, *_ ) in enumerate(FIGS)}
for key, *_ in FIGS:
    shutil.copy2(FIG / f"{key}.png", OUT / f"ch2bib_{key}.png")


_F = {k: (c, w) for k, c, w in FIGS}


def img(key):
    """Markdown for a figure; a multi-panel figure becomes one image per panel (Figure 2.Na, 2.Nb ...)."""
    import panels as PN
    if isinstance(key, int):
        key = FIGS[key][0]
    cap, w = _F[key]
    parts = [f for f in PN.panels(FIG, key) if (key, f.stem[-1]) not in THESIS_SKIP]
    if len(parts) == 1:                    # one panel left: set it as a single figure
        f = parts[0]; lead, sub = PN.split_caption(cap)
        shutil.copy2(f, OUT / f"ch2bib_{f.name}")
        return f"![Figure {FIGNO[key]}. {(lead + ' ') if lead else ''}{sub.get(f.stem[-1], '')}](ch2bib_{f.name}){{width={PN.width_in(f)}in}}"
    if not parts:
        return f"![Figure {FIGNO[key]}. {cap}](ch2bib_{key}.png){{width={w}in}}"
    lead, sub = PN.split_caption(cap)
    out = []
    for f in parts:
        lt = f.stem[-1]
        shutil.copy2(f, OUT / f"ch2bib_{f.name}")
        out.append(f"![Figure {FIGNO[key]}{lt}. {(lead + ' ') if lead else ''}{sub.get(lt, '')}](ch2bib_{f.name}){{width={PN.width_in(f)}in}}")
    return "\n\n".join(out)


def lname(n):
    return n if (len(n) > 1 and n[1].isupper()) else n[0].lower() + n[1:]


def robust_sentence():
    f = V2 / "data/robustness.json"
    if not f.exists():
        return ""
    R = json.loads(f.read_text()); RR = {r["indicator"]: r for r in R["rows"]}
    g = lambda k, d=1: f"{RR[k]['full corpus']:.{d}f}% against {RR[k]['core corpus (risk < 3)']:.{d}f}%"
    return (f"Removing the {R['n_removed']} included studies most likely to be off-topic leaves the findings unchanged: the Sub-Saharan African share is {g('Sub-Saharan Africa setting (%)')}, "
            f"spatial or external validation {g('Spatial or blocked CV' if False else 'Spatial or external validation (% of validated)', 0)} of validated studies, and the prominence–validation correlation is "
            f"{RR['Prominence–validation ρ']['core corpus (risk < 3)']:.2f}. ")


def collab_text():
    import gazetteer as _G
    c = pd.read_csv(TAB / "T_country_links.csv")
    sl = c[(c.a.map(_G.REGION) == "SSA") | (c.b.map(_G.REGION) == "SSA")]
    intra = int(((sl.a.map(_G.REGION) == "SSA") & (sl.b.map(_G.REGION) == "SSA")).sum())
    return (f"Co-authorship shows how the African work is produced. African countries take part in {len(sl)} collaboration links, {int(sl.w.eq(1).sum())} of which rest on a single joint study; "
            f"only {intra} join two African countries. The field's dense, repeated collaborations are transatlantic and intra-European. African participation is occasional and mostly as a partner in projects led elsewhere.")


def obj1_paragraphs():
    f = V2 / "data/obj1_mapping.json"
    if not f.exists():
        return []
    o = json.loads(f.read_text())
    miss = ", ".join(lname(x) for x in o["top20_missing"])
    return ["",
            f"**How the Objective 1 candidate set relates to this ranking.** The {o['n_candidates']} candidates searched in Objective 1 (Chapter 3) were matched to the named proxies of this inventory. "
            f"They measure {o['n_literature_proxies_covered']} of its {o['n_named']} named proxies, including {o['top20_covered']} of the 20 highest-priority ones and {o['top10_covered']} of the top ten. "
            f"The six top-twenty proxies not represented are {miss}. Most of these cannot be built from open data in the PRECISE settings: there are no traffic counts, emission inventories or registers of industrial point sources. "
            f"Conversely, the set adds low-ranked dynamic proxies the literature has hardly tested, such as boundary-layer height, land surface temperature, satellite trace gases and fire activity.",
            "",
            f"The selection itself then departed from the literature's ordering. The {o['n_selected_unforced']} variables kept by forward selection in at least one pool (excluding the three road variables, which were entered first by design) "
            f"have a median literature rank of {o['selected_median_rank']:.0f}, against {o['unselected_median_rank']:.0f} for the variables never kept. "
            f"{o['selected_dynamic_share'] * 100:.0f}% of the kept variables are dynamic, against {o['unselected_dynamic_share'] * 100:.0f}% of those dropped. "
            "Measured against personal exposure in The Gambia, Kenya and Mozambique, the proxies that carried signal were the dynamic, less-studied ones. The static land-use, built-up, population and terrain variables that dominate the literature were not kept. "
            "Prominence in the literature did not predict usefulness for personal exposure in these settings, which is the strongest argument in this chapter for local validation."]


sg = P["segments"]; fs = S["families"]["shares"]; vt = V["types"]; co = S["countries"]
q20 = named[named.records >= 20]
L = []
L += ["### 2.15.1 Purpose and link to Objective 1", "",
      "The narrative review argues that personal exposure cannot be represented by a single ambient concentration or a single land-use variable. "
      "The bibliometric analysis tests whether the structure of the wider literature supports that argument, and it serves Objective 1 directly: identifying and prioritising open geospatial proxies, distinguishing static from dynamic ones, and establishing how and where each has been validated. "
      "Five questions structure the results: "
      "(Q1) how large the literature is, how it has grown and who produces it; "
      "(Q2) how it is organised conceptually and intellectually, and how its focus has shifted; "
      "(Q3) which proxy families, pollutants and methods it uses, and how the balance between static and dynamic proxies has changed; "
      "(Q4) how often, how and where proxies are validated; and "
      "(Q5) which proxies combine prominence with validation evidence, which gives the starting catalogue for Objective 1. "
      "Q3 to Q5 answer Objective 1 directly; Q1 and Q2 show where that evidence comes from and how mature it is. "
      "The full analysis is reported as a stand-alone manuscript (*What is used, what is validated, and where*).", ""]
L += ["### 2.15.2 Search, screening and the sensitivity of the search", "",
      f"Scopus and the Web of Science Core Collection were searched on 1 April 2026. Four concept blocks were combined with AND: pollutant terms; proxy terms (proxy indicator, proxy measure, proxy variable, surrogate, exposure proxy, pollution proxy, geospatial proxy); geospatial, remote-sensing, traffic, land-use and meteorological terms; and assessment or modelling terms. "
      "A sensitivity search tested whether relevant studies were being missed because they say predictor, covariate or indicator instead of proxy. It broadened the proxy block to that vocabulary and, separately, to named proxies (AOD, NDVI, VIIRS, LST, road density, distance to roads, Sentinel-5P, TROPOMI). "
      f"After restricting to articles and reviews and removing duplicates (DOI first, then exact title, then fuzzy title with manual review of near pairs), the primary search gave {n0(F['primary_unique'])} unique records and the sensitivity search {n0(F['sens_unique'])} further records. "
      "Screening applied six published exclusion rules to titles, abstracts and keywords: not about air-pollution assessment; proxy in an unrelated sense; no geospatial proxy; a biological or material proxy; indoor or occupational only; and emission-inventory, chemistry or model-process studies. "
      f"The rules were developed on 200 records and evaluated blind on a further 120 (precision {S['audit']['precision']:.2f}, negative predictive value {S['audit']['npv']:.2f}, estimated recall {S['audit']['est_recall']:.2f}). "
      f"Every included record was coded, with multiple labels allowed, for ten proxy families and {len(rk)} named proxies, pollutant, method, exposure target (ambient or personal), validation design and study country. "
      "Satellite atmospheric, meteorological and fire proxies were classed as dynamic and the others as static, which is the distinction Objective 1 tests.", "",
      f"{F['included_primary']} primary records ({pct(F['included_primary'] / F['primary_unique'], 0)}) and {F['included_sens']} sensitivity records ({pct(F['sens_yield'], 0)}) passed screening. The sensitivity yield exceeded the 20% threshold set in advance, so the two were merged into an analytical corpus of {F['included_total']} studies ({P['first_year']}–{P['last_year']}). "
      f"Only {S['vocabulary']['sens_using_proxy_word']} of the {F['included_sens']} sensitivity studies use the words proxy or surrogate anywhere in the title or abstract, so a search on the word proxy alone would have missed {pct(F['included_sens'] / F['included_total'], 0)} of the corpus. "
      "For Objective 1 this means the candidate catalogue cannot be built from proxy-labelled studies alone. It also means the earlier April 2026 figures, which merged the two searches without auditing the screening, are superseded by those reported here.", "",
      img("Fig01_search_flow"), ""]
L += ["### 2.15.3 Size, growth and producers (Q1)", "",
      f"Production grew by {sg['2000_2009']['rate'] * 100:.0f}% a year between 2000 and 2009 and has since held near {sg['2010_2025']['mean']:.0f} studies a year, with no significant trend from 2010 to 2025. "
      f"Five journals form the Bradford core and hold {pct(S['sources']['core_share'], 0)} of all studies, led by Atmospheric Environment ({S['sources']['top'][0][1]}), Science of the Total Environment ({S['sources']['top'][1][1]}) and Environmental Health Perspectives ({S['sources']['top'][2][1]}). "
      f"The most productive authors ({', '.join(a for a, _ in S['authors']['top'][:4])}) and institutions ({', '.join(i for i, _ in S['institutions']['top'][:3])}) belong to the European and North American land-use regression and cohort networks, and corresponding authors were based in the United States for {co['top_corr'][0][1]} studies, in China for {co['top_corr'][1][1]} and in Canada for {co['top_corr'][2][1]}. "
      "The field is mature, but its evidence is produced in a small number of high-income research systems.", "",
      img("Fig02_production_sources"), "",
      collab_text(), "", img("Fig03_collaboration"), ""]
L += ["### 2.15.4 Conceptual and intellectual structure (Q2)", "",
      "Author keywords form four communities: land-use regression and traffic exposure modelling; traffic-related health epidemiology; machine learning, mobile monitoring and ultrafine particles; and satellite and spatio-temporal modelling. "
      "Coloured by average publication year, the network separates an older core of GIS, traffic, dispersion models and epidemiology from a recent periphery of machine learning, random forest, aerosol optical depth and remote sensing.", "",
      img("Fig04_keyword_network"), "",
      "On the thematic map, land-use regression and exposure assessment are the field's basic themes (central, broadly connected), traffic mapping and child respiratory epidemiology are its motor themes, and satellite modelling and personal exposure are emerging themes, weakly connected to the rest. "
      "Burst detection dates the shift: GIS, traffic, dispersion models and asthma burst between the late 1990s and about 2013, and machine learning, random forest, remote sensing and aerosol optical depth from 2020. No keyword about validation, transfer or personal exposure burst at any time.", "",
      img("Fig05_themes_bursts"), "",
      "The intellectual base is older and narrower. The co-citation network has three communities: the European and North American land-use regression methods literature, the early traffic-proximity health studies, and the particulate-mortality cohorts. No satellite-retrieval reference and no African study is among the 80 most co-cited.", "",
      img("Fig06_cocitation"), ""]
L += ["### 2.15.5 Proxies, pollutants and the static-to-dynamic shift (Q3)", "",
      f"Land use and built environment ({pct(fs['Land use and built environment'], 0)} of studies) and road and traffic ({pct(fs['Road and traffic'], 0)}) dominate, followed by meteorology ({pct(fs['Meteorology'], 0)}), population and settlement ({pct(fs['Population and settlement'], 0)}), satellite atmospheric ({pct(fs['Satellite atmospheric'], 0)}) and topography ({pct(fs['Topography'], 0)}). "
      f"Vegetation and land surface ({pct(fs['Vegetation and land surface'], 0)}) and fire and smoke ({pct(fs['Fire and smoke'], 0)}) are rare. {pct(S['families']['multi_family_share'], 0)} of studies combine families, most often land use with roads. "
      "Road and land-use proxies are tied mostly to NO2, and fire proxies to PM2.5 and black carbon. A PM2.5 model for settings dominated by combustion and dust should therefore not inherit an NO2-oriented, traffic-led predictor set.", "",
      img("Fig07_proxy_families"), "",
      f"The static-versus-dynamic distinction at the heart of Objective 1 is visible in the literature's own trajectory. Studies using only static proxies fell from {pct(dyn('Static families only', '2010–2014'), 0)} in 2010–2014 to {pct(dyn('Static families only', '2020–2026'), 0)} in 2020–2026, while studies with at least one dynamic proxy rose from {pct(dyn('Dynamic proxy family', '2010–2014'), 0)} to {pct(dyn('Dynamic proxy family', '2020–2026'), 0)} and machine learning from {pct(dyn('Machine learning', '2010–2014'), 0)} to {pct(dyn('Machine learning', '2020–2026'), 0)} (Figure {FIGNO['Fig08_trends']}a). "
      f"Studies targeting personal exposure stayed a minority and fell from {pct(dyn('Personal exposure target', '2010–2014'), 0)} to {pct(dyn('Personal exposure target', '2020–2026'), 0)}. The field has moved towards the static-plus-dynamic design this thesis adopts, but not towards the personal-exposure target it uses.", ""]
L += ["### 2.15.6 Validation, and where the evidence comes from (Q4)", "",
      f"{V['n']} studies ({pct(V['share'], 0)}) report an empirical validation. Where a design is stated, random or k-fold cross-validation ({vt.get('Random or k-fold CV', 0)}) far outnumbers independent or external validation ({vt.get('Independent or external validation', 0)}) and spatially blocked cross-validation ({vt.get('Spatial or blocked CV', 0)}). "
      f"Only {V['spatial_or_external']} studies, {pct(V['spatial_or_external'] / F['included_total'])} of the corpus, report a design that tests transfer to unsampled places, and only {V['personal']} compare proxies with personal exposure. "
      "Most published accuracy figures therefore describe interpolation within a monitored network, not prediction in a new place. Section 2.15b and the validation design of Chapter 3 build on this distinction.", "",
      img("Fig08_trends"), "",
      f"Of the studies that name a setting, {pct(G['high_income_share_located'], 0)} were set only in high-income countries. Sub-Saharan Africa was the setting of {G['ssa_n']} of {F['included_total']} studies ({pct(G['ssa_share_all'])}), across {', '.join(G['ssa_countries'])}, and the base of the corresponding author for {co['africa_lead_papers']} ({pct(co['author_region_share'].get('SSA', 0))}). "
      f"Of those {G['ssa_n']} African studies, {V['ssa']} reported any validation and {S['personal']['ssa']} targeted personal exposure. None tested proxies against GPS-linked personal measurement in a peri-urban or rural cohort of the kind PRECISE provides.", "",
      img("Fig09_geography"), "",
      "The three-field plot puts the two gaps in one picture. Transfer-testing validation comes almost entirely from studies set in high-income regions or with no single setting, and none of the twelve African studies used such a design.", "",
      img("Fig10_three_field"), ""]
L += ["### 2.15.7 Proxy priority and the starting catalogue for Objective 1 (Q5)", "",
      f"Each named proxy was scored on prominence (frequency and centrality in the network of proxies used together) and on validation evidence (validated studies, and studies validated spatially or externally). "
      f"The two are almost perfectly rank-correlated (ρ = {S['ranking']['rho_prominence_validation']:.2f}). Among proxies used in at least 20 studies, the share validated ranged from {pct(q20.validation_rate.min(), 0)} to {pct(q20.validation_rate.max(), 0)} and was unrelated to how often the proxy is used, so validation has followed attention rather than being directed at uncertainty. "
      f"The highest-priority named proxies are {', '.join(lname(x) for x in named.proxy.head(9))} and {lname(named.proxy.iloc[9])} (Table 2.1). "
      f"No named proxy has more than {int(named.ssa_records.max())} Sub-Saharan African studies behind it. Proxies that would capture African sources (household fuel use, biomass and open burning, fire activity, land surface temperature, night-time lights) sit low in the ranking because they are rarely studied, not because they have been tested and found weak.", "",
      "Table 2.1. The twenty highest-priority named geospatial proxies (studies / validated / spatially or externally validated / personal-exposure / Sub-Saharan Africa).", "",
      "| Rank | Proxy | Family | Type | Studies | Validated | Spatial or external | Personal | SSA | Priority |",
      "|---|---|---|---|---|---|---|---|---|---|"]
for i, r in named.head(20).iterrows():
    L.append(f"| {i + 1} | {r.proxy} | {r.family} | {'dynamic' if r.dynamic else 'static'} | {r.records} | {r.validation_records} | {r.spatial_or_external_val} | {r.personal_records} | {r.ssa_records} | {r.priority:.2f} |")
L += ["", img("Fig11_proxy_priority"), "",
      "For this thesis the ranking is a list of candidates to test, not a list of proxies known to work. Objective 1 takes the static and dynamic candidates and puts each through the validity gates against measured personal exposure. "
      "The literature cannot settle whether a proxy works in The Gambia, Kenya or Mozambique, because it has almost never asked. "
      ] + obj1_paragraphs() + ["",
      "### 2.15.8 Limitations of the bibliometric analysis", "",
      "Screening and coding used titles, abstracts and keywords, not full texts. The audit puts precision at about three quarters and recall at about four fifths. "
      + robust_sentence() +
      "Abstracts under-report model variables, so family and proxy counts are lower bounds. "
      "Coverage is limited to two English-indexed databases, which under-represents grey literature and African institutional reports. Frequency and validation counts measure attention, not predictive skill. A highly ranked proxy can still fail in a specific setting, which is exactly what Objective 1 tests."]
(OUT / "ch2_bibliometry.md").write_text("\n".join(L) + "\n")
print("wrote", OUT / "ch2_bibliometry.md", len(" ".join(L).split()), "words")

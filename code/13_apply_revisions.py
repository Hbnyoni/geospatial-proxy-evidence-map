#!/usr/bin/env python3
"""Apply the October 2026 supervisory revisions to the hand-edited manuscript .docx.

The manuscript is no longer regenerated from 06_build_manuscript.py: it has been edited in Word, and
its reference list carries field codes and styling that must survive. This script therefore edits the
document in place, paragraph by paragraph, and never touches a paragraph in the Bibliography style or
anything after the References heading.

    python3 scripts/13_apply_revisions.py --check  <file.docx|document.xml>   # match report only
    python3 scripts/13_apply_revisions.py --apply  <file.docx> [-o out.docx]  # write the revised file
"""
from __future__ import annotations
import argparse
import copy
import itertools, re, shutil, sys, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ET.register_namespace("w", W[1:-1])

# ----------------------------------------------------------------------------- the revisions
# ("id", kind, needle, payload)
#   replace_para : needle matches a whole paragraph (normalised); payload replaces its text
#   replace_text : needle is a substring of one paragraph; payload replaces that substring
#   append_para  : payload is appended as new paragraph(s) after the paragraph matching needle
#   insert_before: payload is inserted as new paragraph(s) before the paragraph matching needle
#   delete_para  : the matching paragraph is removed

AIM = ("The aim of this review is to establish which geospatial proxy indicators the air-pollution exposure "
 "literature actually uses, which of them carry evidence that they work, and what that evidence implies for "
 "exposure modelling in Sub-Saharan Africa. Four objectives follow. The first is to delimit the literature "
 "reproducibly, by building a corpus from two databases under explicit, auditable screening rules, and to "
 "quantify how much of the field a proxy-worded search misses. The second is to describe the size, growth, "
 "producers and conceptual structure of that literature, and to date the shift from static to dynamic proxies. "
 "The third is to code every included study for the proxies, pollutants, methods, settings and validation "
 "designs it reports, and so to measure how often, under which designs and in which settings proxies are "
 "tested. The fourth is to place each named proxy on two separate axes, its prominence in the literature and "
 "the evidence that it has been validated, and to identify where the two diverge. Five questions "
 "operationalise these objectives.")

S25 = ("Temporal character was recorded at two levels, because a family and an individual variable within it do "
 "not always agree. At family level, satellite atmospheric, meteorological and fire proxies were treated as "
 "dynamic, because every variable they contain varies from day to day, and the remaining seven families were "
 "treated as static. At variable level, three named proxies that sit in nominally static families are "
 "themselves time-varying and were labelled dynamic: traffic volume or intensity, in road and traffic; and "
 "land surface temperature and vegetation index, both in vegetation and land surface. The family rule is used "
 "for every study-level statistic in this paper, including the period comparisons of Section 3.3 and Figure 7, "
 "where a study is classified by the families it draws on. The variable rule is used in Table 3 and Figure 10, "
 "where the unit is the proxy rather than the study. Both labels are carried for every proxy in Supplementary "
 "Table S3.")

S27 = ("The proxy co-use network used in Section 2.8 was built on the same principles, but from the coded "
 "proxies rather than from author keywords. Each of the 37 named proxies is a node, and two proxies are joined "
 "whenever they are coded in the same study, the edge weight being the number of studies in which they "
 "co-occur. No occurrence threshold was applied, so every coded proxy enters the network. Eigenvector "
 "centrality was computed on this weighted, undirected graph as the entries of the principal eigenvector of "
 "its weighted adjacency matrix, normalised so that the largest value is one. It measures whether a proxy is "
 "used alongside other widely used proxies, and so captures a different aspect of prominence from raw "
 "frequency: a proxy can be common but used in isolation, or less common but embedded in the standard "
 "predictor set.")

S28 = [
 ("Purpose. This section sets out how each proxy was placed on two axes. The purpose is descriptive. The axes "
  "summarise how much attention a proxy has received in this literature, and how much validation has been "
  "reported for it. Neither axis measures predictive accuracy, and the two are deliberately not combined into "
  "a single score."),
 ("Unit of analysis. The unit is the named proxy, not the study. Of the 37 coded proxies, 34 name a variable "
  "that can be extracted for a new setting. The other three, land-use regression predictor sets, unspecified "
  "traffic and general satellite remote sensing, are aggregate categories; they are shown but excluded from "
  "the group assignment and the stability analysis, because they do not identify a variable."),
 ("Inputs. Four quantities were taken from the coding for each proxy: the number of included studies using it; "
  "its eigenvector centrality in the proxy co-use network of Section 2.7; the number of those studies "
  "reporting an empirical validation; and the number reporting a spatial, blocked or independent external "
  "design. Reviews are excluded from the validation counts, as elsewhere."),
 ("Prominence. Frequency and centrality were each converted to a percentile rank across the 37 proxies, and "
  "prominence is their mean. Both component percentiles are reported alongside the composite in Table 3, so "
  "that a reader can see which component drives a proxy's position."),
 ("Validation evidence. The validation axis is a proportion, not a count. For each proxy it is the share of "
  "that proxy's studies reporting a validation, k/n, where n is the number of studies using the proxy and k "
  "the number of those reporting a validation. The denominator is shown with every rate, and each rate "
  "carries a 95% Wilson score interval, which is preferred to the normal approximation because many proxies "
  "have a small n and rates near the bounds. Transfer-testing designs are reported separately, as the count "
  "and the share of studies reporting a spatial, blocked or external validation, because they answer a "
  "different question from random cross-validation and are too rare to support a stable rate. This is a "
  "change from the earlier form of this analysis, in which the validation axis was itself a percentile of two "
  "counts. Counts of validated studies rise mechanically with a proxy's frequency, so a count-based axis is "
  "in large part a restatement of the prominence axis. Both forms are reported in Section 3.5, so that the "
  "difference can be seen."),
 ("Groups. The two axes were divided at their medians across the 34 named proxies, a prominence of 0.47 and a "
  "validation rate of 0.46, giving four descriptive groups: established; prominent but weakly validated; "
  "validated but peripheral; and under-studied. The medians are properties of this corpus and carry no "
  "external meaning. They are drawn on Figure 10a so that a proxy near a boundary can be seen to be near it."),
 ("Uncertainty and sensitivity. Three checks were run, and are reported in Section 3.5. First, every "
  "validation rate carries a Wilson interval, and those intervals are wide where n is small: the median width "
  "is 0.24 for the 21 proxies used in at least 20 studies, and 0.48 for the 13 used less often. Second, the "
  "corpus was resampled with replacement 2,000 times and the whole procedure repeated, recording for each "
  "proxy the proportion of resamples in which it held a place among the leading eight. Third, the composite "
  "was recomputed with the weight on the validation axis varied from 0 to 1 in steps of 0.25, and the "
  "membership of the leading eight compared with the published set."),
 ("Limits on interpretation. The map ranks literature prominence and reported evidence. It does not rank "
  "proxy performance. A proxy's position reflects what this corpus records about it, which depends on how "
  "often authors chose to use it, whether they reported a validation in the title, abstract or keywords, and "
  "which designs they used. A high validation rate on a small denominator is weak evidence, and a proxy in "
  "the under-studied group is not thereby a poor proxy; it is an untested one. The map is therefore read as a "
  "description of where evidence exists and where it is missing, and the proxies it places highest are "
  "candidates for local testing rather than recommendations."),
]

S35 = [
 ("Prominence and the count-based validation score were almost perfectly rank-correlated across the 37 "
  "proxies (Spearman ρ = 0.93, 95% bootstrap interval 0.91 to 0.97). That correlation is largely "
  "constructional. The number of validated studies using a proxy is itself close to a restatement of how often "
  "the proxy is used (ρ = 0.97 between records and validated records), so a validation axis built from "
  "counts cannot vary independently of a prominence axis built from frequency."),
 ("Replacing the counts with rates removes the correlation. The share of a proxy's studies that report a "
  "validation is unrelated to its prominence (ρ = −0.06, p = 0.71, bootstrap interval −0.37 to "
  "0.09; Figure 10a). Among the 21 named proxies used in at least 20 studies, the rate ranged from 18% "
  "(settlement and socio-economic status, 7 of 39) to 67% (industrial, commercial or port land, 33 of 49), "
  "median 46%, and was likewise unrelated to how often the proxy is used (ρ = 0.16, p = 0.50). Validation "
  "effort has been spread roughly in proportion to use, not directed at the proxies whose performance is least "
  "known."),
 ("Transfer-testing designs behave differently. The share of a proxy's studies reporting a spatial, blocked or "
  "external validation does rise with prominence (ρ = 0.48, p = 0.003), but from a very low base: the "
  "median such share among the 21 well-used proxies is 2.6%, the highest is 11.3% (aerosol optical depth, 6 of "
  "53), and 14 of the 34 named proxies have never been validated under any transfer-testing design. The few "
  "studies that test transfer have concentrated on proxies that were already prominent."),
 ("The two axes divide the 34 named proxies into four groups (Figure 10a, Table 3). Seven are established, "
  "prominent and validated at or above the median rate: land use or land cover class, elevation and terrain, "
  "traffic volume or intensity, population density, reanalysis or NWP fields, temperature, and industrial, "
  "commercial or port land. Ten are prominent but weakly validated, among them built-up or impervious surface "
  "(79 of 172, 46%), distance or proximity to roads (51 of 158, 32%) and settlement and socio-economic status "
  "(7 of 39, 18%). Ten are validated but peripheral, and seven are under-studied. The membership of the last "
  "two groups should be read with care, because they hold the smallest denominators: their median proxy is "
  "used in 13 and 9 studies respectively, with Wilson intervals about 0.45 wide, so their rates are compatible "
  "with a wide range of true values. Land surface temperature, for example, is validated in all 4 of its "
  "studies, an interval of 0.51 to 1.00."),
 ("The leading positions are not equally secure. Across 2,000 bootstrap resamples of the corpus, six proxies "
  "held a top-eight place in at least 93% of resamples: land use or land cover class, built-up or impervious "
  "surface, distance or proximity to roads, elevation and terrain, traffic volume or intensity, and population "
  "density (Figure 10c). Beyond these the ordering is resample-dependent: chemical-transport or dispersion "
  "model output held a top-eight place in 77% of resamples, wind in 55% and reanalysis or NWP fields in 49%. "
  "Varying the weight given to the validation axis from 0 to 1 changed the membership of the leading eight by "
  "at most one proxy. The stable finding is therefore a small set of six prominent proxies, not an ordered "
  "catalogue of twenty."),
 ("Dynamic proxies enter the upper part of the map through reanalysis meteorology, wind, temperature and "
  "aerosol optical depth, and are used disproportionately in recent studies; aerosol optical depth, for "
  "example, had 81% of its records published since 2015. The proxies that would describe African sources sit "
  "low on the prominence axis, but not uniformly low on the validation axis. Household fuel use is validated "
  "in 11 of its 21 studies (52%, 0.32 to 0.72) and land surface temperature in 4 of 4, whereas biomass and "
  "open burning (7 of 21, 33%), fire activity and burned area (2 of 9) and night-time lights (1 of 4) are both "
  "rarely used and rarely validated. None of these proxies has ever been validated under a spatial or external "
  "design, and no named proxy has more than 4 Sub-Saharan African studies."),
]

FIG10 = ("Figure 10. The evidence map for named geospatial proxies. (a) Bibliometric prominence, the mean "
 "percentile of frequency and of eigenvector centrality in the proxy co-use network, against the share of each "
 "proxy's studies that report a validation, with 95% Wilson intervals. Dashed lines are the medians across the "
 "34 named proxies and divide the plane into the four groups named in italics; symbol area is proportional to "
 "the number of studies; hollow symbols are aggregate categories, which are shown but not assigned to a group; "
 "labels are shortened, and bold labels mark the proxies relevant to African sources. (b) The same validation "
 "rates with their counts, denominators and intervals shown separately, ordered by rate; filled symbols mark "
 "proxies with at least one spatial, blocked or external validation. (c) The proportion of 2,000 bootstrap "
 "resamples of the corpus in which each proxy held a place among the leading eight; only proxies reaching a "
 "top-eight place in at least one resample are shown.")

TAB3 = ("Table 3. The twenty named proxies with the highest bibliometric prominence. Prominence is the mean of "
 "the frequency and centrality percentiles, both of which are shown in brackets. Validation is reported as a "
 "count over its denominator and as a rate with a 95% Wilson interval. Temporal follows the variable-level "
 "rule of Section 2.5. The evidence group and the stability column are defined in Section 2.8; stability is "
 "the proportion of 2,000 bootstrap resamples in which the proxy held a top-eight place. The ordering is by "
 "prominence, not by a combined score. The full table, including aggregate categories and both temporal rules, "
 "is Supplementary Table S3.")

TAB3_NOTE = ("Records: studies using the proxy. Prominence: the mean of the two component percentiles, which "
 "are given in brackets as frequency / co-use centrality. Validated k / n: studies reporting a validation over "
 "studies using the proxy. Validation rate: k / n with its 95% Wilson score interval. Spatial or external: "
 "studies validated with a spatial, blocked or independent external design. SSA: studies set in Sub-Saharan "
 "Africa. Stability: the proportion of 2,000 bootstrap resamples of the corpus in which the proxy held a "
 "top-eight place.")

REVISIONS = [
 # --- R1 author name
 ("R1a", "replace_text", "Handsome Bongani Nyoni1,2*", "Handsome Nyoni1,2*"),
 ("R1b", "replace_text", ", Handsome Bongani Nyoni", ", Handsome Nyoni"),
 ("R1c", "replace_text", "Handsome Bongani Nyoni conceived", "Handsome Nyoni conceived"),
 # --- R2 aim and objectives
 ("R2a", "replace_text",
  "Here we combine bibliometric mapping with evidence coding of every included study, and organise the "
  "results around five questions.",
  "Here we combine bibliometric mapping with evidence coding of every included study."),
 ("R2b", "insert_before",
  "How large is the literature on geospatial proxies for air-pollution exposure, how has it grown, and who "
  "produces it?", [AIM]),
 # --- R3 research question 5
 ("R3", "replace_para",
  "Which proxies combine prominence in the literature with validation evidence, and so form a defensible "
  "starting catalogue for new settings?",
  "For each named proxy, how does bibliometric prominence compare with the evidence that it has been "
  "validated, and which proxies are prominent without being validated, or validated without being prominent?"),
 # --- R4 section 2.5
 ("R4", "replace_text",
  "Satellite atmospheric, meteorological and fire proxies were treated as dynamic, because they vary from day "
  "to day; the remaining families were treated as static.", S25),
 # --- R5 section 2.7
 ("R5", "append_para", "Network files are provided in VOSviewer format.", [S27]),
 # --- R6 section 2.8
 ("R6a", "replace_para", "2.8 Proxy prioritisation",
  "2.8 The evidence map: prominence and validation evidence"),
 ("R6b", "replace_para",
  "Following the agreed logic of prominence plus validation, each named proxy received two scores.",
  S28[0], S28[1:]),
 # --- R7 section 3.5
 ("R7a", "replace_para", "3.5 Proxies that combine prominence and validation (Q5)",
  "3.5 Prominence and validation evidence"),
 ("R7b", "replace_para", "Among the 37 coded proxies, prominence and validation evidence were almost perfectly",
  S35[0], S35[1:]),
 # --- R8 figure 10 caption
 ("R8", "replace_para", "Figure 10. Bibliometric prominence (mean percentile of frequency", FIG10),
 # --- R9 table 3 caption and note
 ("R9a", "replace_para", "Table 3. The twenty highest-priority named geospatial proxies.", TAB3),
 ("R9b", "replace_para", "Records: studies using the proxy; Validated: those in the validation sub-corpus;",
  TAB3_NOTE),
 # --- R10 abstract (full paragraph; see review/revision_2026-10-27/ABSTRACT_revised.md)
 ("R10", "replace_para",
  "Geospatial proxy indicators, such as land use, road networks, satellite retrievals, meteorology and "
  "population, are the main way",
  "Geospatial proxy indicators, such as land use, road networks, satellite retrievals, meteorology and "
  "population, are the main way air-pollution exposure is estimated where monitors are sparse. Whether the "
  "proxies that dominate the literature have been validated, and in which settings, has not been mapped. We "
  "searched Scopus and Web of Science with a primary search built on proxy and surrogate terms and a "
  "sensitivity search that broadened the vocabulary to predictors, covariates, indicators and named proxies. Of "
  "2,217 unique records, 692 met published screening rules, audited blind at a precision of 0.75 and a negative "
  "predictive value of 0.91. The sensitivity search contributed 429 of these studies (62%), almost none of "
  "which used the words proxy or surrogate. Production grew by 31% a year in 2000–2009 and has since held near "
  "32 studies a year. Land use and built environment (55%) and road and traffic (52%) proxies dominated. "
  "Dynamic proxies (satellite, meteorology, fire) rose from 25% of studies in 2010–2014 to 62% in 2020–2026, "
  "while land-use regression fell from 45% to 23% and machine learning rose from 2% to 37%. 263 studies (38%) "
  "reported an empirical validation, but only 27 described a spatial or external hold-out, and 14 of the 34 "
  "named proxies have never been tested under one. We therefore map proxies on two axes, bibliometric "
  "prominence and validation rate, rather than combining them into a single ranking. The two are unrelated (ρ = "
  "−0.06, p = 0.71): validation effort has been spread in proportion to use, not directed at the proxies whose "
  "performance is least known. Only transfer-testing designs follow attention (ρ = 0.48), from a base of 2.6% "
  "of studies. Ten proxies are prominent but weakly validated, and only six hold a top-eight place in at least "
  "93% of 2,000 bootstrap resamples: land use or land cover class, built-up surface, road proximity, elevation, "
  "traffic intensity and population density. Sub-Saharan Africa was the setting of 12 studies (1.7%), one of "
  "which targeted personal exposure, and no named proxy there exceeds four studies or has been transfer-tested. "
  "The proxies most often recommended have therefore been developed and checked almost entirely outside Africa, "
  "under designs that rarely test transfer to new places."),
 # --- R11 section 4.3
 ("R11", "replace_text",
  "The near-perfect rank correlation between prominence and validation (ρ = 0.93) means that validation "
  "has accumulated where attention already was, not where uncertainty was greatest.",
  "The relationship between attention and validation needs stating carefully. Counts of validated studies "
  "track use almost exactly (ρ = 0.97), so the near-perfect correlation between prominence and a "
  "count-based validation score (ρ = 0.93) is largely a property of the measure rather than a finding. "
  "What the rates show is weaker, but no more comfortable: the share of a proxy's studies reporting a "
  "validation is unrelated to how prominent it is (ρ = −0.06), so validation has been spread in "
  "proportion to use rather than directed at the proxies whose performance is least known. Only for "
  "transfer-testing designs does validation genuinely follow attention (ρ = 0.48), and those designs are "
  "rare enough that the whole pattern rests on 73 study-proxy pairs."),
 # --- R12 section 4.5
 ("R12", "replace_text",
  "First, the priority ranking (Table 3) is a defensible starting catalogue, because it rewards both use and "
  "validation, but it should be read as a list of candidates to test, not a list of proxies known to work in a "
  "new setting.",
  "First, the evidence map (Figure 10, Table 3) identifies candidates to test, not proxies known to work. Only "
  "six proxies hold their leading position across bootstrap resamples of the corpus, and that position records "
  "prominence and reported evidence, not performance. A defensible starting set for a new setting is therefore "
  "small and provisional: those six proxies, read together with their validation rates and denominators, "
  "extended locally rather than adopted wholesale."),
 # --- R13 section 4.6
 ("R13", "replace_text",
  "A highly ranked proxy may still perform poorly in a specific setting, and only local validation can "
  "establish otherwise.",
  "A highly ranked proxy may still perform poorly in a specific setting, and only local validation can "
  "establish otherwise. The composite score used in the earlier form of this analysis compounded that "
  "problem, because its validation component was built from counts that rise with frequency; it is reported "
  "here only alongside the rate-based map that replaces it. Validation rates for proxies used in fewer than "
  "twenty studies have intervals about 0.45 wide and should not be read as estimates."),
 # --- R14 conclusions
 ("R14", "replace_text",
  "very few compare proxies with personal exposure, and validation has followed attention.",
  "very few compare proxies with personal exposure, and the validation that exists has been spread in "
  "proportion to use rather than directed at what is least known."),
 # --- R15 the remaining question tag is handled by R7a, which renames the whole heading
 # --- guidance paragraphs inserted by the reviewer, now acted on
 ("G1", "delete_para", "*This section should explain the prioritisation method in a reproducible order", None),
 ("G2", "delete_para", "I recommend replacing the single “priority” ranking", None),
 ("G3", "delete_para", "Prominence: frequency and co-use centrality, with the component values shown.", None),
 ("G4", "delete_para", "Validation evidence: validation proportion and design type, with counts,", None),
 ("G5", "delete_para", "**After the revision above, you’ll have to do some adjustment", None),
]

# ----------------------------------------------------------------------------- helpers
def ptext(p):
    """Visible text of a paragraph: insertions count, deletions do not."""
    out = []
    for node in p.iter():
        tag = node.tag.replace(W, "")
        if tag == "t":
            out.append(node.text or "")
    return "".join(out)

def norm(s):
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()

def body_paragraphs(root):
    """Every paragraph in the body, with its parent, stopping at the References heading."""
    body = root.find(f"{W}body")
    out, stop = [], False
    def walk(el):
        nonlocal stop
        for ch in list(el):
            tag = ch.tag.replace(W, "")
            if tag == "p":
                if stop: continue
                txt = norm(ptext(ch))
                if txt.lower() == "references":
                    stop = True
                    continue
                out.append((ch, el, txt))
            elif tag in ("tbl", "tr", "tc", "sdt", "sdtContent"):
                walk(ch)
    walk(body)
    return out

def style_of(p):
    pr = p.find(f"{W}pPr")
    if pr is None: return ""
    s = pr.find(f"{W}pStyle")
    return s.get(f"{W}val") if s is not None else ""

XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"

# ----------------------------------------------------------------------------- tracked changes
TRACK = {"on": False, "author": "Handsome Nyoni", "date": "2026-10-28T00:00:00Z"}
_next_id = itertools.count(9001)


def _rev_attrs():
    return {f"{W}id": str(next(_next_id)), f"{W}author": TRACK["author"], f"{W}date": TRACK["date"]}


def _run_with(rpr, text, deleted=False):
    r = ET.Element(f"{W}r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = ET.SubElement(r, f"{W}delText" if deleted else f"{W}t")
    t.set(XMLSPACE, "preserve")
    t.text = text
    return r


def _template_rpr(p):
    for r in p.iter(f"{W}r"):
        if r.find(f"{W}t") is not None:
            return r.find(f"{W}rPr")
    return None


def mark_para_inserted(p):
    """Mark the paragraph mark itself as inserted, so Word attributes the whole paragraph."""
    pr = p.find(f"{W}pPr")
    if pr is None:
        pr = ET.Element(f"{W}pPr")
        p.insert(0, pr)
    rpr = pr.find(f"{W}rPr")
    if rpr is None:
        rpr = ET.SubElement(pr, f"{W}rPr")
    if rpr.find(f"{W}ins") is None:
        rpr.insert(0, ET.Element(f"{W}ins", _rev_attrs()))
    for r in p.findall(f"{W}r"):
        i = list(p).index(r)
        wrap = ET.Element(f"{W}ins", _rev_attrs())
        p.remove(r)
        wrap.append(r)
        p.insert(i, wrap)
    return p


def mark_para_deleted(p):
    """Strike the paragraph out instead of removing it, keeping it reviewable."""
    pr = p.find(f"{W}pPr")
    if pr is None:
        pr = ET.Element(f"{W}pPr")
        p.insert(0, pr)
    rpr = pr.find(f"{W}rPr")
    if rpr is None:
        rpr = ET.SubElement(pr, f"{W}rPr")
    if rpr.find(f"{W}del") is None:
        rpr.insert(0, ET.Element(f"{W}del", _rev_attrs()))
    for r in list(p.findall(f"{W}r")):
        for t in r.findall(f"{W}t"):
            dt = ET.Element(f"{W}delText")
            dt.set(XMLSPACE, "preserve")
            dt.text = t.text
            r.remove(t)
            r.append(dt)
        i = list(p).index(r)
        wrap = ET.Element(f"{W}del", _rev_attrs())
        p.remove(r)
        wrap.append(r)
        p.insert(i, wrap)
    return p


# ----------------------------------------------------------------------------- field-safe editing
def protected_text_nodes(p):
    """Every w:t that belongs to a field result, and so must never be rewritten.

    A Zotero or Mendeley citation is a field: fldChar begin, the instruction, fldChar separate, the
    rendered citation, fldChar end. The rendered part is the field result. Moving or clearing it
    empties the citation on screen and is the one way this script could damage the references, so
    those nodes are identified and left alone. w:fldSimple carries its result inline instead.
    """
    protected, depth = set(), 0
    for el in p.iter():
        tag = el.tag.replace(W, "")
        if tag == "fldChar":
            ty = el.get(f"{W}fldCharType")
            if ty == "separate":
                depth += 1
            elif ty == "end":
                depth = max(0, depth - 1)
        elif tag == "t" and depth:
            protected.add(el)
    for fs in p.iter(f"{W}fldSimple"):
        protected.update(fs.iter(f"{W}t"))
    return protected


def editable_nodes(p):
    prot = protected_text_nodes(p)
    return [t for t in p.iter(f"{W}t") if t not in prot]


def set_paragraph_text(p, text):
    """Replace a paragraph's text, keeping its first run's formatting and its comment anchors.

    Refuses a paragraph that carries a citation field: those are edited with replace_substring,
    which works around the field rather than through it. Comment anchors are carried over, so a
    supervisor's comment still points at the paragraph that answers it.
    """
    if protected_text_nodes(p):
        raise SystemExit(f"refusing to rewrite a paragraph containing a citation field: {ptext(p)[:70]}")
    rpr = _template_rpr(p)
    old = ptext(p)
    starts, ends, refs = [], [], []
    for el in list(p):
        tag = el.tag.replace(W, "")
        if tag == "pPr":
            continue
        if tag == "commentRangeStart":
            starts.append(el)
        elif tag == "commentRangeEnd":
            ends.append(el)
        elif tag == "r" and el.find(f"{W}commentReference") is not None:
            refs.append(el)
        p.remove(el)
    for el in starts:
        p.append(el)
    if TRACK["on"]:
        if old:
            d = ET.SubElement(p, f"{W}del", _rev_attrs())
            d.append(_run_with(rpr, old, deleted=True))
        i = ET.SubElement(p, f"{W}ins", _rev_attrs())
        i.append(_run_with(rpr, text))
    else:
        p.append(_run_with(rpr, text))
    for el in ends + refs:
        p.append(el)
    return p


def _blank_clone(p):
    """A copy of a paragraph keeping only its pPr, so it serves as a formatting template.

    Everything else is dropped, including any citation field, because a clone is a new paragraph and
    must not carry a second copy of a field or of a comment anchor.
    """
    new = copy.deepcopy(p)
    rpr = _template_rpr(new)
    for el in list(new):
        if el.tag.replace(W, "") != "pPr":
            new.remove(el)
    return new, copy.deepcopy(rpr) if rpr is not None else None


def _fill_new_paragraph(new, rpr, text):
    if TRACK["on"]:
        ins = ET.SubElement(new, f"{W}ins", _rev_attrs())
        ins.append(_run_with(rpr, text))
        pr = new.find(f"{W}pPr")
        if pr is None:
            pr = ET.Element(f"{W}pPr")
            new.insert(0, pr)
        r = pr.find(f"{W}rPr")
        if r is None:
            r = ET.SubElement(pr, f"{W}rPr")
        r.insert(0, ET.Element(f"{W}ins", _rev_attrs()))
    else:
        new.append(_run_with(rpr, text))
    return new


def clone_paragraph_after(p, parent, text):
    new, rpr = _blank_clone(p)
    _fill_new_paragraph(new, rpr, text)
    parent.insert(list(parent).index(p) + 1, new)
    return new


def clone_paragraph_before(p, parent, text):
    new, rpr = _blank_clone(p)
    _fill_new_paragraph(new, rpr, text)
    parent.insert(list(parent).index(p), new)
    return new


def make_body_paragraph(p):
    """Strip list identity from a cloned paragraph so it reads as ordinary body text.

    insert_before clones its anchor to inherit the document's fonts and spacing. When the anchor is a
    numbered list item, the clone would otherwise join the list and renumber it, so the list style and
    the numbering reference are removed and body justification and leading are asserted.
    """
    pr = p.find(f"{W}pPr")
    if pr is None:
        return p
    for tag in ("numPr", "pStyle", "ind"):
        el = pr.find(f"{W}{tag}")
        if el is not None:
            pr.remove(el)
    if pr.find(f"{W}jc") is None:
        ET.SubElement(pr, f"{W}jc", {f"{W}val": "both"})
    sp = pr.find(f"{W}spacing")
    if sp is None:
        sp = ET.SubElement(pr, f"{W}spacing")
    sp.set(f"{W}line", "360")
    sp.set(f"{W}lineRule", "auto")
    return p


def replace_substring(p, needle, payload):
    """Replace a run of text inside a paragraph, touching only the runs it actually spans.

    The text is matched across run boundaries and tolerantly of whitespace, then edited in place:
    the prefix stays in its own run, the replacement goes in after it, and the suffix follows in a
    clone of that run. Every other run, and every citation field, is left exactly as it was.
    """
    nodes = editable_nodes(p)
    if not nodes:
        return False
    texts = [n.text or "" for n in nodes]
    joined = "".join(texts)
    pat = re.compile(r"\s+".join(re.escape(tok) for tok in needle.split()), re.S)
    m = pat.search(joined.replace("\u00a0", " "))
    if not m:
        return False
    start, end = m.span()
    matched = joined[start:end]

    bounds, acc = [], 0
    for t in texts:
        bounds.append((acc, acc + len(t)))
        acc += len(t)
    first = next(i for i, (a, b) in enumerate(bounds) if a <= start < b or (a == b == start))
    last = next(i for i, (a, b) in enumerate(bounds) if a < end <= b)

    prefix = texts[first][:start - bounds[first][0]]
    suffix = texts[last][end - bounds[last][0]:]

    parents = {c: q for q in p.iter() for c in q}
    run_first = parents[nodes[first]]
    holder = parents[run_first]

    nodes[first].text = prefix
    nodes[first].set(XMLSPACE, "preserve")
    for i in range(first + 1, last + 1):
        nodes[i].text = ""
        nodes[i].set(XMLSPACE, "preserve")

    rpr = run_first.find(f"{W}rPr")
    at = list(holder).index(run_first) + 1
    new_els = []
    if TRACK["on"]:
        d = ET.Element(f"{W}del", _rev_attrs())
        d.append(_run_with(rpr, matched, deleted=True))
        ins = ET.Element(f"{W}ins", _rev_attrs())
        ins.append(_run_with(rpr, payload))
        new_els += [d, ins]
    else:
        new_els.append(_run_with(rpr, payload))
    if suffix:
        new_els.append(_run_with(rpr, suffix))
        nodes[last].text = ""
    for k, el in enumerate(new_els):
        holder.insert(at + k, el)
    return True


# ----------------------------------------------------------------------------- driver
def run(root, apply=False):
    paras = body_paragraphs(root)
    report = []
    for rev in REVISIONS:
        rid, kind, needle, payload = rev[0], rev[1], rev[2], rev[3]
        extra = rev[4] if len(rev) > 4 else []
        nn = norm(needle)
        hits = [(p, parent, txt) for p, parent, txt in paras
                if (nn in txt if kind in ("replace_text", "append_para") else txt.startswith(nn) or txt == nn)]
        # a Bibliography paragraph is never a target
        hits = [h for h in hits if style_of(h[0]) != "Bibliography"]
        status = "OK" if len(hits) == 1 else ("NOT FOUND" if not hits else f"AMBIGUOUS ({len(hits)})")
        report.append((rid, kind, status, nn[:66]))
        if not apply or len(hits) != 1:
            continue
        p, parent, _ = hits[0]
        if kind == "replace_para":
            set_paragraph_text(p, payload)
            anchor = p
            for t in extra:
                anchor = clone_paragraph_after(anchor, parent, t)
        elif kind == "replace_text":
            replace_substring(p, needle, payload)
        elif kind == "append_para":
            anchor = p
            for t in payload:
                anchor = clone_paragraph_after(anchor, parent, t)
        elif kind == "insert_before":
            for t in payload:
                make_body_paragraph(clone_paragraph_before(p, parent, t))
        elif kind == "delete_para":
            if TRACK["on"]:
                mark_para_deleted(p)
            else:
                parent.remove(p)
        paras = body_paragraphs(root)
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-o", "--out")
    ap.add_argument("--track", action="store_true",
                    help="record every edit as a tracked change instead of applying it silently")
    ap.add_argument("--author", default=TRACK["author"], help="author shown on the tracked changes")
    a = ap.parse_args()
    TRACK["on"] = a.track
    TRACK["author"] = a.author
    if a.track:
        print(f'recording changes as tracked, author "{a.author}"\n')
    tgt = Path(a.target)
    if tgt.suffix == ".xml":
        root = ET.parse(tgt).getroot()
        rep = run(root, apply=False)
    else:
        with zipfile.ZipFile(tgt) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        rep = run(root, apply=a.apply)
        if a.apply:
            out = Path(a.out) if a.out else tgt.with_name(tgt.stem + "_REVISED.docx")
            shutil.copy(tgt, out)
            new_xml = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
            # rewrite the single part, copying everything else byte for byte
            with zipfile.ZipFile(tgt) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == "word/document.xml":
                        data = new_xml
                    zout.writestr(item, data)
            print(f"\nwrote {out}")
    ok = sum(1 for r in rep if r[2] == "OK")
    print(f"\n{'id':5s} {'kind':14s} {'status':14s} needle")
    for rid, kind, status, nn in rep:
        print(f"{rid:5s} {kind:14s} {status:14s} {nn}")
    print(f"\n{ok}/{len(rep)} matched")
    return 0 if ok == len(rep) else 1

if __name__ == "__main__":
    sys.exit(main())

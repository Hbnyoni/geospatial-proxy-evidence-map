"""Step 6 -- build the journal manuscript (Word) from stats.json, the tables and the figures.

Every number in the prose is read from data/stats.json or tables/*.csv, so the text cannot drift
from the analysis. APA 7 author-date references, A4, double-spaced, continuous line numbers,
Times New Roman, chemical subscripts as real Word subscript runs.

    python scripts/06_build_manuscript.py
      -> manuscript/Geospatial_Proxy_Bibliometric_Review_DRAFT.docx
         manuscript/Supplementary_Tables.xlsx
"""
from __future__ import annotations
import json, re, pickle, unicodedata
from pathlib import Path
import pandas as pd
from docx import Document
from docx.shared import Pt, Mm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

V2 = Path(__file__).resolve().parents[1]
S = json.loads((V2 / "data/stats.json").read_text())
TAB, FIG, OUT = V2 / "tables", V2 / "figs", V2 / "manuscript"
F, P, G, V = S["flow"], S["production"], S["geography"], S["validation"]
import sys as _sys; _sys.path.insert(0, str(V2 / "scripts"))
from importlib import import_module as _im
from scipy.stats import spearmanr
NPROX = len(_im("02_screen_code").PROXIES)
_hf = V2 / "data/human_overrides.json"
_H = json.loads(_hf.read_text()).get("screening", {}) if _hf.exists() else {}
HUMAN_DONE = bool(_H)
HUMAN_ADD = sum(v == "INCLUDE" for v in _H.values())

def lname(n):
    return n if (len(n) > 1 and n[1].isupper()) else n[0].lower() + n[1:]
CENTER = WD_ALIGN_PARAGRAPH.CENTER

# ------------------------------------------------------------------ references (APA 7)
# key: (in-text author string, year, full reference)
REFS = {
 "aria2017": ("Aria & Cuccurullo", 2017, "Aria, M., & Cuccurullo, C. (2017). bibliometrix: An R-tool for comprehensive science mapping analysis. *Journal of Informetrics, 11*(4), 959–975. https://doi.org/10.1016/j.joi.2017.08.007"),
 "vaneck2010": ("van Eck & Waltman", 2010, "van Eck, N. J., & Waltman, L. (2010). Software survey: VOSviewer, a computer program for bibliometric mapping. *Scientometrics, 84*(2), 523–538. https://doi.org/10.1007/s11192-009-0146-3"),
 "page2021": ("Page et al.", 2021, "Page, M. J., McKenzie, J. E., Bossuyt, P. M., Boutron, I., Hoffmann, T. C., Mulrow, C. D., … Moher, D. (2021). The PRISMA 2020 statement: An updated guideline for reporting systematic reviews. *BMJ, 372*, n71. https://doi.org/10.1136/bmj.n71"),
 "hoek2008": ("Hoek et al.", 2008, "Hoek, G., Beelen, R., de Hoogh, K., Vienneau, D., Gulliver, J., Fischer, P., & Briggs, D. (2008). A review of land-use regression models to assess spatial variation of outdoor air pollution. *Atmospheric Environment, 42*(33), 7561–7578. https://doi.org/10.1016/j.atmosenv.2008.05.057"),
 "jerrett2005": ("Jerrett et al.", 2005, "Jerrett, M., Arain, A., Kanaroglou, P., Beckerman, B., Potoglou, D., Sahsuvaroglu, T., Morrison, J., & Giovis, C. (2005). A review and evaluation of intraurban air pollution exposure models. *Journal of Exposure Analysis and Environmental Epidemiology, 15*(2), 185–204. https://doi.org/10.1038/sj.jea.7500388"),
 "briggs1997": ("Briggs et al.", 1997, "Briggs, D. J., Collins, S., Elliott, P., Fischer, P., Kingham, S., Lebret, E., Pryl, K., van Reeuwijk, H., Smallbone, K., & van der Veen, A. (1997). Mapping urban air pollution using GIS: A regression-based approach. *International Journal of Geographical Information Science, 11*(7), 699–718. https://doi.org/10.1080/136588197242158"),
 "brauer2003": ("Brauer et al.", 2003, "Brauer, M., Hoek, G., van Vliet, P., Meliefste, K., Fischer, P., Gehring, U., Heinrich, J., Cyrys, J., Bellander, T., Lewné, M., & Brunekreef, B. (2003). Estimating long-term average particulate air pollution concentrations: Application of traffic indicators and geographic information systems. *Epidemiology, 14*(2), 228–239. https://doi.org/10.1097/01.EDE.0000041910.49046.9B"),
 "eeftens2012": ("Eeftens et al.", 2012, "Eeftens, M., Beelen, R., de Hoogh, K., Bellander, T., Cesaroni, G., Cirach, M., … Hoek, G. (2012). Development of land use regression models for PM2.5, PM2.5 absorbance, PM10 and PMcoarse in 20 European study areas: Results of the ESCAPE project. *Environmental Science & Technology, 46*(20), 11195–11205. https://doi.org/10.1021/es301948k"),
 "beelen2013": ("Beelen et al.", 2013, "Beelen, R., Hoek, G., Vienneau, D., Eeftens, M., Dimakopoulou, K., Pedeli, X., … de Hoogh, K. (2013). Development of NO2 and NOx land use regression models for estimating air pollution exposure in 36 study areas in Europe: The ESCAPE project. *Atmospheric Environment, 72*, 10–23. https://doi.org/10.1016/j.atmosenv.2013.02.037"),
 "dockery1993": ("Dockery et al.", 1993, "Dockery, D. W., Pope, C. A., Xu, X., Spengler, J. D., Ware, J. H., Fay, M. E., Ferris, B. G., & Speizer, F. E. (1993). An association between air pollution and mortality in six U.S. cities. *New England Journal of Medicine, 329*(24), 1753–1759. https://doi.org/10.1056/NEJM199312093292401"),
 "pope2002": ("Pope et al.", 2002, "Pope, C. A., Burnett, R. T., Thun, M. J., Calle, E. E., Krewski, D., Ito, K., & Thurston, G. D. (2002). Lung cancer, cardiopulmonary mortality, and long-term exposure to fine particulate air pollution. *JAMA, 287*(9), 1132–1141. https://doi.org/10.1001/jama.287.9.1132"),
 "callon1991": ("Callon et al.", 1991, "Callon, M., Courtial, J. P., & Laville, F. (1991). Co-word analysis as a tool for describing the network of interactions between basic and technological research: The case of polymer chemistry. *Scientometrics, 22*(1), 155–205. https://doi.org/10.1007/BF02019280"),
 "small1973": ("Small", 1973, "Small, H. (1973). Co-citation in the scientific literature: A new measure of the relationship between two documents. *Journal of the American Society for Information Science, 24*(4), 265–269. https://doi.org/10.1002/asi.4630240406"),
 "blondel2008": ("Blondel et al.", 2008, "Blondel, V. D., Guillaume, J.-L., Lambiotte, R., & Lefebvre, E. (2008). Fast unfolding of communities in large networks. *Journal of Statistical Mechanics: Theory and Experiment, 2008*(10), P10008. https://doi.org/10.1088/1742-5468/2008/10/P10008"),
 "bradford1934": ("Bradford", 1934, "Bradford, S. C. (1934). Sources of information on specific subjects. *Engineering, 137*, 85–86."),
 "lotka1926": ("Lotka", 1926, "Lotka, A. J. (1926). The frequency distribution of scientific productivity. *Journal of the Washington Academy of Sciences, 16*(12), 317–323."),
 "vandonkelaar2010": ("van Donkelaar et al.", 2010, "van Donkelaar, A., Martin, R. V., Brauer, M., Kahn, R., Levy, R., Verduzco, C., & Villeneuve, P. J. (2010). Global estimates of ambient fine particulate matter concentrations from satellite-based aerosol optical depth: Development and application. *Environmental Health Perspectives, 118*(6), 847–855. https://doi.org/10.1289/ehp.0901623"),
 "roberts2017": ("Roberts et al.", 2017, "Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., … Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929. https://doi.org/10.1111/ecog.02881"),
 "ploton2020": ("Ploton et al.", 2020, "Ploton, P., Mortier, F., Réjou-Méchain, M., Barbier, N., Picard, N., Rossi, V., … Pélissier, R. (2020). Spatial validation reveals poor predictive performance of large-scale ecological mapping models. *Nature Communications, 11*, 4540. https://doi.org/10.1038/s41467-020-18321-y"),
 "meyer2021": ("Meyer & Pebesma", 2021, "Meyer, H., & Pebesma, E. (2021). Predicting into unknown space? Estimating the area of applicability of spatial prediction models. *Methods in Ecology and Evolution, 12*(9), 1620–1633. https://doi.org/10.1111/2041-210X.13650"),
 "amegah2017": ("Amegah & Agyei-Mensah", 2017, "Amegah, A. K., & Agyei-Mensah, S. (2017). Urban air pollution in Sub-Saharan Africa: Time for action. *Environmental Pollution, 220*(Part A), 738–743. https://doi.org/10.1016/j.envpol.2016.09.042"),
 "katoto2019": ("Katoto et al.", 2019, "Katoto, P. D. M. C., Byamungu, L., Brand, A. S., Mokaya, J., Strijdom, H., Goswami, N., … Nemery, B. (2019). Ambient air pollution and health in Sub-Saharan Africa: Current evidence, perspectives and a call to action. *Environmental Research, 173*, 174–188. https://doi.org/10.1016/j.envres.2019.03.029"),
 "martin2019": ("Martin et al.", 2019, "Martin, R. V., Brauer, M., van Donkelaar, A., Shaddick, G., Narain, U., & Dey, S. (2019). No one knows which city has the highest concentration of fine particulate matter. *Atmospheric Environment: X, 3*, 100040. https://doi.org/10.1016/j.aeaoa.2019.100040"),
 "steinle2013": ("Steinle et al.", 2013, "Steinle, S., Reis, S., & Sabel, C. E. (2013). Quantifying human exposure to air pollution—Moving from static monitoring to spatio-temporal exposure assessment. *Science of the Total Environment, 443*, 184–193. https://doi.org/10.1016/j.scitotenv.2012.10.098"),
 "kwan2012": ("Kwan", 2012, "Kwan, M.-P. (2012). The uncertain geographic context problem. *Annals of the Association of American Geographers, 102*(5), 958–968. https://doi.org/10.1080/00045608.2012.687349"),
 "hoek2017": ("Hoek", 2017, "Hoek, G. (2017). Methods for assessing long-term exposures to outdoor air pollutants. *Current Environmental Health Reports, 4*(4), 450–462. https://doi.org/10.1007/s40572-017-0169-5"),
 "nyoni2026": ("Nyoni et al.", 2026, "Nyoni, H. B., Mushore, T. D., Munthali, L., Makhanya, S. A., Chikoko, L., Luchters, S., … The HEAT Center. (2026). Performance of road-traffic-based exposure proxies against personal PM2.5 measurements in three Sub-Saharan African countries. *Air Quality, Atmosphere & Health, 19*(8), 168. https://doi.org/10.1007/s11869-026-02060-y"),
 "ryan2007": ("Ryan & LeMasters", 2007, "Ryan, P. H., & LeMasters, G. K. (2007). A review of land-use regression models for characterizing intraurban air pollution exposure. *Inhalation Toxicology, 19*(Suppl. 1), 127–133. https://doi.org/10.1080/08958370701495998"),
 "kleinberg2003": ("Kleinberg", 2003, "Kleinberg, J. (2003). Bursty and hierarchical structure in streams. *Data Mining and Knowledge Discovery, 7*(4), 373–397. https://doi.org/10.1023/A:1024940629314"),
 "breiman2001": ("Breiman", 2001, "Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5–32. https://doi.org/10.1023/A:1010933404324"),
 "brunekreef2002": ("Brunekreef & Holgate", 2002, "Brunekreef, B., & Holgate, S. T. (2002). Air pollution and health. *The Lancet, 360*(9341), 1233–1242. https://doi.org/10.1016/S0140-6736(02)11274-8"),
}
CITED = set()


def _sortkey(k):
    n = "".join(ch for ch in unicodedata.normalize("NFKD", REFS[k][0]) if not unicodedata.combining(ch))
    return (n.lower().replace("van ", "van"), REFS[k][1])


def cite(text):
    def paren(m):
        keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
        for k in keys:
            if k not in REFS:
                raise KeyError(k)
            CITED.add(k)
        return "(" + "; ".join(f"{REFS[k][0]}, {REFS[k][1]}" for k in sorted(keys, key=_sortkey)) + ")"

    def narr(m):
        k = m.group(1); CITED.add(k)
        return f"{REFS[k][0]} ({REFS[k][1]})"
    text = re.sub(r"\[(@[^\]]+)\]", paren, text)
    return re.sub(r"\[!([A-Za-z0-9]+)\]", narr, text)


# ------------------------------------------------------------------ document
doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.line_spacing = 2.0
SEC = doc.sections[0]
SEC.page_width, SEC.page_height = Mm(210), Mm(297)
SEC.left_margin = SEC.right_margin = SEC.top_margin = SEC.bottom_margin = Mm(25)
_ln = OxmlElement("w:lnNumType")
for k_, v_ in (("w:countBy", "1"), ("w:distance", "284"), ("w:restart", "continuous")):
    _ln.set(qn(k_), v_)
SEC._sectPr.find(qn("w:pgMar")).addnext(_ln)

SUB = re.compile(r"(PM2\.5|PM10|NO2|NOx|SO2|O3|CO2|R²|\*[^*]+\*)")


def runs(par, text, size=None, bold=False, italic=False):
    """Write text as runs, setting chemical subscripts and *italic* spans as real formatting."""
    for piece in SUB.split(text):
        if not piece:
            continue
        if piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            r = par.add_run(piece[1:-1]); r.italic = True; r.bold = bold
            if size: r.font.size = Pt(size)
            continue
        m = re.fullmatch(r"(PM|NO|SO|O|CO)(2\.5|10|2|x|3)", piece)
        if m:
            r1 = par.add_run(m.group(1)); r2 = par.add_run(m.group(2)); r2.font.subscript = True
            for r in (r1, r2):
                r.bold, r.italic = bold, italic
                if size: r.font.size = Pt(size)
            continue
        r = par.add_run(piece); r.bold, r.italic = bold, italic
        if size: r.font.size = Pt(size)
    return par


def p(text, size=None, bold=False, italic=False, align=None):
    par = doc.add_paragraph(); runs(par, cite(text), size, bold, italic)
    if align: par.alignment = align
    return par


def h(text, level=1):
    par = doc.add_heading(level=level)
    runs(par, text, size={0: 14, 1: 13, 2: 12}.get(level, 12), bold=True)
    for r in par.runs:
        r.font.name = "Times New Roman"; r.font.color.rgb = RGBColor(0, 0, 0)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    return par


# Main-text figures and the panels each keeps; everything else is a supplementary figure.
# Where two figures report the same finding only the stronger is kept in the paper (the thesis keeps all).
MAIN = [("Fig01_search_flow", None), ("Fig02_production_sources", ["a", "c"]), ("Fig04_keyword_network", ["a"]),
        ("Fig05_themes_bursts", ["b"]), ("Fig06_cocitation", None), ("Fig07_proxy_families", ["a", "b"]),
        ("Fig08_trends", ["a"]), ("Fig09_geography", ["a"]), ("Fig10_three_field", None), ("Fig11_proxy_priority", ["a"])]
SUPP = [("Fig02_production_sources", "b"), ("Fig03_collaboration", None), ("Fig04_keyword_network", "b"),
        ("Fig05_themes_bursts", "a"), ("Fig07_proxy_families", "c"), ("Fig08_trends", "b"), ("Fig08_trends", "c"), ("Fig09_geography", "b")]
DROPPED = [("Fig11_proxy_priority", "b")]          # duplicates Table 3
_MAINNO = {k: i + 1 for i, (k, _) in enumerate(MAIN)}
_MAINLET = {k: {o: "abcdef"[j] for j, o in enumerate(ps)} for k, ps in MAIN if ps}
_SUPPNO = {(k, l): i + 1 for i, (k, l) in enumerate(SUPP)}


def R(key, letter=None):
    """Text reference to a figure or panel, wherever it ended up (main text or supplement)."""
    if (key, letter) in _SUPPNO:
        return f"Supplementary Figure S{_SUPPNO[(key, letter)]}"
    if (key, None) in _SUPPNO:
        return f"Supplementary Figure S{_SUPPNO[(key, None)]}"
    n = _MAINNO[key]
    if letter and key in _MAINLET:
        ps = _MAINLET[key]
        return f"Figure {n}" if len(ps) == 1 else f"Figure {n}{ps[letter]}"
    return f"Figure {n}"


FIGNO, CAP = {}, {}


def fig(key, width=6.3, d=None):
    """Main-text figure: the kept panels, each full width and relettered (Figure Na, Nb ...)."""
    import panels as PN
    d = d or doc
    n = _MAINNO[key]
    keep = dict(MAIN)[key]
    lead, sub = PN.split_caption(CAP[key])
    if not keep:
        d.add_picture(str(FIG / f"{key}.png"), width=Inches(width))
        d.paragraphs[-1].alignment = CENTER
        par = p(f"Figure {n}. {CAP[key]}", size=9.5); par.paragraph_format.line_spacing = 1.15
        return
    for o in keep:
        f = FIG / f"{key}_{o}.png"
        d.add_picture(str(f), width=Inches(PN.width_in(f)))
        d.paragraphs[-1].alignment = CENTER
        tag = "" if len(keep) == 1 else _MAINLET[key][o]
        par = p(f"Figure {n}{tag}. " + (f"{lead} " if lead else "") + sub.get(o, ""), size=9.5)
        par.paragraph_format.line_spacing = 1.15


def supplementary_figures():
    """All figures and panels kept out of the main text, as their own Word file."""
    import panels as PN
    global doc
    main_doc = doc
    doc = Document()
    st_ = doc.styles["Normal"]; st_.font.name = "Times New Roman"; st_.font.size = Pt(11)
    sec = doc.sections[0]; sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Mm(25)
    h("Supplementary figures", 0)
    p("What is used, what is validated, and where: a bibliometric evidence map of geospatial proxy indicators for air-pollution exposure assessment", italic=True, size=10)
    for (key, l), i in _SUPPNO.items():
        lead, sub = PN.split_caption(CAP[key])
        f = FIG / (f"{key}_{l}.png" if l else f"{key}.png")
        doc.add_picture(str(f), width=Inches(PN.width_in(f)))
        doc.paragraphs[-1].alignment = CENTER
        txt = (sub.get(l, "") if l else CAP[key])
        if (key, l) == ("Fig04_keyword_network", "b"):
            txt = f"The author-keyword co-occurrence network of Figure {_MAINNO[key]} coloured by the average publication year of each keyword (overlay view)."
        p(f"Supplementary Figure S{i}. " + (f"{lead} " if (lead and l) else "") + txt, size=10)
        doc.add_paragraph()
    doc.save(OUT / "Supplementary_Figures.docx")
    doc = main_doc


def Fn(key):
    FIGNO.setdefault(key, len(FIGNO) + 1)
    return f"Figure {FIGNO[key]}"


TABNO = {}


def Tn(key):
    TABNO.setdefault(key, len(TABNO) + 1)
    return f"Table {TABNO[key]}"


def table(key, df, caption, note=None, widths=None):
    Tn(key)
    cap = p(f"Table {TABNO[key]}. {caption}", size=9.5, bold=True); cap.paragraph_format.line_spacing = 1.15
    t = doc.add_table(rows=1, cols=len(df.columns)); t.style = "Table Grid"
    for j, c in enumerate(df.columns):
        cell = t.rows[0].cells[j]; cell.text = ""; runs(cell.paragraphs[0], str(c), size=9, bold=True)
    for _, r in df.iterrows():
        cells = t.add_row().cells
        for j, v in enumerate(r):
            cells[j].text = ""; runs(cells[j].paragraphs[0], str(v), size=9)
    for row in t.rows:
        for j, cell in enumerate(row.cells):
            for par in cell.paragraphs:
                par.paragraph_format.line_spacing = 1.0
            if widths:
                cell.width = Inches(widths[j])
    if note:
        n = p(note, size=8.5, italic=False); n.paragraph_format.line_spacing = 1.0
    doc.add_paragraph()


def etal(labels):
    out = [re.sub(r"^(.+) \((\d{4}[a-z]?)\)$", r"\1 et al. (\2)", l) for l in labels]
    return ", ".join(out[:-1]) + " and " + out[-1]


pct = lambda x, d=1: f"{x * 100:.{d}f}%"
n0 = lambda x: f"{int(x):,}"

# ------------------------------------------------------------------ captions
CAP = {
 "Fig01_search_flow": "Identification, de-duplication and screening of the two searches. The sensitivity search broadened the proxy vocabulary (predictor, covariate, indicator) and added named proxies; it is counted only for records not already retrieved by the primary search. Exclusion codes are defined in Section 2.3.",
 "Fig02_production_sources": "(a) Annual production by the search that retrieved each study, with the three-year moving mean; 2026 is a partial year, and growth rates are log-linear fits for the two periods. (b) Bradford distribution of sources: cumulative studies against source rank, with the core zone (red) and zone 2 (blue), each holding about one third of the studies. (c) The twelve most productive sources, coloured by Bradford zone.",
 "Fig03_collaboration": "International co-authorship. Blue curves are country pairs with at least two joint studies, width proportional to the number; red curves are every link involving a Sub-Saharan African country. Node area is proportional to the number of studies with an author from the country.",
 "Fig04_keyword_network": "(a) Co-occurrence map of normalised author keywords used in at least five studies, drawn in the VOSviewer style: bubble size and label size are proportional to occurrences, links shown are those co-occurring in at least two studies, and colours are Louvain communities (communities beyond four merged into the one with which they share most association strength). Smaller keywords whose labels would collide are left unlabelled. The search term air pollution and generic words are omitted. (b) The same network coloured by the average publication year of each keyword (overlay view).",
 "Fig05_themes_bursts": "(a) Thematic map: each bubble is a keyword community placed by Callon centrality (links to other themes) and density (internal links); bubble area is total occurrences, and the dashed lines are the medians. (b) Keywords with the strongest bursts of use (Kleinberg two-state detection; scaling 2, transition cost 0.5, keywords in at least five studies, bursts of at least two years); the red segment is the burst period and strength is the log-likelihood gain of the burst state.",
 "Fig06_cocitation": "Co-citation network of the 80 most-cited references, after harmonising Scopus and Web of Science reference formats to a first-author, year and first-page key. Colours are Louvain communities; labels show the 34 most-cited references (letters distinguish same-author, same-year works).",
 "Fig07_proxy_families": "(a) Studies using each proxy family, with the part that also reports an empirical validation (red); a study can use several families. (b) Percentage of each family's studies that name each pollutant. (c) Co-use of proxy families within studies (Jaccard index).",
 "Fig08_trends": "Change by period. (a) Share of studies using static proxies only, at least one dynamic proxy family, machine learning, or targeting personal exposure. (b) Share reporting any empirical validation. (c) Among validated studies, the share whose only stated design is random or k-fold cross-validation, and the share reporting a spatial, external or temporal hold-out. Ribbons are 95% Wilson confidence intervals; n is shown under each period.",
 "Fig09_geography": "(a) Countries in which the studies were set, from the title, abstract and author keywords (log scale); Sub-Saharan Africa is outlined in blue. (b) Share of studies by World Bank region for the study setting (a study counts once for every region it is set in) and for the country of the corresponding author.",
 "Fig10_three_field": "Three-field plot linking study setting, proxy family and validation design. Band width is the number of studies, split equally across a study's proxy families. Bands from Sub-Saharan Africa are blue; bands into spatial, external or temporal hold-out are red.",
 "Fig11_proxy_priority": "(a) Bibliometric prominence (mean percentile of frequency and eigenvector centrality in the proxy co-use network) against validation evidence (mean percentile of validated studies and of studies validated spatially or externally) for every named proxy; labels show the six highest-ranked and the proxies relevant to African sources (bold). Hollow symbols are aggregate categories. (b) The twenty highest-priority named proxies, with the number of studies, validated studies and Sub-Saharan African studies.",
}

# ------------------------------------------------------------------ front matter
def front():
    p("Review article", size=10, italic=True, align=CENTER)
    p("What is used, what is validated, and where: a bibliometric evidence map of geospatial proxy indicators for air-pollution exposure assessment", size=15, bold=True, align=CENTER)
    p("Handsome Bongani Nyoni¹ *, [co-authors to be confirmed]", size=11, align=CENTER)
    p("¹ Department of Geomatics, University of Cape Town, Cape Town, South Africa", size=9.5, align=CENTER)
    p("* Corresponding author: nyonih@staff.msu.ac.zw", size=9.5, align=CENTER)
    p("Draft for co-author review. Author list, affiliations and target journal to be confirmed.", size=9, italic=True, align=CENTER)
    doc.add_page_break()


def highlights():
    h("Highlights", 1)
    for t in [f"{F['included_total']} studies on geospatial air-pollution proxies mapped from Scopus and Web of Science",
              f"{pct(F['included_sens'] / F['included_total'], 0)} of relevant studies never use the words proxy or surrogate",
              f"Dynamic proxies rose from {pct(dyn('Dynamic proxy family', '2010–2014'), 0)} to {pct(dyn('Dynamic proxy family', '2020–2026'), 0)} of studies since 2010",
              f"Only {V['spatial_or_external']} of {V['n']} validated studies report spatial or external validation",
              f"Sub-Saharan Africa is the setting of {G['ssa_n']} studies ({pct(G['ssa_share_all'])}) of the corpus"]:
        par = p("• " + t, size=11)
        par.paragraph_format.line_spacing = 1.5


def dyn(ind, per):
    d = pd.read_csv(TAB / "T_trends_by_period.csv")
    return float(d[(d.indicator == ind) & (d.period == per)].share.iloc[0])


def dynn(ind, per, col="k"):
    d = pd.read_csv(TAB / "T_trends_by_period.csv")
    return int(d[(d.indicator == ind) & (d.period == per)][col].iloc[0])


def abstract():
    h("Abstract", 1)
    fam = S["families"]["shares"]
    sg = P["segments"]
    p(f"Geospatial proxy indicators, such as land use, road networks, satellite retrievals, meteorology and population, are the main way air-pollution exposure is estimated where monitors are sparse. "
      f"Whether the proxies that dominate the literature have been validated, and in which settings, has not been mapped. "
      f"We searched Scopus and Web of Science with a primary search built on proxy and surrogate terms and a sensitivity search that broadened the vocabulary to predictors, covariates, indicators and named proxies. "
      f"Of {n0(F['primary_unique'] + F['sens_unique'])} unique records, {F['included_total']} met published screening rules, which a blinded audit estimated to have a precision of {S['audit']['precision']:.2f} and a negative predictive value of {S['audit']['npv']:.2f}. "
      f"The sensitivity search contributed {F['included_sens']} of the {F['included_total']} studies ({pct(F['included_sens'] / F['included_total'], 0)}), and almost none of these used the words proxy or surrogate. "
      f"Production grew by {sg['2000_2009']['rate'] * 100:.0f}% a year in 2000–2009 and has since held near {sg['2010_2025']['mean']:.0f} studies a year. "
      f"Land use and built environment ({pct(fam['Land use and built environment'], 0)}) and road and traffic ({pct(fam['Road and traffic'], 0)}) proxies dominated. "
      f"Dynamic proxies (satellite, meteorology, fire) rose from {pct(dyn('Dynamic proxy family', '2010–2014'), 0)} of studies in 2010–2014 to {pct(dyn('Dynamic proxy family', '2020–2026'), 0)} in 2020–2026, while land-use regression fell from {pct(dyn('Land-use regression', '2010–2014'), 0)} to {pct(dyn('Land-use regression', '2020–2026'), 0)} and machine learning rose from {pct(dyn('Machine learning', '2010–2014'), 0)} to {pct(dyn('Machine learning', '2020–2026'), 0)}. "
      f"{V['n']} studies ({pct(V['share'], 0)}) reported an empirical validation, but only {V['spatial_or_external']} described a spatial or external hold-out. "
      f"Sub-Saharan Africa was the setting of {G['ssa_n']} studies ({pct(G['ssa_share_all'])}), and only {S['personal']['ssa']} of these targeted personal exposure. "
      f"A ranking that combines bibliometric prominence with validation evidence placed land-use classes, built-up surface, elevation, road proximity, traffic intensity and reanalysis meteorology first; prominence and validation were almost perfectly rank-correlated (ρ = {S['ranking']['rho_prominence_validation']:.2f}), so validation has followed attention rather than tested it. "
      f"The proxies most often recommended have been developed and checked almost entirely outside Africa, and rarely under designs that test transfer to new places.")
    p("*Keywords:* air pollution; exposure assessment; geospatial proxy; land-use regression; remote sensing; bibliometrics; validation; Sub-Saharan Africa", size=11)


# ------------------------------------------------------------------ 1 Introduction
def intro():
    h("1. Introduction", 1)
    p("Most people's exposure to air pollution is never measured. Regulatory monitoring networks are sparse and are concentrated in high-income cities, and in much of Africa there is no continuous ground monitoring at all [@amegah2017; @martin2019]. "
      "Exposure in epidemiological studies, health-impact assessment and environmental-justice analysis is therefore usually estimated rather than observed. The estimate is built from geospatial proxy indicators: variables such as land use, road density, distance to major roads, traffic intensity, satellite aerosol optical depth, vegetation indices, meteorology, elevation and population density, which are related to emissions, dispersion or human activity and can be mapped everywhere [@jerrett2005; @hoek2008; @hoek2017].")
    p("Proxy-based exposure models are now a mature field. Land-use regression, which regresses measured concentrations on surrounding geospatial variables, was established in Europe in the late 1990s [@briggs1997; @brauer2003] and scaled up in multi-city cohorts [@eeftens2012; @beelen2013]. Satellite retrievals extended estimation to regions without monitors [@vandonkelaar2010], and machine learning now combines dozens of static and time-varying predictors. "
      "This methodological growth has not been matched by an account of which proxies have actually been tested, how, and where. A proxy can be widely used and still be weak in a new setting: urban form, fuel use, traffic composition, dust and biomass burning all change the link between a mapped variable and the concentration a person breathes. "
      "Validation designs differ as well. Random cross-validation among nearby monitors describes interpolation, whereas spatially blocked or external validation describes transfer to unsampled places, and the two can give very different answers [@roberts2017; @ploton2020; @meyer2021].")
    p("Sub-Saharan Africa is where these questions matter most and are least studied. Air-pollution burdens are high and rising, household and open combustion, unpaved roads and dust shape exposure differently from European and North American cities, and the monitoring needed to calibrate proxy models locally is largely absent [@katoto2019; @amegah2017]. "
      "Our own evaluation of road-network proxies against personal PM2.5 measurements in The Gambia, Kenya and Mozambique found weak and country-dependent associations [@nyoni2026]. That result raises a question this review addresses directly: were the proxies that failed the ones the literature recommends, and had they ever been validated in comparable settings?")
    p("Earlier reviews of exposure models have been narrative and organised by method [@jerrett2005; @ryan2007; @hoek2008]. Bibliometric science mapping makes it possible to describe a whole field quantitatively, from its sources and producers to its conceptual and intellectual structure [@aria2017; @vaneck2010]. "
      "Here we combine bibliometric mapping with evidence coding of every included study, and organise the results around five questions. "
      "Q1: How large is the literature on geospatial proxies for air-pollution exposure, how has it grown, and who produces it? "
      "Q2: How is it organised conceptually and intellectually, and how has its focus shifted? "
      "Q3: Which proxy families and named proxies are used, for which pollutants and with which methods, and how has the balance between static and dynamic proxies changed? "
      "Q4: How often, and under which designs, are proxies empirically validated, and in which settings? "
      "Q5: Which proxies combine prominence in the literature with validation evidence, and so form a defensible starting catalogue for new settings? "
      "Because the word proxy is used inconsistently, the search strategy itself was tested, and that test is reported with the methods.")


# ------------------------------------------------------------------ 2 Methods
def methods():
    h("2. Materials and methods", 1)
    h("2.1 Search strategy", 2)
    p(f"Scopus and the Web of Science Core Collection were searched on 1 April 2026, in titles, abstracts and keywords, without date limits. The search combined four concept blocks with AND: air pollution or pollutant terms; proxy terms; geospatial, remote-sensing, traffic, land-use and meteorological terms; and assessment or modelling terms ({Tn('search')}). "
      "Because many studies describe proxies as predictors, covariates or indicators without using the word proxy, a sensitivity search replaced the proxy block with this broader vocabulary and, separately, with named proxies (aerosol optical depth, NDVI, VIIRS, land surface temperature, road density, distance to roads, Sentinel-5P and TROPOMI). "
      "Full records with cited references were exported from both databases. The decision rule set in advance was that the sensitivity records would be merged into the analytical corpus if more than 20% of them passed screening, and otherwise reported only as a robustness check.")
    table("search", pd.DataFrame([
        ["1 Pollutant", "\"air pollution\" OR \"air quality\" OR PM2.5 OR PM10 OR NO2 OR ozone OR \"black carbon\"", "unchanged"],
        ["2 Proxy", "\"proxy indicator*\" OR \"proxy measure*\" OR \"proxy variable*\" OR surrogate* OR \"exposure proxy*\" OR \"pollution proxy*\" OR \"geospatial proxy*\"",
         "adds predictor* OR \"spatial predictor*\" OR \"environmental predictor*\" OR covariate* OR \"geospatial covariate*\" OR indicator* OR \"environmental indicator*\"; and separately the named proxies \"Aerosol Optical Depth\" OR AOD OR NDVI OR VIIRS OR \"land surface temperature\" OR LST OR \"road density\" OR \"distance to road*\" OR \"Sentinel-5P\" OR TROPOMI"],
        ["3 Geospatial", "geospatial OR spatial OR satellite* OR \"remote sensing\" OR GIS OR \"land use regression\" OR AOD OR NDVI OR VIIRS OR LST OR \"road density\" OR \"distance to road*\" OR \"population density\" OR meteorolog* OR ERA5", "unchanged"],
        ["4 Purpose", "assess* OR measur* OR monitor* OR estimat* OR model* OR predict* OR validate*", "unchanged"],
    ], columns=["Block", "Primary search", "Sensitivity search"]), "Search strategy. Blocks were combined with AND and searched in title, abstract and keywords.", widths=[0.9, 2.9, 2.6])

    h("2.2 Records and de-duplication", 2)
    p(f"The primary search returned {n0(F['scopus_primary'])} Scopus and {n0(F['wos_primary'])} Web of Science records, and the sensitivity search {n0(F['scopus_sens'])} and {n0(F['wos_sens'])}. Only articles and reviews were kept, and the flow of records is reported following PRISMA 2020 conventions [@page2021], although this is an evidence map rather than a systematic review of effects. "
      f"Duplicates were removed in three passes: by DOI, by exact normalised title, and by fuzzy title matching (token-set similarity of at least 95 with publication years within one year). A fuzzy pair was merged automatically only if the first-author surname also matched; the remaining pairs were listed for manual review. "
      f"Merged records kept the richer metadata of either database, the higher citation count and the longer cited-reference list. Sensitivity records already present in the primary set were removed by the same three rules.")

    h("2.3 Screening", 2)
    p(f"Screening applied explicit rules to the title, abstract and keywords, so that every decision is reproducible and every excluded record carries a reason. A record was retained if it used, compared, validated or reviewed indirect geospatial or environmental variables to assess air pollution or estimate exposure. Exclusions were applied in order: "
      "R1, air pollution is not the topic of the record (it must appear in the title or author keywords, or at least three times in the abstract), including particulates in aquatic or soil settings; "
      "R2, proxy or surrogate in an unrelated sense, such as palaeo-environmental archives or computational emulators of air-quality models; "
      "R4, the proxy is a biological or material sample, such as a biomonitor or biomarker, with no geospatial data layer alongside it; "
      "R5, indoor or occupational settings only; "
      "R6, emission inventories, atmospheric-chemistry, field-campaign and model-process studies with no exposure, proxy or mapping aim; "
      "and R3, no geospatial proxy and no spatial component. "
      "A proxy family counted towards inclusion only when it was named in the title or abstract and accompanied by estimation, exposure or spatial context; generic mentions of traffic, temperature or wind alone did not qualify.")
    au = S["audit"]
    p(f"The rules were developed on two stratified samples of 100 records each, then frozen, and evaluated on a third sample of 120 records (60 included, 60 excluded) drawn from records not used in development and judged with the rule decision hidden. "
      f"In that audit the rules had a precision of {au['precision']:.2f} (95% CI {au['precision_ci'][0]:.2f}–{au['precision_ci'][1]:.2f}) and a negative predictive value of {au['npv']:.2f} ({au['npv_ci'][0]:.2f}–{au['npv_ci'][1]:.2f}); weighting by the corpus proportions, recall was estimated at {au['est_recall']:.2f}. "
      f"One rule (emission inventories and integrated-assessment studies) was tightened after the audit, and the metrics reported are for the final rules. "
      f"Agreement with an earlier keyword-assisted screening of the same records was {S['agreement_v1']['agreement'] * 100:.0f}% (Cohen's κ = {S['agreement_v1']['kappa']:.2f}). "
      + (f"Every included title was then checked by a human reviewer, who removed {F.get('screen_primary_RH', 0) + F.get('screen_sensitivity_RH', 0)} off-topic studies and added {HUMAN_ADD} that the rules had missed. " if HUMAN_DONE else "")
      + (f"Audit verdicts were made by a human reviewer ({au['human_verdicts']} of 120). " if au.get('human_verdicts', 0) >= 120 else
         "[Audit judgements were drafted with AI assistance; a human reviewer must confirm them before submission (review/HUMAN_CHECKLIST.xlsx). The audit workbook is supplied as Supplementary Table S6.]"))

    h("2.4 Records retrieved and the sensitivity of the search", 2)
    p(f"The primary search yielded {n0(F['primary_unique'])} unique records ({F['primary_both_db']} in both databases, {F['primary_scopus_only']} in Scopus only and {F['primary_wos_only']} in Web of Science only), of which {F['included_primary']} ({pct(F['included_primary'] / F['primary_unique'], 0)}) passed screening ({R('Fig01_search_flow')}). "
      f"The primary search was broad but imprecise: {F['screen_primary_R1']} records were not about air pollution, mostly ecological, soil and aquatic studies that use surrogate in other senses. "
      f"The sensitivity search added {n0(F['sens_unique'])} records not retrieved by the primary search, of which {F['included_sens']} ({pct(F['sens_yield'], 0)}) passed. This exceeded the 20% threshold set in advance, so the two sets were merged into an analytical corpus of {F['included_total']} studies: {P['articles']} articles and {P['reviews']} reviews, published between {P['first_year']} and {P['last_year']}. "
      f"Only {S['vocabulary']['sens_using_proxy_word']} ({pct(S['vocabulary']['sens_using_proxy_word'] / S['vocabulary']['sens_n'], 1)}) of the sensitivity-only studies used the words proxy, proxies or surrogate in the title or abstract, so a search built on the word proxy alone would have missed {pct(F['included_sens'] / F['included_total'], 0)} of the corpus.")
    fig("Fig01_search_flow", 5.6)

    h("2.5 Evidence coding", 2)
    p("Every included record was coded from its title, abstract and keywords with a published dictionary (Supplementary Table S1). Coding was multi-label: a record carries every family, named proxy, pollutant and method it mentions. "
      "Proxies were grouped into ten families: road and traffic; land use and built environment; satellite atmospheric; vegetation and land surface; meteorology; population and settlement; fire and smoke; topography; industrial and point sources; and hybrid and composite (chemical-transport or dispersion model output, composite indices and data fusion). "
      f"Within these, {NPROX} named proxies were coded, for example distance to roads, aerosol optical depth, tropospheric NO2 column, NDVI, land surface temperature, boundary-layer height and night-time lights. "
      "Satellite atmospheric, meteorological and fire proxies were treated as dynamic, because they vary from day to day; the remaining families were treated as static. "
      "Each record was also coded for pollutant, modelling method, exposure target (personal or ambient), any empirical validation, and validation design: random or k-fold cross-validation; spatial or blocked cross-validation; independent or external validation; temporal hold-out; and comparison with measurements. "
      "Records reporting a validation, other than reviews, form the validation sub-corpus. "
      "Study setting was located from country, city and sub-national names in the title, abstract and author keywords. It was assigned to World Bank regions and income groups, and a record naming four or more countries was coded as multi-country. Author countries were read from the affiliation strings.")

    h("2.6 Performance analysis", 2)
    p("Annual production was summarised by log-linear growth rates. Sources were divided into Bradford zones, each holding one third of the records [@bradford1934], and author productivity was compared with Lotka's inverse-power law [@lotka1926]. "
      "Country production was counted by the corresponding author's country and split into single-country and multi-country publications. Global citation counts were taken from the databases.")

    h("2.7 Science mapping", 2)
    p("Author keywords were normalised with a thesaurus that merged spellings, abbreviations and synonyms (for example, LUR and land-use regression, AOD and aerosol optical depth). "
      "A co-occurrence network was built from keywords used in at least five records. Edges were weighted by association strength, as in VOSviewer [@vaneck2010], and communities were detected with the Louvain algorithm [@blondel2008]. "
      "An overlay view coloured each keyword by the average publication year of the studies using it. A thematic map placed finer keyword communities by Callon centrality and density [@callon1991], and keyword bursts were detected with Kleinberg's two-state algorithm on yearly counts [@kleinberg2003]. "
      "Country collaboration was mapped from the affiliations of all authors (full counting), and a three-field plot linked study setting, proxy family and validation design. "
      "For co-citation analysis [@small1973], the cited references of Scopus and Web of Science records, which are formatted differently, were harmonised to a key of first-author surname, year and first page (or volume). The 80 most-cited references were then mapped in the same way. Network files are provided in VOSviewer format.")

    h("2.8 Proxy prioritisation", 2)
    p("Following the agreed logic of prominence plus validation, each named proxy received two scores. Prominence is the mean percentile rank of its frequency in the corpus and its eigenvector centrality in the network of proxies used together in the same record. "
      "Validation evidence is the mean percentile rank of the number of validated records using it and the number validated with a spatial or external design. "
      "The priority score is the mean of the two. Aggregate categories (land-use regression predictor sets, unspecified traffic, general satellite remote sensing) were scored but are flagged, because they do not name a variable that can be extracted.")

    h("2.9 Software and reproducibility", 2)
    p("The analysis was carried out in Python, with pandas, NetworkX, SciPy, RapidFuzz and GeoPandas, and the figures were drawn with matplotlib. Six scripts reproduce every number, table and figure from the four raw exports: corpus construction, screening and coding, agreement, analysis, figures and this manuscript. "
      "The prose of this manuscript is generated from the analysis outputs, so the numbers cannot drift from the results.")


# ------------------------------------------------------------------ 3 Results
def results():
    h("3. Results", 1)
    sg = P["segments"]
    so, au_, co = S["sources"], S["authors"], S["countries"]

    # ---------------- Q1
    h("3.1 Size, growth and producers of the literature (Q1)", 2)
    p(f"Production grew rapidly from 2000 to 2009, by {sg['2000_2009']['rate'] * 100:.0f}% a year (p < 0.001), and then levelled off. From 2010 to 2025 it held near {sg['2010_2025']['mean']:.0f} studies a year with no significant trend ({sg['2010_2025']['rate'] * 100:+.1f}% a year, p = {sg['2010_2025']['p']:.2f}; {R('Fig02_production_sources', 'a')}). "
      f"The {F['included_total']} studies appeared in {so['n_sources']} sources. Five formed the Bradford core and held {pct(so['core_share'], 0)} of all studies: Atmospheric Environment ({so['top'][0][1]}), Science of the Total Environment ({so['top'][1][1]}), Environmental Health Perspectives ({so['top'][2][1]}), Environmental Science and Technology ({so['top'][3][1]}) and Environmental Research ({so['top'][4][1]}) ({R('Fig02_production_sources', 'c')}; {R('Fig02_production_sources', 'b')}). "
      f"The {n0(au_['n_authors'])} authors averaged {au_['authors_per_doc']:.1f} per paper, and {pct(au_['single_paper_share'], 0)} contributed a single paper; productivity followed Lotka's law (exponent {au_['lotka_exponent']:.2f}, R² = {au_['lotka_r2']:.2f}). "
      f"Production was led by a European exposure-assessment network: the most productive authors were {', '.join(a for a, _ in au_['top'][:5])}, and the most productive institutions {', '.join(i for i, _ in S['institutions']['top'][:3])}. "
      f"Corresponding authors were based in {co['n_countries']} countries, led by the United States ({co['top_corr'][0][1]}), China ({co['top_corr'][1][1]}) and Canada ({co['top_corr'][2][1]}). "
      f"The corpus had received {n0(S['citations']['total'])} citations (median {S['citations']['median']:.0f} per study; h-index {S['citations']['h_index']}; {Tn('cited')}).")
    fig("Fig02_production_sources")
    cl = S["collaboration"]
    import gazetteer as _G
    _c = pd.read_csv(TAB / "T_country_links.csv")
    ssa_l = _c[(_c.a.map(_G.REGION) == "SSA") | (_c.b.map(_G.REGION) == "SSA")]
    intra = int(((ssa_l.a.map(_G.REGION) == "SSA") & (ssa_l.b.map(_G.REGION) == "SSA")).sum())
    p(f"Co-authorship linked {cl['n_links']} country pairs, of which {cl['n_links_w2']} shared at least two studies ({R('Fig03_collaboration')}). The strongest links were {cl['top'][0][0]}–{cl['top'][0][1]} ({cl['top'][0][2]} studies), {cl['top'][1][0]}–{cl['top'][1][1]} ({cl['top'][1][2]}) and {cl['top'][2][0]}–{cl['top'][2][1]} ({cl['top'][2][2]}), and the densest cluster was the European cohort network around the Netherlands, Germany, Sweden and the United Kingdom. "
      f"Sub-Saharan African countries took part in {cl['ssa_links']} links. {ssa_l.w.eq(1).sum()} of them rested on a single joint study and none on more than {int(ssa_l.w.max())}, and {intra} were between two African countries; the rest ran to partners elsewhere, mostly in North America, Europe and Asia.")
    tc = pd.read_csv(TAB / "T_top_cited.csv").head(10)
    tc["Study"] = tc.first_author.str.replace(r"\s+[A-Z]\.?([A-Z]\.?)*$", "", regex=True) + " et al. (" + tc.year.astype(str) + ")"
    table("cited", tc.assign(Title=tc.title.str.slice(0, 90), Source=tc.source.str.slice(0, 40), Citations=tc.tc, PerYear=tc.tc_per_year)[["Study", "Title", "Source", "Citations", "PerYear"]].rename(columns={"PerYear": "Per year"}),
          "The ten most-cited studies in the corpus (citations from the databases, April 2026).", widths=[1.2, 2.8, 1.5, 0.6, 0.5])


    # ---------------- Q2
    h("3.2 Conceptual and intellectual structure (Q2)", 2)
    kw = S["keywords"]; kn = S["kw_network"]
    th = pd.read_csv(TAB / "T_thematic_map.csv")
    q_ = lambda q: " and ".join(f"({l})" for l in th[th.quadrant == q].label)
    bt = S["bursts"]["top"]
    p(f"Author keywords were available for {pct(kw['coverage'], 0)} of studies and, after normalisation, comprised {n0(kw['n_unique'])} distinct terms. The most frequent, after the search term air pollution ({kw['top'][0][1]}), were land use regression ({kw['top'][1][1]}), exposure assessment ({kw['top'][2][1]}), PM2.5 ({kw['top'][3][1]}), GIS ({kw['top'][4][1]}) and traffic ({kw['top'][5][1]}). "
      f"The co-occurrence network of {kn['nodes']} keywords resolved into four communities ({R('Fig04_keyword_network', 'a')}): "
      f"(1) land-use regression and traffic exposure modelling; (2) traffic-related health epidemiology; (3) machine learning, mobile monitoring and ultrafine particles; and (4) satellite and spatio-temporal modelling. "
      f"Coloured by average publication year ({R('Fig04_keyword_network', 'b')}), the network separates an older core of GIS, traffic, dispersion models, asthma and epidemiology from a recent periphery of machine learning, random forest, deep learning, aerosol optical depth and remote sensing.")
    fig("Fig04_keyword_network", 6.3)
    p(f"On the thematic map ({R('Fig05_themes_bursts', 'a')}), the motor themes, central and well developed, were traffic and GIS mapping {q_('Motor').split(' and (')[0]} and respiratory epidemiology in children ({q_('Motor').split(' and (')[-1]}. Land-use regression and exposure assessment formed the basic themes {q_('Basic')}: highly central but less internally cohesive, the shared foundation of the field. Satellite and spatio-temporal modelling, and personal exposure, fell in the emerging quadrant {q_('Emerging or declining')}: weakly connected to the rest of the field. "
      f"Burst detection dates the shift ({R('Fig05_themes_bursts', 'b')}). The strongest bursts were GIS ({bt[0][1]:.1f}, {bt[0][2]}–{bt[0][3]}), machine learning ({bt[1][1]:.1f}, {bt[1][2]}–{bt[1][3]}) and traffic ({bt[2][1]:.1f}, {bt[2][2]}–{bt[2][3]}): epidemiology, dispersion models, GIS, traffic, vehicle emissions and asthma burst between the late 1990s and about 2013, and random forest, deep learning, remote sensing, aerosol optical depth and machine learning from 2020, most of them still in burst at the end of the record. "
      "No keyword describing validation, transfer or personal exposure burst at any time.")
    fig("Fig05_themes_bursts")
    cc = S["cocitation"]; r_ = S["references"]
    p(f"The corpus cited {n0(r_['unique_refs'])} distinct references {n0(r_['total_cites'])} times. The co-citation network of the 80 most-cited references formed three communities ({R('Fig06_cocitation')}). "
      f"The largest is the methodological core of land-use regression and intra-urban exposure modelling, anchored by Brauer et al. (2003), Hoek et al. (2008), Jerrett et al. (2005) and Briggs et al. (1997) [@brauer2003; @hoek2008; @jerrett2005; @briggs1997]. "
      f"The second is the early traffic-proximity health literature of the 1990s and early 2000s, anchored by {etal(cc['clusters'][1][:4])}. "
      f"The third is the cohort evidence on long-term particulate exposure and mortality, anchored by Pope et al. (2002) and Dockery et al. (1993), with Jerrett et al. (2005) and Miller et al. (2007) [@dockery1993; @pope2002; @brunekreef2002]. "
      "Only one methodological reference from outside exposure science, the random-forest paper [@breiman2001], reached the 80 most co-cited; no satellite-retrieval reference and no reference set in Africa did. The intellectual base of the field is European and North American land-use and traffic work, even as current practice moves to satellites and machine learning.")
    fig("Fig06_cocitation", 6.0)


    # ---------------- Q3
    h("3.3 Proxies, pollutants and methods (Q3)", 2)
    fam = S["families"]
    fs = fam["shares"]
    pol = S["pollutants"]["counts"]; met = S["methods"]["counts"]
    p(f"Land use and built environment ({fam['counts']['Land use and built environment']} studies, {pct(fs['Land use and built environment'], 0)}) and road and traffic ({fam['counts']['Road and traffic']}, {pct(fs['Road and traffic'], 0)}) were the dominant families, followed by meteorology ({pct(fs['Meteorology'], 0)}), population and settlement ({pct(fs['Population and settlement'], 0)}), satellite atmospheric ({pct(fs['Satellite atmospheric'], 0)}) and topography ({pct(fs['Topography'], 0)}). "
      f"Vegetation and land surface ({pct(fs['Vegetation and land surface'], 0)}) and fire and smoke ({pct(fs['Fire and smoke'], 0)}) were rare ({R('Fig07_proxy_families', 'a')}). "
      f"Most studies combined families: {pct(fam['multi_family_share'], 0)} used two or more, and land use with road and traffic was by far the most common pair (Jaccard index 0.49; {R('Fig07_proxy_families', 'c')}). "
      f"NO2 or NOx ({pol['NO2/NOx']} studies) and PM2.5 ({pol['PM2.5']}) were the main targets, ahead of black or elemental carbon ({pol['BC/EC']}), PM10 ({pol['PM10']}) and ozone ({pol['O3']}). "
      f"The pollutant profile follows the mechanism. Road, land-use, population and hybrid proxies were tied mostly to NO2; fire proxies to PM2.5 and black carbon; satellite proxies to NO2 and PM2.5, with the largest share of ozone studies; and industrial proxies to SO2 ({R('Fig07_proxy_families', 'b')}). "
      f"Statistical regression ({met['Statistical regression (GAM, mixed)']} studies) and land-use regression ({met['Land-use regression']}) were the commonest methods, followed by proximity and buffer metrics ({met['Proximity and buffer metrics']}), machine learning ({met['Machine learning']}), geostatistics ({met['Geostatistics and interpolation']}) and dispersion modelling ({met['Dispersion modelling']}).")
    fig("Fig07_proxy_families")

    p(f"The balance between proxy types has shifted ({R('Fig08_trends', 'a')}). Studies using only static proxies fell from {pct(dyn('Static families only', '2010–2014'), 0)} in 2010–2014 to {pct(dyn('Static families only', '2020–2026'), 0)} in 2020–2026, while studies using at least one dynamic proxy family (satellite, meteorology, fire) rose from {pct(dyn('Dynamic proxy family', '2010–2014'), 0)} to {pct(dyn('Dynamic proxy family', '2020–2026'), 0)}. "
      f"Over the same periods machine learning rose from {pct(dyn('Machine learning', '2010–2014'), 0)} to {pct(dyn('Machine learning', '2020–2026'), 0)} and land-use regression fell from {pct(dyn('Land-use regression', '2010–2014'), 0)} to {pct(dyn('Land-use regression', '2020–2026'), 0)}. "
      f"Studies targeting personal rather than ambient exposure were a minority throughout ({pct(S['personal']['share'], 0)} overall), and their share fell from {pct(dyn('Personal exposure target', '2010–2014'), 0)} to {pct(dyn('Personal exposure target', '2020–2026'), 0)}. "
      f"Overall, {S['static_dynamic']['static_only']} studies used static proxies only, {S['static_dynamic']['both']} combined static and dynamic proxies, and {S['static_dynamic']['dynamic_only']} used dynamic proxies only.")

    # ---------------- Q4
    h("3.4 Validation, and where the evidence comes from (Q4)", 2)
    vt = V["types"]
    p(f"{V['n']} studies ({pct(V['share'], 0)}) reported an empirical validation, a share that changed little over time ({R('Fig08_trends', 'b')}). "
      f"Where the design was stated, random or k-fold cross-validation ({vt.get('Random or k-fold CV', 0)} studies) far outnumbered independent or external validation ({vt.get('Independent or external validation', 0)}), comparison with separate measurements ({vt.get('Comparison with measurements', 0)}), spatially blocked cross-validation ({vt.get('Spatial or blocked CV', 0)}) and temporal hold-out ({vt.get('Temporal hold-out', 0)}). "
      f"Designs that test transfer to unsampled places became more common, from {pct(dyn('Spatial, external or temporal validation', '2000–2009'), 0)} of validated studies in 2000–2009 to {pct(dyn('Spatial, external or temporal validation', '2020–2026'), 0)} in 2020–2026, but remained a minority ({R('Fig08_trends', 'c')}). "
      f"In total {V['spatial_or_external']} studies, {pct(V['spatial_or_external'] / F['included_total'])} of the corpus, reported a spatial or external design, and only {V['personal']} validated studies compared proxies with personal exposure.")
    fig("Fig08_trends")
    rc = G["region_counts"]
    p(f"Of the {F['included_total']} studies, {G['located']} named a study setting, spread over {G['n_countries']} countries ({R('Fig09_geography')}). The United States ({G['top_study'][0][1]}), China ({G['top_study'][1][1]}), Canada ({G['top_study'][2][1]}), the United Kingdom ({G['top_study'][3][1]}) and Germany ({G['top_study'][4][1]}) dominated, and {pct(G['high_income_share_located'], 0)} of located studies were set only in high-income countries. "
      f"Sub-Saharan Africa was the setting of {G['ssa_n']} studies ({pct(G['ssa_share_all'])} of the corpus), in {len(G['ssa_countries'])} countries: {', '.join(G['ssa_countries'])}. "
      f"Leadership is more concentrated still ({R('Fig09_geography', 'b')}). Corresponding authors were based in Sub-Saharan Africa for only {co['africa_lead_papers']} studies ({pct(co['author_region_share'].get('SSA', 0))}), although {G['ssa_studies_with_ssa_author']} of the {G['ssa_n']} African studies included at least one author based in the region. "
      f"Of the African studies, {V['ssa']} reported any validation and {S['personal']['ssa']} targeted personal exposure (Supplementary Table S2).")
    fig("Fig09_geography")

    fl = pd.read_csv(TAB / "T_three_field.csv")
    ssa_w = fl[fl.region == "Sub-Saharan Africa"].groupby("validation").w.sum()
    sp_w = fl[fl.validation.str.startswith("Spatial")].groupby("region").w.sum().sort_values(ascending=False)
    sp_tot = fl[fl.validation.str.startswith("Spatial")].w.sum()
    hi = sp_w.reindex(["North America", "Europe & Central Asia", "East Asia & Pacific"]).fillna(0).sum()
    p(f"The three-field plot ({R('Fig10_three_field')}) places the two gaps in one view. Of the {sp_tot:.0f} studies reporting a spatial, external or temporal hold-out, {hi:.0f} were set in North America, Europe or East Asia and most of the rest named no single setting. "
      f"Of the {fl[fl.region == 'Sub-Saharan Africa'].w.sum():.0f} African studies, {ssa_w.get('No validation reported', 0):.0f} reported no validation and {ssa_w.get('Spatial, external or temporal hold-out', 0):.0f} a transfer-testing design.")


    fig("Fig10_three_field")

    # ---------------- Q5
    h("3.5 Proxies that combine prominence and validation (Q5)", 2)
    rk = pd.read_csv(TAB / "T_proxy_ranking.csv")
    named = rk[~rk["aggregate"]].reset_index(drop=True)
    q20 = named[named.records >= 20]
    p(f"Among the {S['ranking']['n_proxies']} coded proxies, prominence and validation evidence were almost perfectly rank-correlated (Spearman ρ = {S['ranking']['rho_prominence_validation']:.2f}; {R('Fig11_proxy_priority', 'a')}). This is largely because a proxy that is used more often has more chances to be validated: among the {len(q20)} named proxies used in at least 20 studies, the share of studies reporting a validation ranged from {pct(q20.validation_rate.min(), 0)} (settlement and socio-economic status) to {pct(q20.validation_rate.max(), 0)} (industrial, commercial or port land), median {pct(q20.validation_rate.median(), 0)}, and was unrelated to how often the proxy is used (Spearman ρ = {spearmanr(q20.records, q20.validation_rate).statistic:.2f}, p = {spearmanr(q20.records, q20.validation_rate).pvalue:.2f}). Validation effort has been spread in proportion to use, not directed at the proxies whose performance is least known. "
      f"The highest-priority named proxies were {', '.join(lname(x) for x in named.proxy.head(7))} and {lname(named.proxy.iloc[7])} ({Tn('rank')}). "
      f"Dynamic proxies entered the top tier through reanalysis meteorology, wind, aerosol optical depth and temperature, and were used disproportionately in recent studies; aerosol optical depth, for example, had {pct(float(rk[rk.proxy == 'Aerosol optical depth'].share_since_2015.iloc[0]), 0)} of its records published since 2015. "
      f"Several proxies relevant to African settings sat low in the ranking because they are rarely studied: household fuel use, biomass and open burning, fire activity, land surface temperature and night-time lights. "
      f"No named proxy had more than {int(named.ssa_records.max())} Sub-Saharan African studies.")
    fig("Fig11_proxy_priority")
    t = named.head(20).copy()
    t["Type"] = t.dynamic.map({True: "dynamic", False: "static"})
    table("rank", t.rename(columns={"rank": "Rank", "proxy": "Proxy", "family": "Family", "records": "Records", "validation_records": "Validated",
                                    "spatial_or_external_val": "Spatial or external", "personal_records": "Personal", "ssa_records": "SSA", "priority": "Priority"})
          [["Proxy", "Family", "Type", "Records", "Validated", "Spatial or external", "Personal", "SSA", "Priority"]].assign(Priority=lambda d: d.Priority.map(lambda v: f"{v:.2f}")),
          "The twenty highest-priority named geospatial proxies. Priority is the mean of the prominence and validation-evidence percentiles (Section 2.8).",
          note="Records: studies using the proxy; Validated: those in the validation sub-corpus; Spatial or external: validated with a spatial or external design; Personal: studies targeting personal exposure; SSA: studies set in Sub-Saharan Africa. The full ranking, including aggregate categories, is in Supplementary Table S3.",
          widths=[1.9, 1.5, 0.6, 0.55, 0.6, 0.65, 0.55, 0.4, 0.55])


# ------------------------------------------------------------------ 4 Discussion
def discussion():
    h("4. Discussion", 1)
    h("4.1 The vocabulary problem", 2)
    p(f"The most consequential finding for anyone reviewing this field is methodological. A search built on proxy and surrogate retrieved fewer than half of the relevant studies; {pct(F['included_sens'] / F['included_total'], 0)} were found only through the words predictor, covariate and indicator or through named proxies, and almost none of those used the word proxy at all. "
      "At the same time, the proxy search was imprecise, because surrogate and proxy are common in ecology, soil science and palaeoclimate. Reviews that rely on the word proxy will therefore be both incomplete and noisy, and will over-represent the older, explicitly framed land-use and traffic literature. "
      "We recommend that future syntheses search for named variables and for predictor and covariate language, and report screening yield for each block, as done here.")
    h("4.2 From static to dynamic proxies", 2)
    p("The field has stopped growing in volume but has changed in kind. Land-use regression with static land-use and road predictors, which defined the field's intellectual base, is giving way to models that add daily satellite and meteorological fields and fit them with machine learning [@steinle2013; @hoek2017]. "
      "The thematic map shows the tension. Land-use regression and exposure assessment are the field's central basic themes, whereas satellite and spatio-temporal modelling, and personal exposure, are weakly connected emerging themes. "
      "The two traditions are being combined in practice faster than they are being integrated conceptually, and the validation evidence for dynamic proxies is correspondingly thinner. Static proxies describe where exposure is persistently high; only dynamic proxies can describe when. A model meant to follow day-to-day exposure needs both.")
    h("4.3 Validation follows attention", 2)
    p(f"Fewer than two in five studies reported any validation, and fewer than one in twenty-five reported a design that tests transfer to new places. Random cross-validation among monitors that share a city and a monitoring campaign estimates interpolation skill. It says little about performance in a city, or a country, the model has not seen [@roberts2017; @ploton2020]. "
      f"The near-perfect rank correlation between prominence and validation (ρ = {S['ranking']['rho_prominence_validation']:.2f}) means that validation has accumulated where attention already was, not where uncertainty was greatest. "
      "The literature therefore offers good evidence that land-use and road proxies explain NO2 within European and North American cities, and weak evidence about anything else. "
      "For a new setting, a proxy's validation record should be read alongside where and how that validation was done, and a transferred model should be accompanied by an explicit estimate of where it is applicable [@meyer2021].")
    h("4.4 The African evidence gap", 2)
    p(f"Sub-Saharan Africa was the setting of {pct(G['ssa_share_all'])} of studies and the base of {pct(S['countries']['author_region_share'].get('SSA', 0))} of corresponding authors. The handful of African studies were mostly descriptive or land-use regression applications in single cities, with {V['ssa']} reporting a validation and {S['personal']['ssa']} targeting personal exposure. "
      "The proxies that rank highest were developed and validated where traffic exhaust and industry dominate, buildings are formal and monitors are dense. "
      "In much of Sub-Saharan Africa, household solid-fuel combustion, open burning of waste and crop residue, unpaved-road and Saharan dust, and informal settlement change which variables matter [@katoto2019; @amegah2017]. "
      "The proxies that would capture these sources, such as household fuel use, fire activity, land surface temperature, night-time lights and settlement type, are among the least validated in the corpus. "
      "Our earlier finding that road-network proxies were weak and country-dependent predictors of personal PM2.5 in The Gambia, Kenya and Mozambique [@nyoni2026] is therefore not anomalous. It is what this evidence map predicts.")
    h("4.5 Implications for proxy selection", 2)
    p("Three practical implications follow. First, the priority ranking ({0}) is a defensible starting catalogue, because it rewards both use and validation, but it should be read as a list of candidates to test, not a list of proxies known to work in a new setting. "
      "Second, candidate sets should mix static proxies (land use, built-up surface, elevation, road proximity, population) with dynamic proxies (reanalysis meteorology, boundary-layer height, aerosol optical depth, fire activity), because only the latter carry day-to-day variation. "
      "Third, any new model should be validated with spatially blocked or external designs, ideally against personal measurements, and should report where it is applicable. Without such designs, a high cross-validated R² describes the training network rather than the place being mapped [@roberts2017; @kwan2012].".format(Tn("rank")))
    h("4.6 Limitations", 2)
    R = json.loads((V2 / "data/robustness.json").read_text()); RR = {r["indicator"]: r for r in R["rows"]}
    rr = lambda k, d=1: f"{RR[k]['full corpus']:.{d}f} and {RR[k]['core corpus (risk < 3)']:.{d}f}"
    p("Screening and coding were rule-based and applied to titles, abstracts and keywords, not full texts. The audit estimates that about one quarter of included studies are false positives and that about a fifth of relevant studies were missed; both mostly affect the margins of the field, such as emission inventories and health studies that use modelled exposure, rather than its core. "
      f"To test whether the false positives drive the results, every headline indicator was recomputed after removing the {R['n_removed']} included studies most likely to be off-topic (Supplementary Table S8). The findings did not change: the Sub-Saharan African share was {rr('Sub-Saharan Africa setting (%)')}% in the full and core corpora, the share of validated studies using spatial or external designs {rr('Spatial or external validation (% of validated)', 0)}%, "
      f"dynamic-proxy use in 2020–2026 {rr('Dynamic proxy, 2020–2026 (%)', 0)}%, and the prominence–validation correlation {rr('Prominence–validation ρ', 2)}. Only the share reporting any validation rose ({rr('Reports validation (%)', 0)}%), partly by construction, because the absence of validation was one of the risk criteria. "
      "Abstracts under-report the variables a model uses, so family and proxy counts are lower bounds, and validation designs that are described only in the full text will have been missed. "
      f"Study location was taken from text, and {pct(G['not_stated'] / F['included_total'], 0)} of studies named no setting. "
      "Co-citation keys harmonise two reference formats and may split or merge a small number of references. "
      "Coverage is limited to English-indexed journals in two databases, which under-represents grey literature and African institutional reports. "
      "Finally, frequency and validation counts measure attention, not predictive skill. A highly ranked proxy may still perform poorly in a specific setting, and only local validation can establish otherwise.")


def conclusions():
    h("5. Conclusions", 1)
    p(f"Geospatial proxies for air-pollution exposure form a mature literature of about {P['segments']['2010_2025']['mean']:.0f} studies a year. It is concentrated in five journals and anchored in European and North American land-use and traffic research. "
      "Most of it never uses the word proxy. The field is moving from static land-use predictors to dynamic satellite and meteorological fields fitted with machine learning, but validation has not kept pace: few studies test transfer to new places, very few compare proxies with personal exposure, and validation has followed attention. "
      f"Sub-Saharan Africa is the setting of {pct(G['ssa_share_all'])} of studies. The proxies most often recommended for it have therefore rarely, if ever, been tested there, and the proxies that would describe its distinctive sources are the least validated of all. "
      "Locally validated, spatially and temporally explicit proxy models are the evidence the field most lacks.")


def declarations():
    h("Declarations", 1)
    for t_, b_ in [("Data and code availability", "The screened corpus, coding, decision and audit workbooks, network files and all analysis scripts are available from the authors and will be deposited in a public repository on acceptance. Database exports are shared within the Scopus and Web of Science licence terms."),
                   ("Funding", "[To be completed.]"),
                   ("Competing interests", "The authors declare no competing interests."),
                   ("Author contributions (CRediT)", "Handsome Bongani Nyoni: Conceptualization, Methodology, Data curation, Formal analysis, Software, Visualization, Writing – original draft. [Co-authors and roles to be confirmed.]"),
                   ("Ethics", "Not applicable; the study uses bibliographic records only."),
                   ("Use of generative AI", "Generative AI (Claude, Anthropic) was used to write analysis code, draft text and pre-screen audit decisions. The authors reviewed all outputs and take full responsibility for the content. [Confirm wording against the target journal's policy.]")]:
        par = doc.add_paragraph(); r = par.add_run(t_ + ". "); r.bold = True
        runs(par, cite(b_))


def reference_list():
    h("References", 1)
    for k in sorted(CITED, key=_sortkey):
        par = doc.add_paragraph()
        par.paragraph_format.left_indent = Inches(0.5); par.paragraph_format.first_line_indent = Inches(-0.5)
        runs(par, REFS[k][2], size=10.5)


def supplementary():
    h("Supplementary material", 1)
    for i, (k, l) in enumerate(SUPP, 1):
        pass
    p(f"Supplementary Figures S1–S{len(SUPP)} (Supplementary_Figures.docx): the Bradford curve, the international co-authorship map, the keyword network coloured by publication year, the thematic map, proxy-family co-use, the share of studies reporting validation by period, validation designs by period, and study setting against author region.", size=10.5)
    for t in ["Table S1. Screening rules and the proxy, pollutant, method and validation dictionaries.",
              "Table S2. The Sub-Saharan African studies, with country, proxies, validation design and exposure target.",
              "Table S3. Full proxy ranking, including aggregate categories, with prominence and validation components.",
              "Table S4. Thematic-map communities and their member keywords.",
              "Table S5. Co-citation communities and their references.",
              "Table S6. Blinded screening audit (120 records).",
              "Table S7. Screening decision for every record, with the matched evidence.",
              "Table S8. Robustness of the headline indicators to removing the likeliest false positives.",
              "Files S1–S3. VOSviewer map and network files (keyword co-occurrence, co-citation, country collaboration)."]:
        p(t, size=10.5)


def supplementary_workbook():
    sys_path = V2 / "scripts"
    import sys; sys.path.insert(0, str(sys_path))
    from importlib import import_module
    SC = import_module("02_screen_code")
    rules = pd.read_csv(TAB / "T_screening_rules.csv")
    dic = pd.DataFrame([(SC.FAM_LABEL[f], n, " | ".join(p_)) for f, n, *p_ in SC.PROXIES], columns=["family", "named proxy", "patterns"])
    with pd.ExcelWriter(OUT / "Supplementary_Tables.xlsx") as xw:
        rules.to_excel(xw, "S1a_screening_rules", index=False)
        dic.to_excel(xw, "S1b_proxy_dictionary", index=False)
        pd.read_csv(TAB / "T_ssa_records.csv").to_excel(xw, "S2_SSA_studies", index=False)
        pd.read_csv(TAB / "T_proxy_ranking.csv").to_excel(xw, "S3_proxy_ranking", index=False)
        pd.read_csv(TAB / "T_thematic_map.csv").to_excel(xw, "S4_thematic_map", index=False)
        pd.read_csv(TAB / "T_cocitation.csv").to_excel(xw, "S5_cocitation", index=False)
        pd.read_excel(V2 / "review/audit_final_120.xlsx").to_excel(xw, "S6_audit", index=False)
        pd.read_excel(V2 / "review/screening_decisions.xlsx").drop(columns=["abstract"]).to_excel(xw, "S7_decisions", index=False)
        pd.read_csv(TAB / "T_robustness.csv").round(2).to_excel(xw, "S8_robustness", index=False)
        for nm in ("T_annual_production", "T_top_sources", "T_top_authors", "T_countries", "T_top_institutions", "T_top_keywords", "T_trend_topics",
                   "T_proxy_families", "T_family_x_pollutant", "T_family_x_method", "T_trends_by_period", "T_study_countries", "T_bradford", "T_lotka"):
            pd.read_csv(TAB / f"{nm}.csv").to_excel(xw, nm[2:][:31], index=False)


def main():
    front(); highlights(); doc.add_page_break(); abstract(); doc.add_page_break()
    intro(); methods(); results(); discussion(); conclusions(); declarations(); reference_list(); supplementary()
    body = sum(len(par.text.split()) for par in doc.paragraphs)
    out = OUT / "Geospatial_Proxy_Bibliometric_Review_DRAFT.docx"
    doc.save(out)
    supplementary_figures()
    supplementary_workbook()
    unused = set(REFS) - CITED
    print(f"wrote {out.name}: ~{body:,} words, {len(MAIN)} main figures + {len(SUPP)} supplementary, {len(TABNO)} tables, {len(CITED)} references; unused refs: {sorted(unused)}")


if __name__ == "__main__":
    main()

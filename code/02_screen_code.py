"""Step 2 -- title/abstract/keyword screening and multi-label coding.

Every decision is made by an explicit, published rule, so the screening is reproducible and
auditable; the rules are listed in tables/T_screening_rules.csv and every record's decision and
the matched evidence are in review/screening_decisions.xlsx.

Exclusion codes (applied in this order; the first that fires is recorded)
  R1  not about air pollution (marine/aquatic particulates, greenhouse-gas budgets, etc.)
  R2  'proxy'/'surrogate' in an unrelated sense (palaeo-climate archives, computational emulators)
  R3  no geospatial proxy and no spatial component
  R4  the proxy is a physical or biological sample, not a geospatial data layer (biomonitors,
      biomarkers) and no geospatial layer is used alongside it
  R5  indoor or occupational environment only
  R6  emission inventory, atmospheric chemistry, field-campaign or model-process study with no exposure,
      proxy or mapping aim in the title

Coding (multi-label; a record can carry several families, pollutants and methods)
  proxy families and named proxies, pollutant, modelling method, validation design,
  exposure target (ambient / personal), temporal character (static / dynamic), study location.
Validation sub-corpus: included records that report an empirical test of the proxy or model
(validation, cross-validation, comparison with measurements, or a goodness-of-fit metric).
"""
from __future__ import annotations
import re, pickle, json, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import gazetteer as G

V2 = Path(__file__).resolve().parents[1]
DATA, TAB, REV = V2 / "data", V2 / "tables", V2 / "review"


def rx(*pats):
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(pats) + r")", re.I)


# ------------------------------------------------------------------ screening vocabularies
AIR_STRONG = rx(r"air pollut", r"air quality", r"air contamina", r"atmospheric pollut", r"ambient (air|pollut|pm|particul|concentration|exposure|no2|ozone)",
                r"pm[- ]?2\.?5", r"pm₂", r"pm[- ]?10(?![0-9])", r"pm[- ]?1(?![0-9.])", r"incinerator", r"burn pit", r"fine particul", r"respirable particul", r"nitrogen dioxide", r"no2(?![0-9])", r"no ?x(?![a-z])",
                r"ozone", r"o3(?![0-9])", r"black carbon", r"elemental carbon", r"soot", r"sul(ph|f)ur dioxide", r"so2(?![0-9])",
                r"carbon monoxide", r"ultrafine", r"traffic[- ]related", r"smog", r"haze", r"aerosol optical", r"smoke",
                r"vehicular emission", r"vehicle emission", r"exhaust(?![a-z])", r"exhaust (emission|gas|particle)", r"particulate air", r"airborne particul", r"dust storm", r"aeolian dust",
                r"atmospheric (aerosol|particul|deposition|concentration)", r"criteria pollutant", r"volatile organic", r"traffic (exposure|intensity|density|volume|pollut|emission)", r"exposure to traffic", r"co concentration", r"oil and gas development")
AIR_WEAK = rx(r"particulate matter", r"aerosol", r"dust", r"pollutant")
NON_AIR = rx(r"seawater", r"sea water", r"ocean", r"marine (particul|ecosystem|sediment|environment)", r"estuar", r"river water", r"groundwater",
             r"lake water", r"wastewater", r"drinking water", r"soil contamina", r"heavy metals? in soil", r"freshwater", r"coastal water", r"benthic", r"plankton", r"sediment transport", r"suspended (particulate|sediment)s? (matter )?in (the )?(gulf|bay|lake|river|sea|water)", r"water quality", r"turbidity", r"cyanobacteria")
GHG = rx(r"methane", r"greenhouse gas", r"co2 emission", r"carbon dioxide emission", r"carbon emission", r"carbon budget", r"ghg")
PALEO = rx(r"pal(a)?eo", r"holocene", r"pleistocene", r"ice core", r"tree[- ]ring", r"dendro", r"speleothem", r"stalagmite", r"sediment core",
           r"lake sediment", r"peat (core|bog)", r"varve", r"millenni", r"quaternary", r"last glacial", r"pre-?industrial (era|period)")
EMULATOR = rx(r"surrogate model", r"emulat", r"reduced[- ]order model", r"metamodel", r"response surface model", r"proxy server", r"surrogate endpoint", r"surrogate marker")
BIO = rx(r"lichen", r"moss(es)?(?![a-z])", r"bryophyte", r"tree bark", r"biomonitor", r"bio-?indicator", r"pine needle", r"leaf (dust|deposit)", r"leaves as",
         r"honey ?bee", r"spider web", r"biomarker", r"urinary", r"blood (lead|level|sample)", r"toenail", r"exhaled", r"hair sample", r"magnetic (biomonitor|properties of leaves)", r"human biomonitoring", r"hbm4eu", r"biomonitoring")
INDOOR = rx(r"indoor", r"household air", r"in-home", r"inside (the )?(home|house)", r"classroom", r"kitchen", r"cookstove", r"cook ?stove", r"in-vehicle", r"in-cabin",
            r"occupational", r"workplace", r"office building", r"subway (station|car)", r"underground (station|mine)", r"cleanroom", r"aircraft cabin", r"tobacco", r"cigar", r"second[- ]?hand smoke", r"environmental tobacco", r"smoking")
OUTDOOR = rx(r"outdoor", r"ambient", r"urban", r"city", r"cities", r"regional", r"neighbo(u)?rhood", r"street", r"land[- ]use", r"satellite", r"community")

# ------------------------------------------------------------------ proxy dictionary
# (family, named proxy, pattern). Families follow the agreed nine plus industrial sources.
FAM_LABEL = {
    "road": "Road and traffic", "landuse": "Land use and built environment", "satellite": "Satellite atmospheric",
    "vegetation": "Vegetation and land surface", "unspecified": "Covariates named generically", "meteorology": "Meteorology", "population": "Population and settlement",
    "fire": "Fire and smoke", "topography": "Topography", "industrial": "Industrial and point sources",
    "hybrid": "Hybrid and composite"}
STATIC_FAM = {"road", "landuse", "topography", "population", "industrial"}
DYNAMIC_FAM = {"satellite", "meteorology", "fire"}
PROXIES = [
    ("road", "Road density or length", r"road (density|length)", r"length of (major )?roads", r"road network densit", r"street (density|length)"),
    ("road", "Distance or proximity to roads", r"distance to (the )?(nearest )?(major |main )?(road|highway|freeway|motorway|street)", r"proximity to (major |busy |main )?(road|highway|freeway|traffic)",
     r"near(-| )road", r"roadside", r"major road(way)?s?", r"busy (road|street)s?", r"(freeway|highway|motorway)s?(?! performance)", r"residential (proximity|exposure) to (major )?(road|traffic|highway|freeway)", r"(within|buffer)[^.]{0,40}(of|around) (major )?roads?"),
    ("road", "Traffic volume or intensity", r"traffic (volume|intensity|density|count|flow|load)", r"vehicle (count|kilomet|miles)", r"aadt", r"annual average daily traffic", r"vehicle km", r"heavy[- ]duty"),
    ("road", "Traffic (unspecified)", r"traffic"),
    ("road", "Street configuration", r"street canyon", r"sky view factor", r"street geometry", r"aspect ratio of street"),
    ("landuse", "Land-use regression predictors", r"land[- ]use regression", r"lur(?![a-z])"),
    ("landuse", "Land use or land cover class", r"land[- ]use (type|class|categor|variable|mix|data)", r"land[- ]cover", r"corine", r"worldcover", r"landuse", r"land use(?! regression)"),
    ("landuse", "Built-up or impervious surface", r"built[- ]up", r"impervious", r"urban (fraction|extent|area|land)", r"building (density|footprint|height|volume|coverage)",
     r"urban form", r"urban morpholog", r"local climate zone", r"urbani[sz]ation"),
    ("landuse", "Industrial, commercial or port land", r"industrial (land|area|zone)", r"commercial (land|area)", r"port area", r"\bport\b", r"airport", r"railway"),
    ("industrial", "Industrial or point-source proximity", r"industrial (facilit|source|plant|emission|site|activit)", r"power (plant|station)", r"point source",
     r"factor(y|ies)", r"smelter", r"refiner", r"mining", r"quarr", r"brick kiln", r"steel (plant|mill)", r"cement (plant|factor)", r"oil (and|&) gas", r"well pad", r"fracking"),
    ("industrial", "Emission inventory", r"emission inventor", r"emissions? database", r"edgar", r"nei(?![a-z])"),
    ("satellite", "Aerosol optical depth", r"aerosol optical (depth|thickness)", r"aod", r"aot(?![a-z])", r"maiac", r"misr", r"deep blue", r"dark target", r"modis aerosol"),
    ("satellite", "Tropospheric NO2 column", r"tropospheric (no2|nitrogen dioxide)", r"no2 column", r"column no2", r"vertical column", r"omi(?![a-z])", r"tropomi", r"sentinel-?5", r"s5p", r"gome", r"sciamachy"),
    ("satellite", "Other satellite trace gas", r"satellite[- ](derived|based|retriev)[^.]{0,30}(so2|co|hcho|formaldehyde|ozone|nh3|ammonia)", r"iasi", r"mopitt", r"airs(?![a-z])"),
    ("satellite", "Satellite remote sensing (general)", r"satellite", r"remote(ly)? sens", r"modis", r"landsat", r"sentinel", r"viirs", r"earth observation", r"google earth engine", r"himawari", r"goes(?![a-z])", r"calipso"),
    ("vegetation", "Vegetation index (NDVI, EVI)", r"ndvi", r"evi(?![a-z])", r"vegetation index", r"normali[sz]ed difference vegetation"),
    ("vegetation", "Green space or tree canopy", r"green ?space", r"greenness", r"tree canopy", r"tree cover", r"urban green", r"vegetation (cover|density|fraction)", r"forest cover", r"green area"),
    ("vegetation", "Land surface temperature", r"land surface temperature", r"lst(?![a-z])", r"surface urban heat island", r"thermal infrared"),
    ("vegetation", "Other land-surface state", r"soil moisture", r"albedo", r"leaf area index", r"lai(?![a-z])", r"snow cover", r"surface reflectance"),
    ("meteorology", "Visibility or visual range", r"visibility", r"visual range", r"light extinction"),
    ("meteorology", "Boundary-layer height", r"boundary[- ]layer height", r"mixing (layer )?height", r"pblh?(?![a-z])", r"blh(?![a-z])", r"mixing depth"),
    ("meteorology", "Wind", r"wind (speed|direction|field|velocity)", r"wind"),
    ("meteorology", "Temperature", r"(air|ambient|surface) temperature", r"temperature(?! inversion)"),
    ("meteorology", "Humidity and precipitation", r"relative humidity", r"humidity", r"precipitation", r"rainfall", r"dew point"),
    ("meteorology", "Stability, inversion, radiation", r"atmospheric stability", r"inversion", r"solar radiation", r"stagnation", r"ventilation coefficient"),
    ("meteorology", "Reanalysis or NWP fields", r"era-?5", r"era-interim", r"reanalysis", r"merra", r"\bwrf\b(?!-chem)", r"gdas", r"narr(?![a-z])", r"meteorological (data|variable|parameter|factor|condition)"),
    ("population", "Population density", r"population (density|count|distribution|size|data)", r"worldpop", r"landscan", r"census (data|tract|block)", r"gpw"),
    ("population", "Night-time lights", r"night[- ]?time light", r"night ?light", r"nighttime luminosity", r"dmsp", r"viirs[- ]?(dnb|day)", r"black marble", r"artificial light"),
    ("population", "Settlement and socio-economic status", r"settlement", r"informal settlement", r"slum", r"socio-?economic (status|indicator|deprivation)", r"deprivation index", r"income level", r"poverty", r"household density"),
    ("population", "Household fuel use", r"(solid|cooking|household|domestic|residential) (fuel|energy|heating|burning|combustion)", r"wood (burning|stove|smoke)", r"charcoal", r"kerosene", r"biomass fuel"),
    ("fire", "Fire activity and burned area", r"active fire", r"fire (count|hotspot|radiative|activit|detection|emission|event|spot|location)", r"burn(ed|t) area", r"firms", r"\bfrp\b", r"fire[- ]?mask"),
    ("fire", "Biomass and open burning", r"biomass burning", r"open burning", r"crop residue", r"agricultural burning", r"stubble burning", r"waste burning", r"slash[- ]and[- ]burn"),
    ("fire", "Wildfire smoke", r"wildfire", r"bushfire", r"forest fire", r"smoke plume", r"wildland fire", r"(wildfire|fire|biomass|bushfire|forest fire)[- ]smoke", r"smoke (from|of) (wild|forest|bush|biomass|agricultur|fire)"),
    ("topography", "Elevation and terrain", r"elevation", r"altitude", r"digital elevation", r"\bdem\b", r"srtm", r"terrain", r"topograph", r"slope(?! of the regression)", r"valley", r"basin"),
    ("topography", "Distance to coast or water", r"distance to (the )?(coast|sea|ocean|water)", r"coastal proximity", r"coastline"),
    ("hybrid", "Chemical-transport or dispersion model output", r"chemical transport model", r"ctm(?![a-z])", r"cmaq", r"geos-?chem", r"wrf-?chem", r"camx", r"cams(?![a-z])", r"copernicus atmosphere",
     r"dispersion model", r"aermod", r"adms", r"caline", r"calpuff", r"gaussian plume", r"model(l)?ed concentration"),
    ("hybrid", "Composite index or data fusion", r"composite (index|indicator|score|measure)", r"data fusion", r"fused", r"hybrid (model|approach|method|exposure)", r"multi-?source data", r"integrated (index|indicator)"),
]
PROXY_RX = [(f, n, rx(*p)) for f, n, *p in PROXIES]

POLL = [("PM2.5", rx(r"pm ?2\.?5", r"pm₂", r"fine particul", r"fine particle", r"fine pm")),
        ("PM10", rx(r"pm ?10(?![0-9])", r"coarse particul", r"respirable particul")),
        ("NO2/NOx", rx(r"no2(?![0-9])", r"nitrogen dioxide", r"no ?x(?![a-z])", r"nitrogen oxide")),
        ("O3", rx(r"ozone", r"o3(?![0-9])")),
        ("BC/EC", rx(r"black carbon", r"elemental carbon", r"soot", r"bc(?![a-z])", r"absorbance", r"black smoke")),
        ("UFP", rx(r"ultrafine", r"particle number", r"ufp", r"pnc(?![a-z])")),
        ("SO2", rx(r"sul(ph|f)ur dioxide", r"so2(?![0-9])")),
        ("CO", rx(r"carbon monoxide", r"(?<![a-z])co(?= (concentration|exposure|level|emission))")),
        ("VOC/PAH", rx(r"volatile organic", r"voc", r"benzene", r"btex", r"polycyclic aromatic", r"pah", r"formaldehyde")),
        ("Dust/metals", rx(r"dust(?![a-z])", r"mineral dust", r"heavy metal", r"trace metal", r"lead (concentration|exposure)")),
        ("PM (unspecified)", rx(r"particulate matter", r"particulate pollut", r"total suspended", r"tsp(?![a-z])", r"aerosol(?! optical)"))]

METHOD = [("Land-use regression", rx(r"land[- ]use regression", r"lur(?![a-z])")),
          ("Dispersion modelling", rx(r"dispersion model", r"aermod", r"adms", r"caline", r"calpuff", r"gaussian plume", r"ospm", r"street canyon model")),
          ("Chemical-transport modelling", rx(r"chemical transport model", r"cmaq", r"geos-?chem", r"wrf-?chem", r"camx", r"chimere", r"emep", r"lotos")),
          ("Satellite-to-surface estimation", rx(r"satellite[- ](derived|based|retriev)", r"aod[- ](pm|to)", r"(estimat|predict|deriv)[a-z]* (ground|surface)[- ]level", r"ground-level pm")),
          ("Geostatistics and interpolation", rx(r"kriging", r"geostatist", r"inverse distance", r"idw", r"interpolat", r"bayesian maximum entropy", r"variogram")),
          ("Machine learning", rx(r"machine learning", r"random forest", r"gradient boost", r"xgboost", r"lightgbm", r"catboost", r"neural network", r"deep learning",
                                  r"support vector", r"convolutional", r"lstm", r"super ?learner", r"stack(ed|ing) (ensemble|model|regress)", r"ensemble learning", r"artificial intelligence", r"decision tree", r"boosted regression")),
          ("Spatial regression and GWR", rx(r"geographically (and temporally )?weighted", r"gwr", r"spatial (lag|error|autoregress|regression)", r"spatial econometric", r"spatial durbin")),
          ("Statistical regression (GAM, mixed)", rx(r"generali[sz]ed additive", r"gam(?![a-z])", r"mixed[- ]effect", r"linear (mixed|regression)", r"multiple (linear )?regression", r"regression model")),
          ("Proximity and buffer metrics", rx(r"buffer", r"proximity", r"distance[- ]based", r"distance-weighted")),
          ("Personal or mobile monitoring", rx(r"personal (exposure|monitor|sampl|measure)", r"wearable", r"gps", r"mobile monitor", r"time[- ]activity", r"microenvironment", r"portable (sensor|monitor)", r"low-?cost sensor"))]

VAL_ANY = rx(r"validat", r"cross[- ]?validat", r"hold[- ]?out", r"leave[- ]one[- ]out", r"loocv", r"r2(?![0-9])", r"r²", r"r-squared", r"r\^2", r"coefficient of determination",
             r"rmse", r"root mean squar", r"mean absolute error", r"mae(?![a-z])", r"model performance", r"predictive (performance|accuracy|ability)", r"explained (\d+|variance)",
             r"(compared|comparison) (with|to|against) (ground|in[- ]situ|monitor|measure|observ|station)", r"agreement with", r"evaluat[a-z]* (against|with) (measure|observ|monitor|ground)")
VAL_TYPE = [("Random or k-fold CV", rx(r"cross[- ]?validat", r"\d+-fold", r"k-fold", r"leave[- ]one[- ]out", r"loocv", r"bootstrap")),
            ("Spatial or blocked CV", rx(r"spatial(ly)?[- ](block|cross|cv|held|hold|independent|cluster)", r"leave[- ](one[- ])?(site|station|city|region|country|area|location|cluster)s?[- ]out",
                                         r"blocked cross", r"spatial block", r"site-based cross", r"by-site", r"station-based cross")),
            ("Independent or external validation", rx(r"external(ly)? validat", r"independent (validation|data|monitor|site|measure|test|dataset)", r"out-of-sample", r"withheld",
                                                     r"held-out site", r"transferab", r"another city", r"unseen")),
            ("Temporal hold-out", rx(r"temporal (validation|hold|cross)", r"(future|subsequent) year", r"leave[- ]one[- ](year|month|day)[- ]out", r"back-?extrapolat", r"forecast(ing)? (skill|accuracy)")),
            ("Comparison with measurements", rx(r"(compared|comparison) (with|to|against) (ground|in[- ]situ|monitor|measure|observ|station)", r"evaluat[a-z]* (against|with) (measure|observ|monitor|ground)", r"agreement with"))]

PERSONAL = rx(r"personal (exposure|monitor|sampl|measure|pm|air)", r"wearable", r"gps", r"time[- ]activity", r"microenvironment", r"individual[- ]level exposure",
              r"individual exposure", r"portable (sensor|monitor)", r"activity[- ]based", r"mobility (pattern|data)", r"dynamic exposure", r"space[- ]time path")
DYNAMIC_T = rx(r"daily", r"hourly", r"day-to-day", r"spatio-?temporal", r"space-?time", r"time-?varying", r"temporal(ly)? (variation|resolution|dynamic|resolved)", r"diurnal",
               r"weekly", r"monthly", r"short-?term", r"near[- ]real[- ]time", r"real[- ]time")
STATIC_T = rx(r"annual (average|mean)", r"long-?term (average|mean|exposure)", r"multi-?year average", r"cross-?sectional", r"static")
REVIEW = rx(r"review", r"meta-?analys", r"bibliometric", r"state of the art", r"overview")

GEO_EXTRA = rx(r"spatial", r"geospatial", r"gis(?![a-z])", r"geographic", r"map(s|ping|ped)?(?![a-z])", r"grid(ded)?", r"high[- ]resolution", r"intra-?urban", r"neighbo(u)?rhood",
               r"geocod", r"residential address", r"spatially", r"hot ?spot", r"surface(s)? of", r"km resolution", r"\d+ ?m resolution")


WEAK = {"Traffic (unspecified)", "Wind", "Temperature", "Humidity and precipitation", "Stability, inversion, radiation",
        "Settlement and socio-economic status", "Elevation and terrain", "Industrial, commercial or port land", "Other land-surface state",
        "Wildfire smoke", "Industrial or point-source proximity", "Satellite remote sensing (general)",
        "Household fuel use", "Biomass and open burning", "Reanalysis or NWP fields",
        "Chemical-transport or dispersion model output"}
ESTIM = rx(r"land[- ]use regression", r"lur(?![a-z])", r"exposure (assessment|estimat|model|surface|map|assign)", r"estimat[a-z]* (exposure|concentration|ground|surface)",
           r"predict[a-z]* (exposure|concentration|pm|no2|air)", r"model(l)?(ed|ing)? (exposure|concentration|air pollut|pm|no2|spatial)", r"spatial (variation|distribution|pattern|model|predict|heterogen)",
           r"concentration (surface|map|field)", r"kriging", r"interpolat", r"machine learning", r"random forest", r"neural network", r"dispersion model", r"chemical transport",
           r"satellite[- ](derived|based|retriev|observ)", r"remote(ly)? sens", r"buffer", r"proximity to", r"distance to", r"downscal", r"hot ?spot", r"geographic(al)? information")
DRIVERS = rx(r"(influencing|driving|explanatory|socio-?economic|natural|environmental|anthropogenic|spatial|geographic(al)?) (factor|variable|driver|determinant)s?",
             r"drivers?", r"determinants?", r"covariates?", r"predictors?", r"influencing factors?", r"mobility", r"travel pattern", r"time[- ]activity")
EXPO = rx(r"exposure", r"exposed", r"epidemiolog", r"health", r"cohort", r"residential", r"residence", r"mortality", r"morbidity", r"asthma", r"population[- ]weighted")
PROCESS = rx(r"emission inventor", r"emission factor", r"inventory of", r"source apportionment", r"chemical (composition|characteri[sz]ation|kinetic|mechanism)", r"kinetic",
             r"formation (of|mechanism)", r"aging of", r"chamber", r"oxidation", r"secondary organic aerosol", r"brown carbon", r"(cmaq|geos-?chem|wrf-?chem|camx|chemical transport model)[- ](simulat|evaluat|model)",
             r"model evaluation", r"field (campaign|experiment)", r"aircraft", r"flight", r"engine", r"fuel (blend|oxygen|propert)", r"combustion (test|characteri)", r"fireworks?", r"dry deposition", r"wet deposition",
             r"emissions? (preparation|downscal|allocation|processing)", r"downscaling (national )?.{0,30}emission", r"spatial (surrogates|allocation)", r"tropospheric chemistry",
             r"conversion rate", r"injection height", r"oxidative potential", r"bioaerosol", r"life cycle", r"lca(?![a-z])", r"crop (loss|yield)", r"aot40", r"atmospheric deposition", r"radar")
INVENTORY = rx(r"emission inventor", r"emissions? (inventor|disaggregat|allocat|downscal)", r"inventor(y|ies) of", r"(biomass burning|wood burning|aviation|shipping) emissions?",
               r"integrated assessment", r"source-receptor", r"emission reductions?")
ESTIM_T = rx(r"land[- ]use regression", r"exposure", r"spatial (variation|distribution|model|predict)", r"predict", r"estimat", r"mapping", r"map(s)?(?![a-z])", r"satellite", r"proxy", r"surrogate", r"indicator")
PROXYLANG = rx(r"proxy", r"proxies", r"surrogate", r"predictor", r"covariate", r"explanatory variable", r"indicator", r"determinant", r"independent variable")


def text_of(r):
    return " ".join([r["title"], r["abstract"], "; ".join(r["kw_author"]), "; ".join(r["kw_index"])])


def screen(r):
    t = text_of(r)
    ti_ab = r["title"] + " " + r["abstract"]
    ev = {}
    proxies = sorted({(f, n) for f, n, p in PROXY_RX if p.search(t)})
    fams = sorted({f for f, _ in proxies})
    # air pollution must be the topic, not a passing mention: in the title or author keywords,
    # or at least twice in the abstract (index keywords are too noisy to establish topic)
    head = r["title"] + " " + "; ".join(r["kw_author"])
    strong = AIR_STRONG.search(head) or len(AIR_STRONG.findall(r["abstract"])) >= 3
    if not strong:
        return "R1", "no air-pollution focus", proxies, fams
    if not AIR_STRONG.search(ti_ab) and NON_AIR.search(ti_ab):
        return "R1", "aquatic or soil particulates", proxies, fams
    if PALEO.search(ti_ab) and not re.search(r"(?i)air quality|air pollut|exposure", ti_ab):
        return "R2", "palaeo-environmental proxy", proxies, fams
    tiab_prox = sorted({(f, n) for f, n, p in PROXY_RX if p.search(ti_ab)})
    strong_layer = sorted({f for f, n in tiab_prox if n not in WEAK})
    weak_layer = sorted({f for f, n in tiab_prox if n in WEAK})
    spatial = bool(GEO_EXTRA.search(ti_ab))
    expo = bool(EXPO.search(ti_ab))
    context = bool(ESTIM.search(ti_ab)) or (bool(PROXYLANG.search(ti_ab)) and (expo or spatial)) or (spatial and expo)
    data_layer = strong_layer if context else []
    personal = bool(PERSONAL.search(ti_ab))
    if not data_layer and weak_layer and (ESTIM.search(ti_ab) or (spatial and PROXYLANG.search(ti_ab)) or personal):
        data_layer = weak_layer
    if EMULATOR.search(r["title"]) and not EXPO.search(r["title"]):
        return "R2", "computational surrogate or emulator", proxies, fams
    if INVENTORY.search(r["title"]) and not EXPO.search(r["title"]):
        return "R6", "emission inventory, chemistry or model-process study", proxies, fams
    if PROCESS.search(r["title"]) and not (EXPO.search(r["title"]) or PROXYLANG.search(r["title"]) or ESTIM_T.search(r["title"])):
        return "R6", "emission inventory, chemistry or model-process study", proxies, fams
    if EMULATOR.search(ti_ab) and not data_layer:
        return "R2", "computational surrogate or emulator", proxies, fams
    if BIO.search(r["title"]) and not re.search(r"(?i)land[- ]use regression|satellite|gis", r["title"]):
        return "R4", "biological or material sample as proxy", proxies, fams
    if BIO.search(r["title"] + " " + r["abstract"][:400]) and not data_layer:
        return "R4", "biological or material sample as proxy", proxies, fams
    if INDOOR.search(r["title"]) and not OUTDOOR.search(r["title"]):
        return "R5", "indoor or occupational only", proxies, fams
    if INDOOR.search(ti_ab) and not OUTDOOR.search(ti_ab) and not data_layer:
        return "R5", "indoor or occupational only", proxies, fams
    if not data_layer and spatial and DRIVERS.search(ti_ab) and (ESTIM.search(ti_ab) or personal):
        data_layer = ["unspecified"]          # explanatory covariates named only generically
        fams = fams + ["unspecified"] if "unspecified" not in fams else fams
    if not data_layer and personal and ESTIM.search(ti_ab):
        data_layer = ["unspecified"]
        fams = fams + ["unspecified"] if "unspecified" not in fams else fams
    if not data_layer:
        return "R3", "no geospatial proxy or spatial component", proxies, fams
    return "INCLUDED", "", proxies, fams


def code(r, proxies, fams):
    t = text_of(r)
    ti_ab = r["title"] + " " + r["abstract"]
    # 'traffic (unspecified)' only when no more specific road proxy was found
    named = [n for f, n in proxies]
    if any(n in named for n in ("Road density or length", "Distance or proximity to roads", "Traffic volume or intensity")):
        named = [n for n in named if n != "Traffic (unspecified)"]
    if any(n in named for n in ("Aerosol optical depth", "Tropospheric NO2 column", "Other satellite trace gas")):
        named = [n for n in named if n != "Satellite remote sensing (general)"]
    polls = [p for p, x in POLL if x.search(t)]
    if len(polls) > 1 and "PM (unspecified)" in polls and ("PM2.5" in polls or "PM10" in polls):
        polls.remove("PM (unspecified)")
    meths = [m for m, x in METHOD if x.search(t)]
    vals = [v for v, x in VAL_TYPE if x.search(ti_ab)]
    val_any = bool(VAL_ANY.search(ti_ab)) or bool(vals)
    isos = G.study_countries(ti_ab + " " + "; ".join(r["kw_author"]))
    macro = G.macro_regions(ti_ab)
    regions = sorted({G.REGION[i] for i in isos})
    if not isos:
        if "SSA" in macro or "AFR" in macro:
            regions = ["SSA"] if "SSA" in macro else ["AFR"]
    if len(isos) >= 4 or (not isos and "GLOBAL" in macro):
        scope = "Global or multi-country"
    elif isos or regions:
        scope = "Country or regional"
    else:
        scope = "Not stated"
    return dict(
        families=fams, proxies=sorted(set(named)), n_families=len(fams),
        has_static=bool(set(fams) & STATIC_FAM), has_dynamic=bool(set(fams) & DYNAMIC_FAM),
        pollutants=polls, methods=meths, validation=val_any, val_types=vals,
        personal=bool(PERSONAL.search(ti_ab)), temporal_dynamic=bool(DYNAMIC_T.search(ti_ab)), temporal_static=bool(STATIC_T.search(ti_ab)),
        is_review=r["doc_type_std"] == "Review" or bool(REVIEW.search(r["title"])),
        study_iso=isos, study_regions=regions, scope=scope,
        africa=any(G.REGION.get(i) == "SSA" for i in isos) or "SSA" in regions or "AFR" in regions,
        ssa=any(G.REGION.get(i) == "SSA" for i in isos) or "SSA" in regions,
    )


def author_countries(r):
    cs = [G.aff_country(a) for a in r["affiliations"]]
    cs = [c for c in cs if c]
    # corresponding/first: Scopus correspondence address ends with a country; WoS RP likewise
    corr = G.aff_country(r["corresp"].split("; email")[0].split(";")[-1]) if r["corresp"] else None
    if not corr:
        corr = G.aff_country(r["corresp"]) if r["corresp"] else None
    if not corr and cs:
        corr = cs[0]
    return sorted(set(cs)), corr


def main():
    df = pickle.load(open(DATA / "records_all.pkl", "rb"))
    # human verdicts from review/HUMAN_CHECKLIST.xlsx (scripts/08_checklist.py apply) override the rules
    hf = DATA / "human_overrides.json"
    HUMAN = json.loads(hf.read_text()).get("screening", {}) if hf.exists() else {}
    out = []
    for _, r in df.iterrows():
        dec, why, proxies, fams = screen(r)
        if HUMAN.get(r["rid"]) == "EXCLUDE" and dec == "INCLUDED":
            dec, why = "RH", "excluded on human review"
        elif HUMAN.get(r["rid"]) == "INCLUDE" and dec != "INCLUDED":
            dec, why = "INCLUDED", f"included on human review (rules: {dec})"
            if not fams:
                fams = ["unspecified"]
        rec = dict(rid=r["rid"], decision=dec, reason=why)
        rec.update(code(r, proxies, fams))
        ac, corr = author_countries(r)
        rec.update(aff_countries=ac, corr_country=corr, mcp=len(ac) > 1)
        out.append(rec)
    c = pd.DataFrame(out)
    df = df.merge(c, on="rid")
    df["included"] = df["decision"] == "INCLUDED"
    df["val_subcorpus"] = df["included"] & df["validation"] & ~df["is_review"]
    pickle.dump(df, open(DATA / "records_coded.pkl", "wb"))

    # decisions workbook for audit
    keep = ["rid", "corpus", "db", "in_scopus", "in_wos", "year", "title", "source", "doi", "decision", "reason", "families", "proxies",
            "pollutants", "methods", "validation", "val_types", "personal", "study_iso", "study_regions", "scope", "corr_country", "abstract"]
    x = df[keep].copy()
    for col in ("families", "proxies", "pollutants", "methods", "val_types", "study_iso", "study_regions"):
        x[col] = x[col].map("; ".join)
    x.to_excel(REV / "screening_decisions.xlsx", index=False)

    rules = [("R1", "Not about air-pollution assessment or exposure", "Air pollution is not the topic (not in the title or author keywords, fewer than three mentions in the abstract), or particulates only in an aquatic or soil context"),
             ("R2", "Proxy in an unrelated sense", "Palaeo-environmental archive, or a computational surrogate/emulator with no geospatial data layer"),
             ("R4", "Non-geospatial proxy", "Biomonitor or biomarker as the proxy, with no geospatial data layer alongside"),
             ("R5", "Indoor or occupational only", "Indoor/occupational setting with no outdoor, ambient or geospatial component"),
             ("R6", "Process or inventory study", "Emission inventory, atmospheric chemistry, field campaign or model-process study with no exposure, proxy or mapping aim"),
             ("R3", "No geospatial proxy", "No geospatial proxy family and no spatial component"),
             ("RH", "Excluded on human review", "Included by the rules but judged off-topic on the human title check"),
             ("INCLUDED", "Retained", "Uses, compares, validates or reviews geospatial or environmental proxies to assess air pollution or exposure")]
    pd.DataFrame(rules, columns=["code", "label", "rule"]).to_csv(TAB / "T_screening_rules.csv", index=False)
    s = df.groupby(["corpus", "decision"]).size().unstack(fill_value=0)
    print(s); print(df.groupby("corpus")["included"].mean())
    print("validation sub-corpus:", df.val_subcorpus.sum(), " SSA:", df[df.included].ssa.sum())


if __name__ == "__main__":
    main()

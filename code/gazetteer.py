"""Country gazetteer: ISO3, World Bank region, World Bank income group (FY2025), and the
names, adjectives, sub-national units and large cities used to locate a study from its
title, abstract and keywords, and an author from an affiliation string.

Regions: EAP East Asia & Pacific, ECA Europe & Central Asia, LAC Latin America & Caribbean,
MENA Middle East & North Africa, NAM North America, SAS South Asia, SSA Sub-Saharan Africa.
Income: H high, UM upper-middle, LM lower-middle, L low.
"""
import re

# iso3: (display name, region, income, [study-text patterns], [affiliation country strings])
C = {
 # ---------------- Sub-Saharan Africa
 "AGO": ("Angola", "SSA", "LM", ["angola", "luanda"], ["Angola"]),
 "BEN": ("Benin", "SSA", "LM", ["benin", "cotonou"], ["Benin"]),
 "BWA": ("Botswana", "SSA", "UM", ["botswana", "gaborone"], ["Botswana"]),
 "BFA": ("Burkina Faso", "SSA", "L", ["burkina faso", "ouagadougou"], ["Burkina Faso"]),
 "BDI": ("Burundi", "SSA", "L", ["burundi"], ["Burundi"]),
 "CMR": ("Cameroon", "SSA", "LM", ["cameroon", "yaound", "douala"], ["Cameroon"]),
 "CPV": ("Cabo Verde", "SSA", "UM", ["cape verde", "cabo verde"], ["Cape Verde", "Cabo Verde"]),
 "CAF": ("Central African Rep.", "SSA", "L", ["central african republic"], ["Central African Republic"]),
 "TCD": ("Chad", "SSA", "L", [r"(?-i:Chad)(?! time)(?! [A-Z])(?! activity)", "n'djamena", "lake chad"], ["Chad"]),
 "COD": ("DR Congo", "SSA", "L", ["democratic republic of (the )?congo", r"\bdrc\b", "kinshasa"], ["Democratic Republic Congo", "Congo (Kinshasa)"]),
 "COG": ("Congo", "SSA", "LM", [r"republic of (the )?congo", "brazzaville"], ["Congo", "Rep Congo"]),
 "CIV": ("Cote d'Ivoire", "SSA", "LM", ["ivory coast", "c[oô]te d.ivoire", "abidjan"], ["Cote Ivoire", "Côte d'Ivoire", "Cote d'Ivoire"]),
 "ETH": ("Ethiopia", "SSA", "L", ["ethiopia", "addis ababa"], ["Ethiopia"]),
 "GAB": ("Gabon", "SSA", "UM", ["gabon"], ["Gabon"]),
 "GMB": ("The Gambia", "SSA", "L", ["gambia", "banjul"], ["Gambia", "The Gambia"]),
 "GHA": ("Ghana", "SSA", "LM", ["ghana", "accra", "kumasi"], ["Ghana"]),
 "GIN": ("Guinea", "SSA", "LM", [r"(?<!new )(?<!equatorial )\bguinea\b(?!-bissau)(?! pig)", "conakry"], ["Guinea"]),
 "KEN": ("Kenya", "SSA", "LM", ["kenya", "nairobi", "mombasa", "kilifi", "kisumu"], ["Kenya"]),
 "LSO": ("Lesotho", "SSA", "LM", ["lesotho"], ["Lesotho"]),
 "LBR": ("Liberia", "SSA", "L", ["liberia"], ["Liberia"]),
 "MDG": ("Madagascar", "SSA", "L", ["madagascar"], ["Madagascar"]),
 "MWI": ("Malawi", "SSA", "L", ["malawi", "blantyre", "lilongwe"], ["Malawi"]),
 "MLI": ("Mali", "SSA", "L", [r"\bmali\b", "bamako"], ["Mali"]),
 "MRT": ("Mauritania", "SSA", "LM", ["mauritania"], ["Mauritania"]),
 "MUS": ("Mauritius", "SSA", "UM", ["mauritius"], ["Mauritius"]),
 "MOZ": ("Mozambique", "SSA", "L", ["mozambique", "maputo", "manhi[cç]a"], ["Mozambique"]),
 "NAM": ("Namibia", "SSA", "UM", ["namibia", "windhoek"], ["Namibia"]),
 "NER": ("Niger", "SSA", "L", [r"\bniger\b(?! delta)", "niamey"], ["Niger"]),
 "NGA": ("Nigeria", "SSA", "LM", ["nigeria", "lagos", "abuja", "ibadan", "port harcourt", "niger delta", "kano"], ["Nigeria"]),
 "RWA": ("Rwanda", "SSA", "L", ["rwanda", "kigali"], ["Rwanda"]),
 "SEN": ("Senegal", "SSA", "LM", ["senegal", "dakar"], ["Senegal"]),
 "SLE": ("Sierra Leone", "SSA", "L", ["sierra leone", "freetown"], ["Sierra Leone"]),
 "SOM": ("Somalia", "SSA", "L", ["somalia"], ["Somalia"]),
 "ZAF": ("South Africa", "SSA", "UM", ["south africa", "johannesburg", "cape town", "durban", "pretoria", "gauteng", "highveld", "soweto", "mpumalanga", "kwazulu"], ["South Africa"]),
 "SSD": ("South Sudan", "SSA", "L", ["south sudan"], ["South Sudan"]),
 "SDN": ("Sudan", "SSA", "L", [r"(?<!south )\bsudan\b", "khartoum"], ["Sudan"]),
 "TZA": ("Tanzania", "SSA", "LM", ["tanzania", "dar es salaam"], ["Tanzania"]),
 "TGO": ("Togo", "SSA", "L", [r"\btogo\b", "lom[eé]"], ["Togo"]),
 "UGA": ("Uganda", "SSA", "L", ["uganda", "kampala"], ["Uganda"]),
 "ZMB": ("Zambia", "SSA", "LM", ["zambia", "lusaka", "copperbelt"], ["Zambia"]),
 "ZWE": ("Zimbabwe", "SSA", "LM", ["zimbabwe", "harare", "bulawayo"], ["Zimbabwe"]),
 # ---------------- Middle East & North Africa
 "DZA": ("Algeria", "MENA", "UM", ["algeria", "algiers"], ["Algeria"]),
 "EGY": ("Egypt", "MENA", "LM", ["egypt", "cairo", "nile delta"], ["Egypt"]),
 "MAR": ("Morocco", "MENA", "LM", ["morocco", "casablanca", "rabat"], ["Morocco"]),
 "TUN": ("Tunisia", "MENA", "LM", ["tunisia"], ["Tunisia"]),
 "LBY": ("Libya", "MENA", "UM", ["libya"], ["Libya"]),
 "IRN": ("Iran", "MENA", "UM", [r"\biran\b", "tehran", "isfahan", "ahvaz", "khuzestan", "mashhad", "tabriz", "shiraz"], ["Iran"]),
 "IRQ": ("Iraq", "MENA", "UM", [r"\biraq\b", "baghdad"], ["Iraq"]),
 "ISR": ("Israel", "MENA", "H", ["israel", "tel aviv", "jerusalem", "haifa"], ["Israel"]),
 "JOR": ("Jordan", "MENA", "LM", [r"\bjordan\b", "amman"], ["Jordan"]),
 "KWT": ("Kuwait", "MENA", "H", ["kuwait"], ["Kuwait"]),
 "LBN": ("Lebanon", "MENA", "LM", ["lebanon", "beirut"], ["Lebanon"]),
 "OMN": ("Oman", "MENA", "H", [r"\boman\b", "muscat"], ["Oman"]),
 "QAT": ("Qatar", "MENA", "H", ["qatar", "doha"], ["Qatar"]),
 "SAU": ("Saudi Arabia", "MENA", "H", ["saudi", "riyadh", "jeddah"], ["Saudi Arabia"]),
 "ARE": ("United Arab Emirates", "MENA", "H", ["united arab emirates", r"\buae\b", "dubai", "abu dhabi"], ["U Arab Emirates", "United Arab Emirates"]),
 "SYR": ("Syria", "MENA", "L", ["syria"], ["Syria"]),
 "YEM": ("Yemen", "MENA", "L", ["yemen"], ["Yemen"]),
 "PSE": ("Palestine", "MENA", "LM", ["palestin", "gaza", "west bank"], ["Palestine"]),
 "BHR": ("Bahrain", "MENA", "H", ["bahrain"], ["Bahrain"]),
 "CYP": ("Cyprus", "ECA", "H", ["cyprus"], ["Cyprus"]),
 "TUR": ("Turkey", "ECA", "UM", ["turkey", "t[uü]rkiye", "istanbul", "ankara", "izmir"], ["Turkey", "Turkiye", "Türkiye"]),
 # ---------------- South Asia
 "IND": ("India", "SAS", "LM", ["india", "delhi", "mumbai", "kolkata", "chennai", "bangalore", "bengaluru", "hyderabad", "pune", "kanpur", "ahmedabad", "indo-gangetic", "lucknow", "tamil nadu", "punjab, india", "uttar pradesh", "varanasi", "agra", "jaipur", "patna", "kerala", "odisha", "gujarat", "maharashtra"], ["India"]),
 "PAK": ("Pakistan", "SAS", "LM", ["pakistan", "lahore", "karachi", "islamabad", "peshawar"], ["Pakistan"]),
 "BGD": ("Bangladesh", "SAS", "LM", ["bangladesh", "dhaka", "chittagong", "chattogram"], ["Bangladesh"]),
 "NPL": ("Nepal", "SAS", "LM", ["nepal", "kathmandu"], ["Nepal"]),
 "LKA": ("Sri Lanka", "SAS", "LM", ["sri lanka", "colombo"], ["Sri Lanka"]),
 "AFG": ("Afghanistan", "SAS", "L", ["afghanistan", "kabul"], ["Afghanistan"]),
 "BTN": ("Bhutan", "SAS", "LM", ["bhutan"], ["Bhutan"]),
 # ---------------- East Asia & Pacific
 "CHN": ("China", "EAP", "UM", ["china", "chinese", "beijing", "shanghai", "guangzhou", "shenzhen", "wuhan", "chengdu", "chongqing", "tianjin", "hebei", "nanjing", "hangzhou", "xi'an", "xian", "lanzhou", "harbin", "shenyang", "jinan", "zhengzhou", "yangtze river delta", "pearl river delta", "jing-jin-ji", "sichuan", "guangdong", "jiangsu", "zhejiang", "shandong", "henan", "hubei", "hunan", "anhui", "fujian", "shaanxi", "shanxi", "xinjiang", "tibet", "qinghai", "inner mongolia", "yunnan", "guizhou", "liaoning", "jilin", "heilongjiang", "jiangxi", "gansu", "ningxia", "fenwei", "north china plain", "hong kong", "macau", "macao"], ["China", "Peoples R China", "Hong Kong", "Macau", "Macao"]),
 "TWN": ("Taiwan", "EAP", "H", ["taiwan", "taipei", "kaohsiung", "taichung"], ["Taiwan"]),
 "JPN": ("Japan", "EAP", "H", ["japan", "tokyo", "osaka", "kyoto", "fukuoka", "nagoya"], ["Japan"]),
 "KOR": ("South Korea", "EAP", "H", ["korea", "seoul", "busan", "incheon"], ["South Korea", "Korea", "Republic of Korea"]),
 "PRK": ("North Korea", "EAP", "L", ["north korea", "pyongyang"], ["North Korea"]),
 "MNG": ("Mongolia", "EAP", "UM", [r"(?<!inner )mongolia", "ulaanbaatar", "ulan bator"], ["Mongolia"]),
 "VNM": ("Vietnam", "EAP", "LM", ["vietnam", "viet nam", "hanoi", "ho chi minh"], ["Vietnam", "Viet Nam"]),
 "THA": ("Thailand", "EAP", "UM", ["thailand", "bangkok", "chiang mai"], ["Thailand"]),
 "MYS": ("Malaysia", "EAP", "UM", ["malaysia", "kuala lumpur", "penang"], ["Malaysia"]),
 "SGP": ("Singapore", "EAP", "H", ["singapore"], ["Singapore"]),
 "IDN": ("Indonesia", "EAP", "UM", ["indonesia", "jakarta", "sumatra", "kalimantan", "borneo", "java"], ["Indonesia"]),
 "PHL": ("Philippines", "EAP", "LM", ["philippines", "manila"], ["Philippines"]),
 "KHM": ("Cambodia", "EAP", "LM", ["cambodia", "phnom penh"], ["Cambodia"]),
 "LAO": ("Laos", "EAP", "LM", [r"\blaos\b", r"\blao pdr\b"], ["Laos"]),
 "MMR": ("Myanmar", "EAP", "LM", ["myanmar", "yangon"], ["Myanmar"]),
 "AUS": ("Australia", "EAP", "H", ["australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "queensland", "new south wales", "victoria, australia", "tasmania"], ["Australia"]),
 "NZL": ("New Zealand", "EAP", "H", ["new zealand", "auckland", "christchurch", "wellington"], ["New Zealand"]),
 "PNG": ("Papua New Guinea", "EAP", "LM", ["papua new guinea"], ["Papua N Guinea", "Papua New Guinea"]),
 # ---------------- Europe & Central Asia
 "GBR": ("United Kingdom", "ECA", "H", ["united kingdom", r"\buk\b", "britain", "british", "england", "scotland", "wales", "northern ireland", "london", "manchester", "birmingham", "leeds", "glasgow", "edinburgh", "bristol", "sheffield", "liverpool", "oxford"], ["UK", "United Kingdom", "England", "Scotland", "Wales", "North Ireland", "Northern Ireland"]),
 "IRL": ("Ireland", "ECA", "H", [r"(?<!northern )ireland", "dublin"], ["Ireland"]),
 "NLD": ("Netherlands", "ECA", "H", ["netherlands", "dutch", "amsterdam", "rotterdam", "utrecht"], ["Netherlands"]),
 "BEL": ("Belgium", "ECA", "H", ["belgium", "flanders", "brussels", "antwerp"], ["Belgium"]),
 "DEU": ("Germany", "ECA", "H", ["germany", "german", "berlin", "munich", "hamburg", "ruhr", "cologne", "frankfurt", "augsburg", "leipzig", "dresden", "stuttgart"], ["Germany"]),
 "FRA": ("France", "ECA", "H", ["france", "french", "paris", "lyon", "marseille", "grenoble", "strasbourg"], ["France"]),
 "ESP": ("Spain", "ECA", "H", ["spain", "spanish", "madrid", "barcelona", "valencia", "seville", "catalonia", "bilbao"], ["Spain"]),
 "PRT": ("Portugal", "ECA", "H", ["portugal", "lisbon", "porto"], ["Portugal"]),
 "ITA": ("Italy", "ECA", "H", ["italy", "italian", "rome", "milan", "turin", "naples", "po valley", "lombardy", "bologna", "florence", "venice", "taranto"], ["Italy"]),
 "CHE": ("Switzerland", "ECA", "H", ["switzerland", "swiss", "zurich", "geneva", "basel"], ["Switzerland"]),
 "AUT": ("Austria", "ECA", "H", ["austria", "vienna", "graz"], ["Austria"]),
 "DNK": ("Denmark", "ECA", "H", ["denmark", "danish", "copenhagen", "aarhus"], ["Denmark"]),
 "SWE": ("Sweden", "ECA", "H", ["sweden", "swedish", "stockholm", "gothenburg", "malm[oö]", "ume[aå]"], ["Sweden"]),
 "NOR": ("Norway", "ECA", "H", ["norway", "norwegian", "oslo", "bergen"], ["Norway"]),
 "FIN": ("Finland", "ECA", "H", ["finland", "finnish", "helsinki"], ["Finland"]),
 "ISL": ("Iceland", "ECA", "H", ["iceland"], ["Iceland"]),
 "POL": ("Poland", "ECA", "H", ["poland", "polish", "warsaw", "krak[oó]w", "silesia", "wroc"], ["Poland"]),
 "CZE": ("Czechia", "ECA", "H", ["czech", "prague", "ostrava"], ["Czech Republic", "Czechia"]),
 "SVK": ("Slovakia", "ECA", "H", ["slovakia", "bratislava"], ["Slovakia"]),
 "HUN": ("Hungary", "ECA", "H", ["hungary", "budapest"], ["Hungary"]),
 "ROU": ("Romania", "ECA", "H", ["romania", "bucharest"], ["Romania"]),
 "BGR": ("Bulgaria", "ECA", "UM", ["bulgaria", "sofia"], ["Bulgaria"]),
 "GRC": ("Greece", "ECA", "H", ["greece", "greek", "athens", "thessaloniki"], ["Greece"]),
 "SVN": ("Slovenia", "ECA", "H", ["slovenia", "ljubljana"], ["Slovenia"]),
 "HRV": ("Croatia", "ECA", "H", ["croatia", "zagreb"], ["Croatia"]),
 "SRB": ("Serbia", "ECA", "UM", ["serbia", "belgrade"], ["Serbia"]),
 "BIH": ("Bosnia and Herz.", "ECA", "UM", ["bosnia", "sarajevo"], ["Bosnia & Herceg", "Bosnia and Herzegovina"]),
 "MKD": ("North Macedonia", "ECA", "UM", ["macedonia", "skopje"], ["North Macedonia", "Macedonia"]),
 "ALB": ("Albania", "ECA", "UM", ["albania", "tirana"], ["Albania"]),
 "EST": ("Estonia", "ECA", "H", ["estonia", "tallinn"], ["Estonia"]),
 "LVA": ("Latvia", "ECA", "H", ["latvia", "riga"], ["Latvia"]),
 "LTU": ("Lithuania", "ECA", "H", ["lithuania", "vilnius", "kaunas"], ["Lithuania"]),
 "LUX": ("Luxembourg", "ECA", "H", ["luxembourg"], ["Luxembourg"]),
 "MLT": ("Malta", "ECA", "H", [r"\bmalta\b"], ["Malta"]),
 "RUS": ("Russia", "ECA", "UM", ["russia", "moscow", "siberia", "st. petersburg", "saint petersburg"], ["Russia"]),
 "UKR": ("Ukraine", "ECA", "UM", ["ukraine", "kyiv", "kiev"], ["Ukraine"]),
 "BLR": ("Belarus", "ECA", "UM", ["belarus", "minsk"], ["Belarus"]),
 "KAZ": ("Kazakhstan", "ECA", "UM", ["kazakhstan", "almaty", "astana"], ["Kazakhstan"]),
 "UZB": ("Uzbekistan", "ECA", "LM", ["uzbekistan", "tashkent"], ["Uzbekistan"]),
 "KGZ": ("Kyrgyzstan", "ECA", "LM", ["kyrgyz", "bishkek"], ["Kyrgyzstan"]),
 "TJK": ("Tajikistan", "ECA", "LM", ["tajikistan"], ["Tajikistan"]),
 "GEO": ("Georgia", "ECA", "UM", [r"georgia \(country\)", "tbilisi"], ["Georgia"]),
 "ARM": ("Armenia", "ECA", "UM", ["armenia", "yerevan"], ["Armenia"]),
 "AZE": ("Azerbaijan", "ECA", "UM", ["azerbaijan", "baku"], ["Azerbaijan"]),
 # ---------------- North America
 "USA": ("United States", "NAM", "H", ["united states", r"\bu\.s\.", r"\busa\b", r"\bus\b(?= (cities|counties|states|epa|population|census))", "contiguous us", "conterminous", "california", "los angeles", "new york", "texas", "houston", "chicago", "boston", "seattle", "atlanta", "pittsburgh", "denver", "phoenix", "philadelphia", "baltimore", "detroit", "san francisco", "bay area", "san diego", "salt lake", "portland, oregon", "oregon", "washington state", "north carolina", "south carolina", "massachusetts", "michigan", "ohio", "pennsylvania", "colorado", "arizona", "utah", "nevada", "georgia, usa", "florida", "illinois", "minnesota", "wisconsin", "iowa", "kansas", "missouri", "tennessee", "kentucky", "virginia", "maryland", "new jersey", "connecticut", "alaska", "hawaii", "montana", "idaho", "wyoming", "new mexico", "oklahoma", "louisiana", "alabama", "mississippi", "arkansas", "nebraska", "dakota", "indiana", "maine", "vermont", "new hampshire", "rhode island", "delaware", "fresno", "sacramento", "san joaquin", "nhanes", "medicare", "u.s. epa", "us epa"], ["USA", "United States"]),
 "CAN": ("Canada", "NAM", "H", ["canada", "canadian", "toronto", "montreal", "vancouver", "ontario", "quebec", "british columbia", "alberta", "calgary", "edmonton", "winnipeg", "ottawa", "hamilton, ontario", "saskatchewan", "manitoba", "nova scotia", "halifax"], ["Canada"]),
 # ---------------- Latin America & Caribbean
 "MEX": ("Mexico", "LAC", "UM", ["mexico(?! city)", "mexico city", "guadalajara", "monterrey"], ["Mexico"]),
 "BRA": ("Brazil", "LAC", "UM", ["brazil", "s[aã]o paulo", "rio de janeiro", "amazon", "belo horizonte", "porto alegre"], ["Brazil"]),
 "ARG": ("Argentina", "LAC", "UM", ["argentina", "buenos aires", "c[oó]rdoba, argentina"], ["Argentina"]),
 "CHL": ("Chile", "LAC", "H", ["chile", "santiago"], ["Chile"]),
 "COL": ("Colombia", "LAC", "UM", ["colombia", "bogot", "medell[ií]n", "cali,"], ["Colombia"]),
 "PER": ("Peru", "LAC", "UM", [r"\bperu\b", "lima"], ["Peru"]),
 "ECU": ("Ecuador", "LAC", "UM", ["ecuador", "quito"], ["Ecuador"]),
 "BOL": ("Bolivia", "LAC", "LM", ["bolivia", "la paz"], ["Bolivia"]),
 "VEN": ("Venezuela", "LAC", "UM", ["venezuela", "caracas"], ["Venezuela"]),
 "URY": ("Uruguay", "LAC", "H", ["uruguay", "montevideo"], ["Uruguay"]),
 "PRY": ("Paraguay", "LAC", "UM", ["paraguay"], ["Paraguay"]),
 "CUB": ("Cuba", "LAC", "UM", [r"\bcuba\b", "havana"], ["Cuba"]),
 "GTM": ("Guatemala", "LAC", "UM", ["guatemala"], ["Guatemala"]),
 "HND": ("Honduras", "LAC", "LM", ["honduras"], ["Honduras"]),
 "NIC": ("Nicaragua", "LAC", "LM", ["nicaragua"], ["Nicaragua"]),
 "CRI": ("Costa Rica", "LAC", "UM", ["costa rica"], ["Costa Rica"]),
 "PAN": ("Panama", "LAC", "H", ["panama"], ["Panama"]),
 "PRI": ("Puerto Rico", "LAC", "H", ["puerto rico"], ["Puerto Rico"]),
 "HTI": ("Haiti", "LAC", "L", ["haiti"], ["Haiti"]),
 "DOM": ("Dominican Rep.", "LAC", "UM", ["dominican republic"], ["Dominican Rep", "Dominican Republic"]),
 "JAM": ("Jamaica", "LAC", "UM", ["jamaica"], ["Jamaica"]),
 "TTO": ("Trinidad and Tobago", "LAC", "H", ["trinidad"], ["Trinidad Tobago", "Trinidad and Tobago"]),
}

NAME = {k: v[0] for k, v in C.items()}
REGION = {k: v[1] for k, v in C.items()}
INCOME = {k: v[2] for k, v in C.items()}
REGION_NAME = {"SSA": "Sub-Saharan Africa", "MENA": "Middle East & North Africa", "SAS": "South Asia",
               "EAP": "East Asia & Pacific", "ECA": "Europe & Central Asia", "LAC": "Latin America & Caribbean",
               "NAM": "North America"}

_TEXT = [(iso, re.compile(r"(?<![a-z])(" + "|".join(p for p in v[3]) + r")(?![a-z])", re.I)) for iso, v in C.items()]

# multi-country / continental regions, used only when no country is named
MACRO = [
    ("SSA", re.compile(r"sub-?saharan|east africa|west africa|southern africa|central africa|sahel", re.I)),
    ("AFR", re.compile(r"\bafrica(n)?\b", re.I)),
    ("EUR", re.compile(r"\beurope(an)?\b|\beu\b|\bescape\b", re.I)),
    ("ASIA", re.compile(r"\basia(n)?\b", re.I)),
    ("LAC", re.compile(r"latin america|south america", re.I)),
    ("GLOBAL", re.compile(r"\bglobal(ly)?\b|worldwide|world-wide|\bacross the world\b|multi-?country|\b\d{2,3} countries", re.I)),
]


def study_countries(text: str):
    t = text.replace("’", "'")
    t = re.sub(r"(?i)(united states|u\.s\.|us) environmental protection agency|\bepa\b|national aeronautics|american (thoracic|cancer|heart|journal|chemical|geophysical)", " ", t)
    return sorted({iso for iso, rx in _TEXT if rx.search(t)})


def macro_regions(text: str):
    return [k for k, rx in MACRO if rx.search(text)]


# affiliation strings end with the country
_AFF = {}
for iso, v in C.items():
    for a in v[4]:
        _AFF[a.lower()] = iso
_US_TAIL = re.compile(r"\b[A-Z]{2}\s*\d{5}(-\d{4})?\s+USA$|\bUSA$|United States( of America)?$")


def aff_country(aff: str):
    s = aff.strip().rstrip(".").strip()
    if not s:
        return None
    if _US_TAIL.search(s):
        return "USA"
    last = s.split(",")[-1].strip()
    last = re.sub(r"^[A-Z0-9\- ]*\d[A-Z0-9\- ]*\s+", "", last)  # postcodes in front of the country
    lk = last.lower()
    if lk in _AFF:
        return _AFF[lk]
    for k, iso in _AFF.items():
        if lk.endswith(" " + k) or lk == k:
            return iso
    return None

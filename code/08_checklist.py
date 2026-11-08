"""Step 8 -- human verification checklist, and reading it back.

    python scripts/08_checklist.py make    -> review/HUMAN_CHECKLIST.xlsx
    python scripts/08_checklist.py apply   -> data/human_overrides.json (read by 02_screen_code.py)

Sheet 1 'Included (check)': every included study, the likeliest false positives first.
Sheet 2 'Excluded (maybe)': excluded studies most likely to be relevant (missed inclusions).
Sheet 3 'Audit 120': the blinded audit, for a human verdict alongside the AI-drafted one.
Fill the 'Verdict' column (KEEP / DROP / INCLUDE / EXCLUDE). Blank means 'agree with the rules'.
"""
from __future__ import annotations
import sys, re, json, pickle
from pathlib import Path
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

V2 = Path(__file__).resolve().parents[1]
XL = V2 / "review/HUMAN_CHECKLIST.xlsx"

CORE = re.compile(r"(?i)exposure|proxy|proxies|surrogate|land[- ]use|\blur\b|regression|model|map|predict|estimat|satellite|"
                  r"traffic|road|spatial|gis\b|geograph|remote sens|aod|aerosol optical|ndvi|kriging|interpolat|machine learning|random forest")
OFFCORE = re.compile(r"(?i)emission|inventor|policy|econom|governance|mortality|hospital|admission|association|cohort|risk of|incidence|"
                     r"source apportionment|composition|chemistry|forecast")
AIRT = re.compile(r"(?i)air pollut|air quality|pm ?2\.?5|pm ?10|no2|nitrogen dioxide|ozone|black carbon|particulate|traffic[- ]related")
EXPT = re.compile(r"(?i)exposure|land[- ]use regression|\blur\b|proxy|surrogate|satellite|aod|spatial|predict|estimat|model")


def risk(r):
    s = 0
    if not CORE.search(r.title): s += 2
    if OFFCORE.search(r.title) and not EXPT.search(r.title): s += 2
    if len(r.families) <= 1: s += 1
    if not r.val_subcorpus: s += 1
    return s


def why_in(r):
    bits = []
    if r.families: bits.append("families: " + ", ".join(r.families))
    if r.proxies: bits.append("proxies: " + ", ".join(r.proxies[:4]))
    return "; ".join(bits)


def make():
    df = pickle.load(open(V2 / "data/records_coded.pkl", "rb"))
    inc = df[df.included].copy()
    inc["risk"] = inc.apply(risk, axis=1)
    inc = inc.sort_values(["risk", "year"], ascending=[False, True])
    exc = df[~df.included].copy()
    exc["chance"] = (exc.title.str.contains(AIRT).astype(int) * 2 + exc.title.str.contains(EXPT).astype(int) * 2
                     + exc.decision.isin(["R3", "R6", "R5"]).astype(int))
    exc = exc[exc.chance >= 3].sort_values(["chance", "year"], ascending=[False, True])
    aud = pd.read_excel(V2 / "review/audit_final_120.xlsx")
    abst = df.set_index("rid").abstract

    wb = Workbook()
    head_font, head_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1C1C1C")
    wrap = Alignment(wrap_text=True, vertical="top")

    def sheet(ws, cols, rows, widths, options, verdict_col, note):
        ws.append([note]); ws["A1"].font = Font(italic=True, color="555555")
        ws.append(cols)
        for c in ws[2]:
            c.font, c.fill, c.alignment = head_font, head_fill, Alignment(wrap_text=True, vertical="center")
        for r in rows:
            ws.append(r)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[ws.cell(2, i).column_letter].width = w
        for row in ws.iter_rows(min_row=3):
            for c in row:
                c.alignment = wrap
        ws.freeze_panes = "C3"
        ws.auto_filter.ref = f"A2:{ws.cell(2, len(cols)).column_letter}{ws.max_row}"
        L = ws.cell(2, verdict_col).column_letter
        dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
        ws.add_data_validation(dv); dv.add(f"{L}3:{L}{ws.max_row}")
        for v, col in (("DROP", "F7B7BB"), ("EXCLUDE", "F7B7BB"), ("KEEP", "DCE6F2"), ("INCLUDE", "DCE6F2")):
            ws.conditional_formatting.add(f"A3:{ws.cell(2, len(cols)).column_letter}{ws.max_row}",
                                          FormulaRule(formula=[f'${L}3="{v}"'], fill=PatternFill("solid", fgColor=col)))

    ws = wb.active; ws.title = "Included (check)"
    rows = [[r.rid, "", "", r.risk, r.title, r.year, r.source, why_in(r), "yes" if r.val_subcorpus else "", (r.abstract or "")[:400]] for r in inc.itertuples()]
    sheet(ws, ["ID", "Verdict", "Note", "Risk", "Title", "Year", "Source", "Why the rules included it", "Validation", "Abstract (first 400 characters)"],
          rows, [8, 10, 22, 6, 60, 6, 26, 36, 9, 70], "KEEP,DROP", 2,
          f"{len(inc)} included studies, likeliest false positives first (Risk 0–6). Mark DROP if the study does not use, compare, validate or review "
          "geospatial or environmental proxies to assess air pollution or estimate exposure. Blank = keep.")
    ws2 = wb.create_sheet("Excluded (maybe)")
    rows = [[r.rid, "", "", r.decision, r.reason, r.title, r.year, r.source, (r.abstract or "")[:400]] for r in exc.itertuples()]
    sheet(ws2, ["ID", "Verdict", "Note", "Rule", "Rule reason", "Title", "Year", "Source", "Abstract (first 400 characters)"],
          rows, [8, 10, 22, 6, 24, 60, 6, 26, 70], "INCLUDE,EXCLUDE", 2,
          f"{len(exc)} excluded studies whose titles look most relevant (possible missed inclusions). Mark INCLUDE if it should be in the corpus. Blank = stays excluded.")
    ws3 = wb.create_sheet("Audit 120")
    rows = [[r.rid, "", "", "relevant" if r.truth else "not relevant", "included" if r.rule else "excluded", r.decision, r.title, (abst.get(r.rid) or "")[:400]] for r in aud.itertuples()]
    sheet(ws3, ["ID", "Human verdict", "Note", "AI-drafted verdict", "Rules", "Rule code", "Title", "Abstract (first 400 characters)"],
          rows, [8, 13, 22, 14, 10, 8, 60, 70], "relevant,not relevant", 2,
          "Blinded audit used to estimate precision and recall. Enter your own verdict in column B; the audit metrics are recomputed from yours when it is filled.")
    ws4 = wb.create_sheet("How to use")
    for line in ["1. 'Included (check)': skim titles from the top (riskiest first). Mark DROP for off-topic studies; leave blank to keep.",
                 "2. 'Excluded (maybe)': mark INCLUDE for any study that belongs in the corpus.",
                 "3. 'Audit 120': give your own verdict for every row (this replaces the AI-drafted one in the manuscript).",
                 "4. Save the file, then run:  python scripts/08_checklist.py apply  &&  ./run_all.sh",
                 "   Your verdicts override the rules; every number, table, figure, the manuscript and Chapter 2 are rebuilt.",
                 "Inclusion test: does the study use, compare, validate or review indirect geospatial/environmental variables",
                 "to assess air pollution or estimate exposure? Exclude emission inventories, monitor-only epidemiology, chemistry,",
                 "indoor-only, and 'proxy' in unrelated senses (palaeo, emulators, biomarkers)."]:
        ws4.append([line])
    ws4.column_dimensions["A"].width = 120
    wb.move_sheet("How to use", offset=-3)
    wb.save(XL)
    print(f"wrote {XL}: {len(inc)} included, {len(exc)} excluded-maybe, {len(aud)} audit")


def apply():
    wb = load_workbook(XL, data_only=True)
    ov = {}
    for name, col_v, force in (("Included (check)", 2, {"DROP": "EXCLUDE"}), ("Excluded (maybe)", 2, {"INCLUDE": "INCLUDE"})):
        for row in wb[name].iter_rows(min_row=3, values_only=True):
            rid, v = row[0], (row[col_v - 1] or "").strip().upper()
            if rid and v in force:
                ov[rid] = force[v]
    aud = {}
    for row in wb["Audit 120"].iter_rows(min_row=3, values_only=True):
        if row[0] and row[1]:
            aud[row[0]] = row[1].strip().lower() == "relevant"
    (V2 / "data/human_overrides.json").write_text(json.dumps(dict(screening=ov, audit=aud), indent=1))
    print(f"overrides: {sum(v == 'EXCLUDE' for v in ov.values())} dropped, {sum(v == 'INCLUDE' for v in ov.values())} added; "
          f"audit verdicts: {len(aud)} of 120")


if __name__ == "__main__":
    {"make": make, "apply": apply}[sys.argv[1] if len(sys.argv) > 1 else "make"]()

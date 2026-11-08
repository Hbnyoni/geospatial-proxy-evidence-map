"""Agreement between the rule-based screening (v2) and the April 2026 screening (v1)."""
import pickle, re, json, sys
from pathlib import Path
import pandas as pd
from sklearn.metrics import cohen_kappa_score
V2 = Path(__file__).resolve().parents[1]; RAW = V2.parent
sys.path.insert(0, str(Path(__file__).parent))
nt = lambda t: re.sub(r"[^a-z0-9]+", "", str(t).lower())
df = pickle.load(open(V2 / "data/records_coded.pkl", "rb"))
old = pd.concat([pd.read_excel(RAW / "screening_MERGED_main_corpus_SCREENED.xlsx"),
                 pd.read_excel(RAW / "screening_MERGED_sensitivity_SCREENED.xlsx")])
old["k"] = old["doi"].fillna("").str.lower().str.strip()
old["t"] = old["title"].map(nt)
bydoi = dict(zip(old.k, old.include_title_abs)); bytit = dict(zip(old.t, old.include_title_abs))
df["v1"] = [bydoi.get(d) if d and d in bydoi else bytit.get(nt(t)) for d, t in zip(df.doi, df.title)]
m = df[df.v1.notna()].copy()
m["v1i"] = m.v1.eq("Y"); m["v2i"] = m.included
res = dict(matched=len(m), unmatched=int(df.v1.isna().sum()),
           agreement=round((m.v1i == m.v2i).mean(), 3), kappa=round(cohen_kappa_score(m.v1i, m.v2i), 3),
           both_in=int((m.v1i & m.v2i).sum()), both_out=int((~m.v1i & ~m.v2i).sum()),
           v1_only=int((m.v1i & ~m.v2i).sum()), v2_only=int((~m.v1i & m.v2i).sum()))
print(json.dumps(res, indent=1))
(V2 / "data/agreement_v1_v2.json").write_text(json.dumps(res, indent=1))
d = m[m.v1i != m.v2i][["rid", "v1", "decision", "reason", "title", "abstract", "families"]]
d.to_csv(V2 / "review/disagreements_v1_v2.csv", index=False)


# ---------------------------------------------------------------- audit metrics (human verdicts take precedence)
import numpy as np
a = pd.read_pickle(V2 / "data/audit_final.pkl")
Y = {2,3,6,7,9,13,17,22,26,27,28,32,33,37,39,40,42,45,48,49,57,60,62,63,65,66,68,69,72,73,75,79,83,84,86,89,91,97,100,102,104,105,106,111,114,116,118,120}
a["truth"] = [(i + 1) in Y for i in range(len(a))]          # AI-drafted verdicts (see review/audit_final_120.xlsx)
hf = V2 / "data/human_overrides.json"
hum = json.loads(hf.read_text()).get("audit", {}) if hf.exists() else {}
a["truth"] = [hum.get(r, t) for r, t in zip(a.rid, a.truth)]
d = df.set_index("rid")
rule = a.rid.map(d.included)
tp = int((a.truth & rule).sum()); fp = int((~a.truth & rule).sum()); fn = int((a.truth & ~rule).sum()); tn = int((~a.truth & ~rule).sum())
def wilson(k, n, z=1.96):
    p = k / n; dd = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return [round((c - h) / dd, 3), round((c + h) / dd, 3)]
ninc = int(d.included.sum()); nexc = len(d) - ninc
prec, npv = tp / (tp + fp), tn / (tn + fn)
audit = dict(n=len(a), tp=tp, fp=fp, fn=fn, tn=tn, precision=round(prec, 3), precision_ci=wilson(tp, tp + fp), npv=round(npv, 3), npv_ci=wilson(tn, tn + fn),
             est_recall=round(prec * ninc / (prec * ninc + (1 - npv) * nexc), 3), human_verdicts=len(hum),
             note="Blinded audit of 120 records drawn after rule tuning on 200 others; human verdicts replace the AI-drafted ones where given.")
(V2 / "data/audit_final_result.json").write_text(json.dumps(audit, indent=1))
print("audit:", {k: audit[k] for k in ("precision", "npv", "est_recall", "human_verdicts")})

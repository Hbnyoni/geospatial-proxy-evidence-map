"""Step 1 -- read the four database exports, filter document types, de-duplicate.

Inputs (raw exports, 1 April 2026, in the parent folder)
    scopus_export_Mian_CSV_01042026.csv    Scopus primary search   (with cited references)
    scopus_export_Sens_CSV_01042026.csv    Scopus sensitivity search
    WoS_Main_plaintext.txt                 WoS Core Collection primary search (tagged, with CR)
    WoS_Sens_plaintext.txt                 WoS Core Collection sensitivity search

De-duplication follows the agreed protocol: DOI first, then exact normalised title, then a fuzzy
title pass (token-set ratio >= 95, publication years within one) whose candidate pairs are written
out for manual review. A pair is merged automatically only when the first-author surname also
matches; every other near-pair stays separate and is listed in review/near_duplicates.csv.

Outputs  data/records_all.pkl  (one row per unique record, with source flags)
         tables/T_identification.csv, review/near_duplicates.csv
"""
from __future__ import annotations
import re, unicodedata, pickle, json
from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz

V2 = Path(__file__).resolve().parents[1]
RAW = V2.parent
DATA, TAB, REV = V2 / "data", V2 / "tables", V2 / "review"


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def norm_title(t: str) -> str:
    t = ascii_fold(str(t)).lower()
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def norm_doi(d) -> str:
    if not isinstance(d, str) or not d.strip():
        return ""
    d = d.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    return d.rstrip(".")


def surname_key(author: str) -> str:
    """'de Hoogh K.' / 'de Hoogh K' / 'Hoek, G' -> 'dehoogh'. Drops initials."""
    a = ascii_fold(author).replace(",", " ").strip()
    toks = [t for t in re.split(r"\s+", a) if t]
    keep = [t for t in toks if not re.fullmatch(r"([A-Z]\.?-?)+|[A-Z]{1,3}", t)]
    if not keep:
        keep = toks[:1]
    return re.sub(r"[^a-z]", "", " ".join(keep).lower())


def _display_surname(author: str) -> str:
    toks = [t for t in ascii_fold(author).replace(",", " ").split() if not re.fullmatch(r"([A-Z]\.?-?)+|[A-Z]{1,3}", t)]
    out = " ".join(toks) if toks else author.split()[0]
    return out if out.isupper() is False else out.title()


# ---------------------------------------------------------------- cited references
def ref_key_wos(cr: str):
    """'Hoek G, 2008, ATMOS ENVIRON, V42, P7561, DOI 10.1016/...' -> key, label."""
    parts = [p.strip() for p in cr.split(",")]
    if len(parts) < 3 or not re.fullmatch(r"\d{4}", parts[1] or ""):
        return None
    sur, yr = surname_key(parts[0]), parts[1]
    page = next((p[1:] for p in parts if re.fullmatch(r"P\d+", p)), "")
    vol = next((p[1:] for p in parts if re.fullmatch(r"V\d+", p)), "")
    if not sur or not (page or vol):
        return None
    key = f"{sur}|{yr}|{'p' + page if page else 'v' + vol}"
    return key, dict(first=parts[0].split()[0].title(), first_full=_display_surname(parts[0]), year=yr, source=parts[2].title(), title="")


def ref_key_scopus(ref: str):
    """'Bey I.; Jacob D.; ..., Title, J. Geophys. Res., 106, D19, pp. 23073-23095, (2001)'."""
    m = re.search(r"\((\d{4})\)\s*$", ref)
    if not m:
        return None
    yr = m.group(1)
    head = ref.split(",")[0]
    first = head.split(";")[0].strip()
    # a reference that opens with its title has no author block
    if not re.search(r"\b[A-Z]\.", first) or len(first) > 45:
        return None
    sur = surname_key(first)
    pg = re.search(r"pp?\.\s*([A-Za-z]?\d+)", ref)
    body = ref[len(head):]
    nums = re.findall(r",\s*(\d+),", body)
    if pg:
        tail = "p" + re.sub(r"\D", "", pg.group(1))
    elif nums:
        tail = "v" + nums[0]
    else:
        return None
    after = ref[ref.rfind(";", 0, ref.find(",")) + 1:] if ";" in head else ref
    segs = [s.strip() for s in after.split(",")]
    title = segs[1] if len(segs) > 2 else ""
    src = segs[2] if len(segs) > 3 else ""
    return f"{sur}|{yr}|{tail}", dict(first=first.split()[0].title(), first_full=_display_surname(first), year=yr, source=src, title=title)


REF_LABELS: dict[str, dict] = {}


def keys_from(refs, fn):
    out = []
    for r in refs:
        k = fn(r)
        if k:
            out.append(k[0])
            lab = REF_LABELS.setdefault(k[0], k[1])
            if not lab.get("title") and k[1].get("title"):
                lab["title"], lab["source"] = k[1]["title"], k[1]["source"]
    return sorted(set(out))


# ---------------------------------------------------------------- readers
def read_scopus(path: Path, search: str) -> pd.DataFrame:
    d = pd.read_csv(path)
    rows = []
    for _, r in d.iterrows():
        refs = re.split(r"(?<=\(\d{4}\));\s+", r["References"]) if isinstance(r["References"], str) else []
        affs = [a.strip() for a in str(r["Affiliations"]).split(";")] if isinstance(r["Affiliations"], str) else []
        rows.append(dict(
            db="Scopus", search=search, uid=r["EID"], title=str(r["Title"]).strip(),
            authors=[a.strip() for a in str(r["Authors"]).split(";") if a.strip() and a.strip() != "[No author name available]"],
            year=int(r["Year"]), source=str(r["Source title"]).strip(), doi=norm_doi(r["DOI"]),
            abstract="" if str(r["Abstract"]).startswith("[No abstract") else str(r["Abstract"]),
            kw_author=[k.strip().lower() for k in str(r["Author Keywords"]).split(";")] if isinstance(r["Author Keywords"], str) else [],
            kw_index=[k.strip().lower() for k in str(r["Index Keywords"]).split(";")] if isinstance(r["Index Keywords"], str) else [],
            doc_type=str(r["Document Type"]), language=str(r["Language of Original Document"]),
            tc=int(r["Cited by"]) if pd.notna(r["Cited by"]) else 0,
            affiliations=affs, corresp=str(r["Correspondence Address"]) if pd.notna(r["Correspondence Address"]) else "",
            n_refs=len(refs), ref_keys=keys_from(refs, ref_key_scopus)))
    return pd.DataFrame(rows)


def parse_tagged(path: Path):
    recs, cur, tag = [], {}, None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("ER"):
            recs.append(cur); cur, tag = {}, None; continue
        if line[:2].strip() and len(line) > 2 and line[2] == " ":
            tag = line[:2]; cur.setdefault(tag, []).append(line[3:])
        elif line.startswith("   ") and tag:
            cur[tag].append(line[3:])
    return recs


WOS_DT = {"Article": "Article", "Review": "Review"}


def read_wos(path: Path, search: str) -> pd.DataFrame:
    rows = []
    for r in parse_tagged(path):
        j = lambda t, sep=" ": sep.join(r.get(t, [])).strip()
        dt = j("DT")
        c1 = j("C1", " ")
        affs = [a.strip() for a in re.split(r";\s*(?=\[)|(?<=[A-Za-z])\s*;\s+", c1) if a.strip()]
        affs = [re.sub(r"^\[[^\]]*\]\s*", "", a) for a in affs]
        rows.append(dict(
            db="WoS", search=search, uid=j("UT"), title=j("TI"),
            authors=[a.strip() for a in r.get("AU", [])],
            year=int(j("PY") or 0), source=j("SO").title(), doi=norm_doi(j("DI")),
            abstract=j("AB"),
            kw_author=[k.strip().lower() for k in j("DE").split(";") if k.strip()],
            kw_index=[k.strip().lower() for k in j("ID").split(";") if k.strip()],
            doc_type=dt, language=j("LA"), tc=int(j("TC") or 0),
            affiliations=affs, corresp=j("RP"),
            n_refs=len(r.get("CR", [])), ref_keys=keys_from(r.get("CR", []), ref_key_wos)))
    return pd.DataFrame(rows)


def keep_type(dt: str) -> str | None:
    d = dt.lower()
    if d.startswith("review"):
        return "Review"
    if d.startswith("article"):
        return "Article"
    return None


# ---------------------------------------------------------------- de-duplication
def dedupe(df: pd.DataFrame, label: str):
    """Union-find over DOI, exact title, and (reviewed) fuzzy title."""
    df = df.reset_index(drop=True).copy()
    df["ntitle"] = df["title"].map(norm_title)
    df["fa"] = df["authors"].map(lambda a: surname_key(a[0]) if a else "")
    parent = list(range(len(df)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    stage = {"doi": 0, "title": 0, "fuzzy_auto": 0}
    for key, st in (("doi", "doi"), ("ntitle", "title")):
        for _, idx in df[df[key] != ""].groupby(key).groups.items():
            idx = list(idx)
            for k in idx[1:]:
                if find(k) != find(idx[0]):
                    stage[st] += 1
                union(idx[0], k)
    # fuzzy pass on group representatives
    reps = sorted({find(i) for i in range(len(df))})
    near = []
    by_year = {}
    for i in reps:
        by_year.setdefault(df.at[i, "year"], []).append(i)
    for i in reps:
        ti = df.at[i, "title"].lower()
        if len(ti) < 25:
            continue
        for y in (df.at[i, "year"] - 1, df.at[i, "year"], df.at[i, "year"] + 1):
            for j in by_year.get(y, []):
                if j <= i or find(i) == find(j):
                    continue
                s = fuzz.token_set_ratio(ti, df.at[j, "title"].lower())
                if s >= 95:
                    same_fa = df.at[i, "fa"] == df.at[j, "fa"] and df.at[i, "fa"] != ""
                    near.append(dict(corpus=label, score=round(s, 1), merged=same_fa,
                                     title_a=df.at[i, "title"], year_a=df.at[i, "year"], first_a=df.at[i, "fa"], db_a=df.at[i, "db"],
                                     title_b=df.at[j, "title"], year_b=df.at[j, "year"], first_b=df.at[j, "fa"], db_b=df.at[j, "db"]))
                    if same_fa:
                        union(i, j); stage["fuzzy_auto"] += 1
    df["grp"] = [find(i) for i in range(len(df))]
    out = []
    for g, sub in df.groupby("grp"):
        sub = sub.sort_values("db", key=lambda s: s.map({"Scopus": 0, "WoS": 1}))
        rec = sub.iloc[0].to_dict()
        for c in ("abstract", "doi", "corresp"):
            if not rec[c]:
                rec[c] = next((v for v in sub[c] if v), "")
        for c in ("kw_author", "kw_index", "affiliations"):
            if not rec[c]:
                rec[c] = next((v for v in sub[c] if len(v)), [])
        rec["tc"] = int(sub["tc"].max())
        best = sub.loc[sub["n_refs"].idxmax()]
        rec["ref_keys"], rec["n_refs"] = best["ref_keys"], int(best["n_refs"])
        rec["in_scopus"] = bool((sub["db"] == "Scopus").any())
        rec["in_wos"] = bool((sub["db"] == "WoS").any())
        rec["n_merged"] = len(sub)
        out.append(rec)
    res = pd.DataFrame(out).drop(columns=["grp"])
    return res, stage, near


def main():
    sm = read_scopus(RAW / "scopus_export_Mian_CSV_01042026.csv", "primary")
    ss = read_scopus(RAW / "scopus_export_Sens_CSV_01042026.csv", "sensitivity")
    wm = read_wos(RAW / "WoS_Main_plaintext.txt", "primary")
    ws = read_wos(RAW / "WoS_Sens_plaintext.txt", "sensitivity")
    ident = []
    for nm, d in (("Scopus primary", sm), ("WoS primary", wm), ("Scopus sensitivity", ss), ("WoS sensitivity", ws)):
        d["doc_type_std"] = d["doc_type"].map(keep_type)
        ident.append(dict(stage="identified", set=nm, n=len(d),
                          excluded_doctype=int(d["doc_type_std"].isna().sum()),
                          kept=int(d["doc_type_std"].notna().sum()),
                          excluded_types=json.dumps(d.loc[d.doc_type_std.isna(), "doc_type"].value_counts().to_dict())))
    prim = pd.concat([sm, wm]).query("doc_type_std.notna()")
    sens = pd.concat([ss, ws]).query("doc_type_std.notna()")
    P, stP, nearP = dedupe(prim, "primary")
    # sensitivity: dedupe within, then remove anything already in the primary corpus
    S, stS, nearS = dedupe(sens, "sensitivity")
    # overlap with the primary corpus: DOI, exact title, or fuzzy title (>= 95, year +-1, same first author)
    pdoi = set(P["doi"][P["doi"] != ""]); ptit = set(P["title"].map(norm_title))
    p_by_year = {}
    for t, y, fa in zip(P["title"], P["year"], P["authors"].map(lambda a: surname_key(a[0]) if a else "")):
        p_by_year.setdefault(y, []).append((t.lower(), fa))
    nearB = []

    def overlaps(r):
        if (r["doi"] and r["doi"] in pdoi) or norm_title(r["title"]) in ptit:
            return True
        fa = surname_key(r["authors"][0]) if r["authors"] else ""
        for y in (r["year"] - 1, r["year"], r["year"] + 1):
            for t, pfa in p_by_year.get(y, []):
                sc = fuzz.token_set_ratio(r["title"].lower(), t)
                if sc >= 95:
                    nearB.append(dict(corpus="sensitivity-vs-primary", score=round(sc, 1), merged=fa == pfa and fa != "",
                                      title_a=r["title"], year_a=r["year"], first_a=fa, db_a=r["db"],
                                      title_b=t, year_b=y, first_b=pfa, db_b="primary"))
                    if fa == pfa and fa:
                        return True
        return False

    S["in_primary"] = S.apply(overlaps, axis=1).astype(bool)
    S_unique = S[~S["in_primary"]].drop(columns=["in_primary"]).copy()
    P["corpus"], S_unique["corpus"] = "primary", "sensitivity"
    allrec = pd.concat([P, S_unique], ignore_index=True)
    allrec["rid"] = [f"R{i:04d}" for i in range(1, len(allrec) + 1)]
    allrec = allrec.drop(columns=[c for c in ("ntitle", "fa", "_from") if c in allrec])

    flow = dict(
        scopus_primary=len(sm), wos_primary=len(wm), scopus_sens=len(ss), wos_sens=len(ws),
        primary_identified=len(sm) + len(wm),
        primary_doctype_excluded=int(len(sm) + len(wm) - len(prim)),
        primary_after_doctype=len(prim), primary_dup_doi=stP["doi"], primary_dup_title=stP["title"],
        primary_dup_fuzzy=stP["fuzzy_auto"], primary_unique=len(P),
        primary_both_db=int((P.in_scopus & P.in_wos).sum()),
        primary_scopus_only=int((P.in_scopus & ~P.in_wos).sum()),
        primary_wos_only=int((~P.in_scopus & P.in_wos).sum()),
        sens_identified=len(ss) + len(ws), sens_doctype_excluded=int(len(ss) + len(ws) - len(sens)),
        sens_after_doctype=len(sens), sens_dup_within=stS["doi"] + stS["title"] + stS["fuzzy_auto"],
        sens_unique_within=len(S), sens_overlap_primary=int(len(S) - len(S_unique)),
        sens_unique=len(S_unique), near_pairs_for_review=len(nearP) + len(nearS) + len(nearB),
    )
    pd.DataFrame(ident).to_csv(TAB / "T_identification.csv", index=False)
    pd.DataFrame(nearP + nearS + nearB).drop_duplicates(subset=["title_a", "title_b"]).to_csv(REV / "near_duplicates.csv", index=False)
    (DATA / "flow_identification.json").write_text(json.dumps(flow, indent=2))
    with open(DATA / "records_all.pkl", "wb") as f:
        pickle.dump(allrec, f)
    with open(DATA / "ref_labels.pkl", "wb") as f:
        pickle.dump(REF_LABELS, f)
    print(json.dumps(flow, indent=2))
    print("ref keys per record (median):", allrec["ref_keys"].map(len).median(),
          " records with refs:", (allrec["ref_keys"].map(len) > 0).sum())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Add threaded comment replies (author Handsome Nyoni) to the tracked manuscript."""
import re, shutil, sys, zipfile, os

SRC = sys.argv[1]
DST = sys.argv[2]
AUTHOR, INITIALS, DATE = "Handsome Nyoni", "HN", "2026-11-03T00:00:00Z"

# parent comment id -> (paraId of the comment's LAST paragraph, reply id, reply paraId, text)
REPLIES = [
    ("1", "0876DE39", "101", "5A1D0001",
     "Accepted, all three parts. A paragraph stating the aim and four objectives has been "
     "inserted in Section 1 immediately before the question list, and the five questions are "
     "now presented as the operationalisation of those objectives. The supplementary material "
     "exists and is complete; it was simply not attached to the review copy, and both files "
     "(Supplementary_Tables.xlsx, Supplementary_Figures.docx) are attached this time. Table 3 "
     "has been rebuilt and your six paragraph-format changes are accepted."),
    ("2", "00B3AC6C", "102", "5A1D0002",
     "Accepted, and the concern is stronger than “partly”: the number of validated studies "
     "using a proxy correlates with the number of studies using it at ρ = 0.97, so the validation "
     "axis could not vary independently of a frequency-based prominence axis. Section 2.8 has been "
     "rewritten. The validation axis is now a rate, k/n, with the denominator shown and a 95% Wilson "
     "interval on every value; transfer-testing designs are reported separately as counts because "
     "they are too rare for a stable rate; and the single priority score is replaced by the "
     "two-dimensional evidence map."),
    ("35", "4DE55FA4", "103", "5A1D0003",
     "Accepted. Section 3.5 now separates the three quantities and says what each can support: "
     "counts (ρ = 0.93) are labelled constructional and carry no claim; rates (ρ = −0.06, "
     "p = 0.71) support only the weaker statement that validation effort has tracked use rather than "
     "need; design type (ρ = 0.48, p = 0.003) is the one place the original reading survives, and it "
     "does so from a base of 2.6% of studies. “Validation has followed attention” is removed from "
     "the abstract and conclusions in its unqualified form, and “defensible starting catalogue” is "
     "withdrawn: the 2,000-sample bootstrap leaves only six proxies holding a top-eight place in at "
     "least 93% of resamples."),
    ("36", "27DC73F2", "104", "5A1D0004",
     "Accepted; the conflict is real and is exactly three rows, where Table 3 applied a variable-level "
     "rule that labelled traffic volume or intensity, vegetation index and land surface temperature "
     "dynamic although their families are static. Section 2.5 now states both rules, names those three "
     "exceptions with their justification, and says which rule is used where: the family rule for every "
     "study-level statistic, the variable rule for Table 3 and Figure 10 where the unit is the proxy "
     "rather than the study. Both labels are carried in Supplementary Table S3."),
]

CT_PART = "/word/commentsExtended.xml"
CT_TYPE = ("application/vnd.openxmlformats-officedocument"
           ".wordprocessingml.commentsExtended+xml")
REL_TYPE = ("http://schemas.microsoft.com/office/2011/relationships/commentsExtended")

zin = zipfile.ZipFile(SRC)
parts = {n: zin.read(n) for n in zin.namelist()}
infos = {i.filename: i for i in zin.infolist()}
order = zin.namelist()
zin.close()

# ---------------------------------------------------------------- comments.xml
c = parts["word/comments.xml"].decode("utf8")
assert c.rstrip().endswith("</w:comments>")
new = []
for pid, ppara, rid, rpara, text in REPLIES:
    assert f'w14:paraId="{ppara}"' in c, f"parent paraId {ppara} not found"
    body = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    new.append(
        f'<w:comment w:id="{rid}" w:author="{AUTHOR}" w:date="{DATE}" w:initials="{INITIALS}">'
        f'<w:p w14:paraId="{rpara}" w14:textId="77777777">'
        f'<w:pPr><w:pStyle w:val="CommentText"/></w:pPr>'
        f'<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:annotationRef/></w:r>'
        f'<w:r><w:t xml:space="preserve">{body}</w:t></w:r>'
        f'</w:p></w:comment>')
c = c.replace("</w:comments>", "".join(new) + "</w:comments>")
parts["word/comments.xml"] = c.encode("utf8")

# ------------------------------------------------------------- document.xml
d = parts["word/document.xml"].decode("utf8")
for pid, ppara, rid, rpara, text in REPLIES:
    start = f'<w:commentRangeStart w:id="{pid}" />'
    end = f'<w:commentRangeEnd w:id="{pid}" />'
    assert d.count(start) == 1 and d.count(end) == 1, f"anchor for {pid} not unique"
    # reply range nests immediately inside the parent range
    d = d.replace(start, start + f'<w:commentRangeStart w:id="{rid}" />', 1)
    d = d.replace(end, f'<w:commentRangeEnd w:id="{rid}" />' + end, 1)
    # the reply's reference run follows the parent's reference run
    m = re.search(r'<w:r\b[^>]*>(?:(?!</w:r>).)*?<w:commentReference w:id="%s" />.*?</w:r>' % pid,
                  d, re.S)
    assert m, f"commentReference run for {pid} not found"
    ref_run = ('<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
               f'<w:commentReference w:id="{rid}" /></w:r>')
    d = d[:m.end()] + ref_run + d[m.end():]
parts["word/document.xml"] = d.encode("utf8")

# -------------------------------------------------------- commentsExtended.xml
ex = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
      '<w15:commentsEx '
      'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
      'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
      'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
      'mc:Ignorable="w14 w15">']
seen = set()
for pid, ppara, rid, rpara, text in REPLIES:
    if ppara not in seen:
        ex.append(f'<w15:commentEx w15:paraId="{ppara}" w15:done="0"/>')
        seen.add(ppara)
    ex.append(f'<w15:commentEx w15:paraId="{rpara}" '
              f'w15:paraIdParent="{ppara}" w15:done="0"/>')
ex.append('</w15:commentsEx>')
parts["word/commentsExtended.xml"] = "".join(ex).encode("utf8")

# ------------------------------------------------------------- content types
ct = parts["[Content_Types].xml"].decode("utf8")
if CT_PART not in ct:
    ct = ct.replace("</Types>",
                    f'<Override PartName="{CT_PART}" ContentType="{CT_TYPE}"/></Types>')
    parts["[Content_Types].xml"] = ct.encode("utf8")

# ------------------------------------------------------------- relationships
rels = parts["word/_rels/document.xml.rels"].decode("utf8")
if "commentsExtended.xml" not in rels:
    used = {int(x) for x in re.findall(r'Id="rId(\d+)"', rels)}
    rid_new = f"rId{max(used) + 1}"
    rels = rels.replace("</Relationships>",
                        f'<Relationship Id="{rid_new}" Type="{REL_TYPE}" '
                        f'Target="commentsExtended.xml"/></Relationships>')
    parts["word/_rels/document.xml.rels"] = rels.encode("utf8")

# ------------------------------------------------------------------- rewrite
if "word/commentsExtended.xml" not in order:
    order.insert(order.index("word/comments.xml") + 1, "word/commentsExtended.xml")
with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zo:
    for name in order:
        info = infos.get(name)
        zi = zipfile.ZipInfo(name, date_time=info.date_time if info else (2026, 11, 3, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zo.writestr(zi, parts[name])
print(f"wrote {DST}")

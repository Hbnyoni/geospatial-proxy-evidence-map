#!/usr/bin/env python3
"""Append the open-access and REF-readiness section to the response letter, in both formats.

The letter's original renderer was a throwaway and is gone, so this appends to the existing .docx
rather than re-rendering it. Nothing already in the letter is touched, and the same text is appended
to the Markdown source so the two do not drift apart.

    python3 scripts/23_append_ref_section.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import docx

ROOT = Path(__file__).resolve().parent.parent
REV = ROOT / "review" / "revision_2026-10-27"
MARKER = "Open access, deposit and REF readiness"

HEAD = MARKER
INTRO = (
    "Added after the figure round, at the author's request. The University of Cape Town does not "
    "submit to the UK Research Excellence Framework, but the third affiliation on this paper is the "
    "Liverpool School of Tropical Medicine, which does. The declarations are therefore written so "
    "that the paper can be submitted there and judged on its content rather than returned on "
    "paperwork, and so that an assessor can trace each claim about the work to evidence in the "
    "paper or in the deposit."
)
ITEMS = [
    ("Data and code availability, rewritten.", "It previously read “available from the authors "
     "and will be deposited in a public repository on acceptance”. An on-request promise is now "
     "widely read as non-availability. It now names what is deposited, the CC BY 4.0 licence and the "
     "deposit DOI, and states that the search strings and retrieval dates are archived so the corpus "
     "can be rebuilt independently."),
    ("Funding, rewritten.", "It previously read “No funding was acquired for this study”. It "
     "now records the NIEHS and Office of Strategic Coordination award U01ES036146-0 and the Fogarty "
     "International Center award U54TW012083 through the HE2AT Centre, which support the doctoral "
     "programme this review sits in, acknowledges institutional support, and adds the standard "
     "statement that no funder had any role in the review or the decision to submit. The PRECISE "
     "award is deliberately not listed, because no PRECISE data is used in a bibliometric review."),
    ("Open access, new.", "The rights-retention wording: a CC BY 4.0 licence applied to the Author "
     "Accepted Manuscript, deposited with no embargo in the Liverpool School of Tropical Medicine "
     "and University of Cape Town repositories within three months of acceptance. This is the "
     "sentence that makes the output eligible, and the deadline runs from acceptance, so it has to "
     "be on the page before submission rather than arranged afterwards."),
    ("Contribution of this review, new, closing the introduction.", "One paragraph naming the "
     "originality, the significance and the rigour of the review against figures already reported: "
     "two independent axes rather than a publication ranking; six of 37 proxies holding a leading "
     "place in at least 93% of 2,000 resamples, validation share unrelated to prominence, and "
     "Sub-Saharan Africa at 12 studies of 692; and a corpus of 2,217 records screened under "
     "published rules, audited blind at a precision of 0.75 and a negative predictive value of 0.91, "
     "including the statement that the review's own rank correlation of 0.93 is largely "
     "constructional."),
    ("Pathway to application, new, closing the conclusions.", "What the evidence map is for: "
     "selecting candidate predictors for the personal outdoor exposure indicator being validated "
     "against measured personal exposure in the Gambia, Kenya and Mozambique, and the two findings "
     "that carry into it. This states the impact pathway in the paper instead of leaving an assessor "
     "to infer it."),
    ("Methods, one sentence added.", "The identification paragraph now says that the Boolean string "
     "for each database, the date it was executed and the count it returned are archived in the "
     "deposit."),
]
DEPOSIT = (
    "The deposit itself is built and sitting at review/zenodo_deposit: 81 files, 4.5 MB, holding the "
    "2,217 screened records with all 43 publishable columns and the 692 inclusions, the two screening "
    "workbooks as completed, the identification, agreement, audit and robustness records, 32 derived "
    "tables, 25 analysis scripts and the network files. Abstracts, database index keywords and "
    "cited-reference lists are withheld under the Scopus and Web of Science licence terms, and "
    "WITHHELD_FIELDS.md records what was withheld and why, so the corpus does not merely look "
    "incomplete. The .pkl caches are excluded as well, because unpickling executes code and an "
    "archive should be safe for a stranger to open."
)
ACTIONS = [
    ("The two Boolean search strings are not recorded anywhere in the project files.", "This is the "
     "one real reproducibility gap in the review. The exports carry records but not the query that "
     "produced them, and they cannot be reconstructed from the records. They have to be copied out "
     "of the Scopus and Web of Science search histories, with the date each was run, into "
     "SEARCH_STRATEGY.md. The manuscript now promises them, so the deposit is incomplete until they "
     "are there."),
    ("The deposit DOI is a placeholder.", "The manuscript reads 10.5281/zenodo.XXXXXXX. Upload the "
     "deposit, reserve the DOI, and it replaces that string in one edit."),
    ("Confirm the two award numbers cover this output.", "They are copied from the companion "
     "empirical paper. If the review sits outside both awards, the honest statement is that it was "
     "unfunded, and the original sentence should stand."),
    ("Add ORCID identifiers to the title page.", "Outputs are matched to authors and institutions by "
     "DOI and ORCID. Without them the paper is harder to attribute to a submitting unit, and the "
     "open-access statement refers to author identifiers on the title page."),
]


def main() -> int:
    md = REV / "RESPONSE_TO_SUPERVISOR.md"
    dx = REV / "Response_to_supervisory_review.docx"
    text = md.read_text()
    if MARKER in text:
        print("section already present; nothing appended")
        return 0

    md_block = [f"\n## {HEAD}\n", INTRO, ""]
    md_block += [f"{i}. **{h}** {b}" for i, (h, b) in enumerate(ITEMS, 1)]
    md_block += ["", DEPOSIT, "", "**Needs your decision or an action before submission.**", ""]
    md_block += [f"- **{h}** {b}" for h, b in ACTIONS]
    md.write_text(text.rstrip() + "\n" + "\n".join(md_block) + "\n")

    d = docx.Document(str(dx))
    d.add_heading(HEAD, level=2)
    d.add_paragraph(INTRO)
    for h, b in ITEMS:
        p = d.add_paragraph(style="List Number")
        p.add_run(h).bold = True
        p.add_run(" " + b)
    d.add_paragraph(DEPOSIT)
    p = d.add_paragraph()
    p.add_run("Needs your decision or an action before submission.").bold = True
    for h, b in ACTIONS:
        p = d.add_paragraph(style="List Bullet")
        p.add_run(h).bold = True
        p.add_run(" " + b)
    d.save(str(dx))

    out = docx.Document(str(dx))
    print(f"appended to both; letter now {len(out.paragraphs)} paragraphs, {len(out.tables)} tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())

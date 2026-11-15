# Labelling instruction: compliance requirements stated in Single Audit finding texts

You are an independent labeller. Read each finding text in `blind.jsonl` and record which federal compliance
requirement(s) the text itself states for that finding. Work only from `blind.jsonl`. Do not open any other file, do not
look up the findings anywhere else, and do not write or run code that extracts requirements. Read every text in full.

## Input
`blind.jsonl` has 150 lines. Each line is `{"id": "<report_id> <ref>", "text": "<finding text>"}`. The `ref` (for
example `2024-003`) is the finding you label. A text sometimes discusses other findings too. Label only this one.

## The letters
These are the compliance requirement types on the federal Single Audit data collection form (SF-SAC). They follow
Part 3 of the OMB Compliance Supplement (2 CFR 200, Appendix XI). Quoted from the form's key:

> Enter the letter(s) of all type(s) of compliance requirement(s) that apply to audit findings [...]
> A. Activities allowed or unallowed
> B. Allowable costs/cost principles
> C. Cash management
> D. Reserved
> E. Eligibility
> F. Equipment and real property management
> G. Matching, level of effort, earmarking
> H. Period of performance (or availability) of Federal funds
> I. Procurement and suspension and debarment
> J. Program income
> K. Reserved
> L. Reporting
> M. Subrecipient monitoring
> N. Special tests and provisions
> P. Other

Source: Form SF-SAC, copy published by the New Mexico Department of Finance and Administration,
https://www.nmdfa.state.nm.us/wp-content/uploads/2026/04/SF-SAC-Data-Collection-Form-for-Single-Audits.pdf
(read 15 Nov 2026). D and K are reserved and are never used.

## What counts as "stated"
- The text names the requirement as the compliance requirement of this finding. It may be a field label (such as
  "Compliance Requirement: Reporting", "Area: Eligibility", "Type of compliance requirement: ..."), the finding's title
  or heading (such as "2024-004 – Reporting" or "Finding 2024-002: Procurement, Suspension and Debarment"), or a
  sentence in the body that says which requirement the finding is about (such as "This is a finding on the
  eligibility compliance requirement").
- Use the meaning in the list above. A word alone is not enough. For example, "reporting" in "SEFA reporting" (the
  schedule of expenditures of federal awards), in financial statement reporting, or in the Single Audit "reporting
  package" is not requirement L. "Cost Principles" inside the title of 2 CFR 200 is not requirement B.
- Do not infer a requirement the text does not name. A cited regulation (for example 2 CFR 200.318), the kind of
  program, or what went wrong is not enough. If the text names no requirement, the answer is `none`.
- If the text names several requirements for this finding, give all their letters. A phrase that names both
  activities allowed and allowable costs (for example "Allowable Activities and Costs") counts as both A and B.
- If the text gives an explicit letter code and a name that do not match (for example "Code: A - Allowable Costs"),
  give the code's letter and say so in `note`.
- Give P only if the text itself says the requirement is "Other", or names as the compliance requirement something
  outside A to N.

## Output
Write `labels.jsonl`: one JSON object per line, in the same order as `blind.jsonl`, 150 lines in all:

```
{"id": "<same id>", "letters": "<letters in alphabetical order, or none>", "where": "label|title|prose|none", "span": "<exact quote>", "note": "<optional, short>"}
```

- `letters`: for example `"L"`, `"AB"`, `"EIL"`, or `"none"`.
- `where`: where the clearest statement is. `label` is a field label, `title` is the title or heading, `prose` is a
  body sentence, and `none` goes with `letters: "none"`. If it is stated in several places, pick the first that
  applies in the order label, title, prose.
- `span`: the shortest passage that shows the statement, copied character for character from the text, so it can be
  found by exact search. Use `""` when `letters` is `none`.
- `note`: only when something needs explaining, such as a code that conflicts with a name, a text covering two
  findings, or an unclear case. Leave it out otherwise.

When a case is truly unclear, choose the reading most faithful to the text and explain it in `note`. Do not skip a
finding.

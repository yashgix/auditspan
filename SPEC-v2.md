# findingtrace, SPEC v2: what changes from v1 and why

`SPEC.md` (v1) stays as written, and every v1 behaviour, name and metric it fixes is kept. v2 runs beside it.
The v1 metrics stay in `results/metrics.json`. The v2 metrics go to `results/metrics_v2.json`. v2 changes only the
requirements field. Severity, repeat and questioned costs are exactly as in v1.

## Why v1 is kept unchanged
The v1 acceptance tests pin the corpus counts, the disagreement list and the labelled sample's draw. A v1 fix to any
requirement pattern changes those numbers, so the fixes live in v2 instead of editing v1.

## 1. Two requirement patterns (`extract.LETTERS_V2`)
`LETTERS_V2` is `LETTERS` with two entries replaced:
- `"N": r"special tests?"`. The singular "Special Test and Provision" is common in labels. v1 read
  "Special Test and Provision – Protection of Federal Interest in Real Property" as F, because the first dash part
  named no requirement and the second named "real property".
- `"L": r"reporting(?! package)"`. "Data Collection Form and Single Audit Reporting Package" is the audit filing
  itself, not the Reporting compliance requirement. v1 read it as L.

`requirement_letters(value, letters=LETTERS)`, `requirements(text, letters=LETTERS)` and
`extract(text, letters=LETTERS)` take the pattern table as an optional argument. The default is v1.

## 2. Two more requirement outcomes (`compare.requirements_verdict`)
`OUTCOMES_V2 = ("silent", "agree", "disagree", "a_vs_b", "uncheckable")`. For requirements, with `extra` = the text's
letters that the form does not list:
- no `extra`: `"agree"` (the v1 subset rule).
- `extra` is only A or B, and the form lists the other one: `"a_vs_b"`. A (activities allowed or unallowed) and B
  (allowable costs/cost principles) are often tested and written up together, and auditors file either letter. In v1,
  10 of the 25 requirements disagreements were only this.
- otherwise, the form lists P: `"uncheckable"`. P means "Other" on the SF-SAC form: a requirement outside the
  Compliance Supplement's A-N list. The text cannot be checked against it.
- otherwise: `"disagree"`.

Other fields keep the v1 rule. `verdict(field, value, form, v2=False)`, `outcome(fact, form, v2=False)` and
`compare(finding, v2=False)` take the version flag. The default is v1.

## 3. Scoring and metrics
- `evaluate(findings, rows, v2=False)`: with v2, facts come from `compare(finding, v2=True)`. A flag is a v2
  `"disagree"`, and it is confirmed when the label's own v2 verdict against the form is `"disagree"`.
- `summarize(corpus, rows, v2=False)` and `run.main(data_dir, out, v2=False)`: with v2, every v1 metric is computed
  from the v2 comparison, and two per-field counts are added, `a_vs_b` and `uncheckable` (37 metrics).
  `disagree_rate` and its bootstrap count only `"disagree"`.
- `python experiment.py --out results/metrics.json --v2-out results/metrics_v2.json` writes both. `make experiment`
  runs this.

## 4. Generated README block
- The corpus line says what `facts_quoted_exactly` proves: each quote is an exact copy of its source span. It does not
  show that the quote supports the fact.
- The v1 example table gains a `v2 outcome` column, computed from the data.
- When `metrics_v2.json` is present, a v2 section shows the requirements line, its labelled-sample scores and the first
  confirmed v2 requirements disagreement in `labels.json`, in the same format as v1.

## Not changed in this version
No new extraction rules (title lines, other label wordings) and no new labels. These are planned with a fresh blind
sample, so the gain can be measured out of sample.

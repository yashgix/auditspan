# findingtrace, SPEC v2: what changes from v1 and why

Version 1 (git tag `v1-pipeline-final`, described in `docs/DESIGN.md`) stays as written, and every v1 behaviour, name and metric is kept. v2 runs beside it.
The v1 metrics stay in `results/metrics.json`. The v2 metrics go to `results/metrics_v2.json`. v2 changes only the
requirements field. Severity, repeat and questioned costs are exactly as in v1.

## Why v1 is kept unchanged
The v1 acceptance tests pin the corpus counts, the disagreement list and the labelled sample's draw. A v1 fix to any
requirement rule changes those numbers, so the fixes live in v2 instead of editing v1.

## 1. Requirements extraction (`findingtrace/requirements_v2.py`)
v1 reads only a line that starts with "compliance requirement". In the random 100, it found 13 of the 50 requirements
the labels name. Most of the 37 misses were stated in a way v1 does not read, mostly in the finding's title line.
`requirements_v2(text)` returns the first Fact of these rules, in order:
1. The v1 label (`REQUIREMENT_LABEL`).
2. More label wordings (`LABEL_V2`): "compliance requirement" anywhere in a line, followed by `:`, a dash or a hyphen
   (for example "Uniform Guidance Compliance Requirement Code: A-Allowable Costs"). Also these at the start of a line,
   followed by a separator: "Requirement", "Area", "Control category", "Description", "Type of finding: compliance",
   "Compliance".
3. The title line: among the first 3 non-empty lines, a line that does not start with a field label (criteria,
   condition, cause, effect, context, recommendation, questioned, federal, program, assistance, ALN, CFDA, grantor,
   pass, award, information). The first dash part of the line that names a requirement must be at most 120
   characters (longer is prose). The span is the whole line.

A value's letters (`letters_v2`):
- Explicit letter codes win: "(L.)" or "(L)" anywhere, and, in labels only, a leading code such as "A-" or "N –".
  "Special Tests and Provisions - Reporting (L.)" is L. "Code: A-Allowable Costs" is A.
- Otherwise the v1 dash rule runs with `LETTERS_V2` after removing phrases that name a requirement but are not one
  (`NOT_A_REQUIREMENT`). These are "Single Audit Reporting Package", SEFA, statement, close, clearinghouse and
  "over financial" reporting, "reporting process", and the 2 CFR 200 title ("Uniform Administrative Requirements,
  Cost Principles").
- `LETTERS_V2` differs from `LETTERS` in three entries. N accepts the singular "special test". v1 read
  "Special Test and Provision – Protection of Federal Interest in Real Property" as F. A and B also read "Allowable
  Activities and Costs", "Allowable Costs and Activities" and "Allowable Activities/Costs" as both A and B.

The rules were written while reading the random 100 and the other findings listed in the development record. Their
labelled-sample scores are therefore in-sample. They are frozen at the git tag `v2-rules-frozen`, and a fresh blind
sample measures them out of sample.

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
`compare(finding, v2=False)` take the version flag. The default is v1. With v2, `compare` takes requirements from
`requirements_v2`.

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
- When `metrics_v2.json` is present, a v2 section shows the requirements line, its labelled-sample scores (marked
  in-sample) and the first confirmed v2 requirements disagreement in `labels.json`, in the same format as v1.

## 5. Blind hold-out (`study/heldout/`, `findingtrace/heldout.py`)
- Draw: after the tag `v2-rules-frozen`, `draw.py` (seed 20261115) drew 150 findings at random from those not in
  `dev-ids.jsonl`. That file lists every finding looked at while the rules were written, and why. `ids.txt` lists the
  drawn ids. The texts are in `data/findings_text.csv`, and `draw.py` rebuilds the labeller's input file from them
  (sha256 `2e7d5513691ae641db22a5724a3ff342426275eb511601ad8ae2e95557a0906c`). `SHA256SUMS` covers the folder.
- Labeller: Codex (OpenAI), run through ChatGPT Plus with the default model and high reasoning, in a read-only
  sandbox. It saw only the 150 ids and texts and `LABEL-PROMPT.md`, not the rules, their output or the form values.
  The labels are `labels-codex.jsonl`, unedited. Nobody has reviewed them yet.
- Known bias: the prompt was written by the author of the rules. Its examples share the rules' reading of a few cases
  ("SEFA reporting" and the "reporting package" are not L, "Cost Principles" in the 2 CFR 200 title is not B,
  "Allowable Activities and Costs" is A and B, an explicit code beats a name). Agreement on those cases is not
  independent. The prompt also asks for P when the text names a requirement outside A to N. No rule emits P, so
  recall is also reported with P ignored.
- Scoring (`heldout.score`, written by `experiment.py --heldout-out` to `results/heldout.json`): for v1
  `requirements` and v2 `requirements_v2`:
  - precision is exact letter equality with the label, over extracted facts.
  - false positives are facts where the label says none.
  - "A vs B only" counts facts that differ from the label only in A versus B.
  - recall uses two scopes: `label_title` (stated in a label or title, as `data/labels.json` defines it) and `all`
    (body sentences too).
  - Every rate has a Wilson interval. The findings come from different reports almost always, so no report bootstrap
    is used.
  - Both the extracted facts and the labels are also compared with the form, using `requirements_verdict`.
- The scores are raw. A human check of the disagreements is reported separately, never folded into these numbers.
- Text overlap: `draw.py` excluded development findings by id, not by text. One drawn finding,
  2024-09-GSAFAC-0000384866 2024-001, has exactly the same text as development finding 2024-09-GSAFAC-0000385016
  2024-001. `heldout.score` leaves out any hold-out finding whose text sha256 equals a development finding's, so
  149 findings are scored. That is the headline. A test checks disjointness by id and by text hash.

## 6. Version 2.1: fixes after review (not blind) (`findingtrace/rules_v2_1.py`)
An independent review read the code and the hold-out errors after the hold-out was scored. Its fixes are version 2.1.
Because they were found by looking at hold-out errors, the v2.1 hold-out scores are not blind. The frozen v2 result
stays the headline, and v2.1 is reported beside it. `requirements_v2.py` is unchanged since the tag. v1 is unchanged
because its acceptance tests pin it. v1's per-value answers are now the helpers `repeat_answer` and `costs_answer`,
with the same behaviour, so v2.1 can replace one step.
- Repeat: an explicit "yes" or "no" at the start of the labelled value wins. "Yes, prior finding 2023-001 has not
  been corrected" is a repeat. v1 reads the "not" in the first sentence and says no.
- Questioned costs: "None of" or "No ... of" at the start is not a no-costs answer. "None of the $50,000 was
  allowable" questions $50,000, so it is true.
- Requirements, title line: the scan stops at the first body-section heading (criteria, condition, cause, effect,
  context, recommendation, questioned costs, statement of condition, views of responsible officials). Program
  information lines are still skipped. A regulation title quoted under "Criteria" is no longer read as a title.
- Requirements, audit filing: "reporting deadline ... single audit" and "audit reporting" are removed before
  matching. Submitting the audit is not the Reporting requirement.
- `compare`, `evaluate`, `summarize` and `run.main` take `version` ("v1", "v2" or "v2.1") instead of a v2 flag.
  `experiment.py --v2-1-out` writes `results/metrics_v2_1.json`, and the hold-out file scores all three versions.

## Not changed in this version
Severity, repeat and questioned costs. The labels in `data/labels.json`.

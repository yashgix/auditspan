# findingtrace

**Evidence-linked extraction you can audit.** Every fact the tool reports points at the exact characters it came
from, and its error rate is reported with intervals rather than claimed.

## The question

A US organisation that spends $750,000 or more of federal awards in a fiscal year must obtain a Single Audit
($1,000,000 for fiscal years beginning on or after 1 October 2024, 2 CFR 200.501. Most audits in this dataset cover
earlier fiscal years.) For each finding the auditor writes free text — condition, criteria, cause, effect, questioned
costs — and files the same finding as structured flags on form SF-SAC: material weakness or significant deficiency, a
repeat finding, questioned costs, and the compliance requirement concerned. The text and the form are written by the
same auditor about the same finding, so they should agree.

findingtrace reads the text with plain deterministic rules, extracts those four facts, keeps the character span that
states each one, compares each fact with the filed form, and lists every disagreement with the quote and the form
value side by side. Accuracy is measured on a labelled sample, not asserted.

## This is a stand-in, not SOX

These are government Single Audits under the Uniform Guidance (2 CFR 200, Subpart F), not Sarbanes-Oxley audits of
public companies. SOX evidence is private. The Federal Audit Clearinghouse is a large public corpus of real control
findings that also carries auditor-filed flags to check the text against. Nothing here is claimed about how any company builds audit tooling.

## What is here

- `findingtrace/extract.py` — rule-based extraction of the four facts, each with an exact span.
- `findingtrace/compare.py` — text value versus form value per finding, with outcome `silent`, `agree` or `disagree`.
- `findingtrace/data.py` — loads the pinned CSVs and aggregates the per-award form rows into one form per finding.
- `findingtrace/sample.py`, `findingtrace/labels.py`, `findingtrace/stats.py` — the labelled sample, its scoring,
  Wilson intervals and a report-level bootstrap.
- `findingtrace/run.py`, `experiment.py` — the metrics and the JSON they are written to.
- `SPEC.md` is the v1 specification. `SPEC-v2.md` lists what version 2 changes and why.
- `python -m findingtrace disagreements` — the main output: a CSV of disagreements, each row putting the auditor's
  own words next to what the same auditor filed.

## Run it

Python 3.14, the standard library plus NumPy. From the repository root:

```
make test        # own and v1 acceptance tests. Tests that need data/ skip with a clear message when it is missing
make lint        # ruff check and ruff format --check
make experiment  # writes results/metrics.json (v1) and results/metrics_v2.json (v2)

python demo.py                                     # one-line summary of results/metrics.json
python demo.py --readme README.md --out README.md  # re-render the results block below
```

The experiment takes about a second and is deterministic: two runs write identical bytes. The data is pinned in the
repository, so neither the tests nor the experiment touch the network.

### Command line

```
python -m findingtrace show REPORT_ID REF
python -m findingtrace disagreements [--field severity|repeat|questioned_costs|requirements] [--out PATH]
```

`show` prints one finding's four facts as JSON — each with `field`, `value`, `start`, `end` and `quote` — plus the form
values and the outcomes. `disagreements` writes a CSV with the columns `report_id, ref, field, text_value,
form_value, start, end, quote`, findings in load order and fields in the fixed order
`severity, repeat, questioned_costs, requirements`.

## Data

`data/findings_text.csv` (8,772 rows) and `data/findings.csv` (21,183 rows) hold every row of the FAC's 2025
`findings_text` and `findings` files — what the FAC accepted in calendar 2025 — whose `fac_accepted_date` falls from
2025-07-01 to 2025-12-31, in upstream order. `data/labels.json` is the labelled sample, original to this repository.
`data/MANIFEST.json` records the sha256 and size of all three files, and `data/LICENSE-FAC.md` quotes the terms.

The FAC states: "The data collected by the FAC is free to use and in the public domain" (fac.gov/data, read
2026-11-14). The FAC is run by the U.S. General Services Administration. The findings are written by independent
auditors in Single Audit reports, not in SOX audits.

To rebuild or check the pinned files:

```
python tools/fetch_data.py --verify   # checks the files against MANIFEST.json, no network
python tools/fetch_data.py            # re-downloads from the FAC and rebuilds the subset (needs network, writes data/)
```

The FAC adds and amends records, so a later download may differ. The manifest says when this snapshot was taken.

## Results

The block below is rendered from `results/metrics.json`, `results/metrics_v2.json` and `data/`. No number in it is typed by hand. Re-render it
with `python demo.py --readme README.md --out README.md` after re-running the experiment.

Read the per-field lines carefully: `9 form rows differ` counts **findings**, not rows — the findings whose filed
form rows do not agree with each other on that field. A finding filed against several awards has several form rows.
This number counts that finding once. It is the `form_varies` metric: a property of the form as filed, not an error of
the text and not a count of rows.

The corpus line counts quotes that are an exact copy of their source span. That is true by construction, since each
quote is cut from the text by its start and end. It shows the tool never paraphrases. It does not show that each quote
supports its fact. A severity quote is only the two words "material weakness" or "significant deficiency", so a reader
checks the surrounding text.

Version 2 changes only the requirements field (see `SPEC-v2.md`). It also reads the finding's title line, more label
wordings and explicit letter codes, and it fixes misreads of v1. It stops counting two kinds of difference as
disagreements. One kind is A versus B: "activities allowed or unallowed" and "allowable
costs" are often tested together, and auditors file either letter. The other is a form that says P ("Other"), which the
text cannot be checked against. The v1 numbers stay as they were, and the v1 example table shows each example's
version 2 outcome. The version 2 lines come from `results/metrics_v2.json`.

The version 2 requirements rules were frozen at the git tag `v2-rules-frozen`. Then 150 new findings were drawn at
random from those not looked at while writing the rules, and labelled blind by Codex, an OpenAI model. The blind
hold-out lines below are the honest measure of version 2. The labels' own limits are in `SPEC-v2.md` section 5:
the label prompt shares the rule writer's reading of a few cases, and no person has checked the labels yet. The ids,
labels, prompt and draw script are in `study/heldout/` with checksums.

<!-- results:start -->
Corpus: 6271 findings in 3293 reports, from 8772 text rows and 21183 form rows. 151 split texts and 396 form-only findings are left out. Cited facts: 9503, of which 9503 are an exact copy of their source span (this checks the copying, not that each quote supports its fact).

### Text versus form, per field
- severity: 2707 covered, 2683 agree, 24 disagree (0.9% [0.5%, 1.3%]) in 22 reports, 9 form rows differ.
- repeat: 2474 covered, 2452 agree, 22 disagree (0.9% [0.5%, 1.4%]) in 19 reports, 26 form rows differ.
- questioned costs: 3474 covered, 3437 agree, 37 disagree (1.1% [0.7%, 1.5%]) in 32 reports, 17 form rows differ.
- requirements: 848 covered, 823 agree, 25 disagree (2.9% [1.7%, 4.4%]) in 20 reports, 33 form rows differ.

### Labelled sample
Labels: labelled by Claude from the text, not by an auditor.
- severity: precision 98.3% [91.0%, 99.7%] (58/59), recall 98.3% [91.0%, 99.7%] (58/59), confirmed flags 53.8% [29.1%, 76.8%] (7/13).
- repeat: precision 97.5% [87.1%, 99.6%] (39/40), recall 79.6% [66.4%, 88.5%] (39/49), confirmed flags 84.6% [57.8%, 95.7%] (11/13).
- questioned costs: precision 100.0% [93.4%, 100.0%] (54/54), recall 83.1% [72.2%, 90.3%] (54/65), confirmed flags 91.7% [64.6%, 98.5%] (11/12).
- requirements: precision 92.9% [68.5%, 98.7%] (13/14), recall 26.0% [15.9%, 39.6%] (13/50), confirmed flags 76.9% [49.7%, 91.8%] (10/13).

### Severity: text versus form
| text / form | material weakness | significant deficiency | none |
| --- | --- | --- | --- |
| material weakness | 1243 | 5 | 2 |
| significant deficiency | 12 | 1440 | 5 |

### First confirmed disagreement per field
| field | finding | text value | form value | quote | v2 outcome |
| --- | --- | --- | --- | --- | --- |
| severity | 2025-06-GSAFAC-0000392695 2025-001 | significant_deficiency | material_weakness | significant deficiency | disagree |
| repeat | 2024-06-GSAFAC-0000377872 2024-003 | false | true | Repeat Finding: No | disagree |
| questioned costs | 2024-06-GSAFAC-0000376191 2024-008 | false | true | Questioned Costs: $0 | disagree |
| requirements | 2024-12-GSAFAC-0000381878 2024-006 | AB | B | Compliance Requirement Affected: Activities Allowed/Allowable Costs | a_vs_b |

### Version 2: requirements (SPEC-v2.md, the other fields are as in version 1)
- requirements: 2502 covered, 2307 agree, 94 disagree (3.8% [2.9%, 4.7%]) in 82 reports, 33 form rows differ.
- requirements outcomes not counted as disagreements: 53 differ only in A versus B, 48 uncheckable (the form says P, Other).

Labelled sample, version 2. The version 2 rules were written while reading this sample, so these scores are in-sample, not a measure on new findings:
- requirements: precision 95.9% [86.3%, 98.9%] (47/49), recall 94.0% [83.8%, 97.9%] (47/50), confirmed flags 50.0% [18.8%, 81.2%] (3/6).

| field | finding | text value | form value | quote |
| --- | --- | --- | --- | --- |
| requirements | 2023-09-GSAFAC-0000374131 2023-003 | ABE | E | Compliance Requirement: Eligibility and Allowable Activities/Costs |

### Blind hold-out: requirements on new findings
150 findings drawn after the version 2 rules were frozen (git tag `v2-rules-frozen`), labelled by Codex (an OpenAI model) from the text alone, not by an auditor. Raw scores, before any human check.

| rules | extracted | precision | false positives | A vs B only | recall, label or title | recall, label or title, P ignored | recall, all statements |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 9 | 100.0% [70.1%, 100.0%] (9/9) | 0 | 0 | 11.4% [6.1%, 20.3%] (9/79) | 12.2% [6.5%, 21.5%] (9/74) | 8.4% [4.5%, 15.2%] (9/107) |
| v2 | 59 | 91.5% [81.6%, 96.3%] (54/59) | 3 | 0 | 68.4% [57.5%, 77.6%] (54/79) | 74.3% [63.3%, 82.9%] (55/74) | 50.5% [41.1%, 59.8%] (54/107) |

- Codex labels: 35 label, 44 title, 28 body sentence, 43 none. 11 include P (Other), which no rule emits. Against the form: 84 agree, 19 disagree, 0 a_vs_b, 4 uncheckable.
- v2 facts against the form: 55 agree, 3 disagree, 0 a_vs_b, 1 uncheckable.
<!-- results:end -->

## Limits

- Labels are by one AI labeller (Claude) from the text alone, not by an auditor, and were not double-checked by a
  person. A disagreement means the text and the form differ. It does not say which one is wrong.
- The rules were tuned while reading about 80 flagged disagreements with form values visible, in the same session that
  later labelled the disagreement strata. `flag_precision` is therefore not an out-of-sample measure. Only the random
  stratum is, and about 2 of its 100 findings may overlap those read during development.
- Rules miss facts stated in unusual ways. Recall is reported per field and is low for requirements, where only
  labelled lines are read. Version 2 also reads title lines, but its rules were written while reading the random
  labelled sample, so its scores there are in-sample until a fresh blind sample is scored. Multi-part findings (a
  different severity per part) and one text covering two findings are known error sources for severity and
  requirements.
- Questioned costs under the $25,000 reporting threshold are skipped when the text says so. A small stated amount with
  the form saying "no" is still listed, though the threshold may explain it.
- `form_varies` counts findings, not rows: a finding filed against three awards whose flags disagree counts once. It
  says how much the filed form wobbles on its own, so a `form rows differ` number is smaller than the number of rows
  involved and is not evidence that the text is wrong.
- One subset only (FAC acceptances July–December 2025). Findings within a report are correlated, hence the report-level
  bootstrap. The labelled sample's Wilson intervals treat findings as independent.
- The blind hold-out labels come from one AI labeller (Codex), not an auditor. The label prompt was written by the
  author of the rules and shares its reading of a few cases, so agreement on those cases is not independent.
- Proxy domain: Single Audit findings under the Uniform Guidance, not SOX.

## Layout

```
findingtrace/   package: data, extract, compare, stats, sample, labels, run, __main__
tests/          unittest suite, one module per package module
demo.py         renders the results block and the summary line
experiment.py   writes results/metrics.json
tools/          fetch_data.py: pinned rebuild and --verify check
data/           pinned CSVs, labels, manifest, licence note
docs/           DESIGN.md, INTERVIEW.md
```

## References

- 2 CFR 200.501 and Subpart F, eCFR (the Single Audit requirement).
- FAC public data downloads: https://www.fac.gov/data/download/

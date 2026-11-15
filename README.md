# findingtrace

**Evidence-linked extraction you can audit.** Every fact the tool reports points at the exact characters it came
from, and its error rate is reported with intervals rather than claimed.

## The question

A US organisation that spends $750,000 or more of federal awards in a fiscal year must obtain a Single Audit
($1,000,000 for fiscal years beginning on or after 1 October 2024; 2 CFR 200.501 — most audits in this dataset cover
earlier fiscal years). For each finding the auditor writes free text — condition, criteria, cause, effect, questioned
costs — and files the same finding as structured flags on form SF-SAC: material weakness or significant deficiency, a
repeat finding, questioned costs, and the compliance requirement concerned. The text and the form are written by the
same auditor about the same finding, so they should agree.

findingtrace reads the text with plain deterministic rules, extracts those four facts, keeps the character span that
states each one, compares each fact with the filed form, and lists every disagreement with the quote and the form
value side by side. Accuracy is measured on a labelled sample, not asserted.

## This is a stand-in, not SOX

These are government Single Audits under the Uniform Guidance (2 CFR 200, Subpart F), not Sarbanes-Oxley audits of
public companies. SOX evidence is private; the Federal Audit Clearinghouse is a large public corpus of real control
findings that also carries auditor-filed flags to check the text against. Nothing here is claimed about how any company builds audit tooling.

## What is here

- `findingtrace/extract.py` — rule-based extraction of the four facts, each with an exact span.
- `findingtrace/compare.py` — text value versus form value per finding; outcome `silent`, `agree` or `disagree`.
- `findingtrace/data.py` — loads the pinned CSVs and aggregates the per-award form rows into one form per finding.
- `findingtrace/sample.py`, `findingtrace/labels.py`, `findingtrace/stats.py` — the labelled sample, its scoring,
  Wilson intervals and a report-level bootstrap.
- `findingtrace/run.py`, `experiment.py` — the metrics and the JSON they are written to.
- `python -m findingtrace disagreements` — the main output: a CSV of disagreements, each row putting the auditor's
  own words next to what the same auditor filed.

## Run it

Python 3.14, the standard library plus NumPy. From the repository root:

```
make test        # unittest suite; tests that need data/ skip with a clear message when it is missing
make lint        # ruff check and ruff format --check
make experiment  # python experiment.py --out results/metrics.json

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
2026-11-14). The FAC is run by the U.S. General Services Administration; the findings are written by independent
auditors in Single Audit reports, not in SOX audits.

To rebuild or check the pinned files:

```
python tools/fetch_data.py --verify   # checks the files against MANIFEST.json; no network
python tools/fetch_data.py            # re-downloads from the FAC and rebuilds the subset; needs network and writes data/
```

The FAC adds and amends records, so a later download may differ; the manifest says when this snapshot was taken.

## Results

The block below is rendered from `results/metrics.json` and `data/`; no number in it is typed by hand. Re-render it
with `python demo.py --readme README.md --out README.md` after re-running the experiment.

<!-- results:start -->
_Run `python experiment.py --out results/metrics.json`, then `python demo.py --readme README.md --out README.md`, to render the measured results here._
<!-- results:end -->

## Limits

- Labels are by one AI labeller (Claude) from the text alone, not by an auditor, and were not double-checked by a
  person. A disagreement means the text and the form differ; it does not say which one is wrong.
- The rules were tuned while reading about 80 flagged disagreements with form values visible, in the same session that
  later labelled the disagreement strata. `flag_precision` is therefore not an out-of-sample measure. Only the random
  stratum is, and about 2 of its 100 findings may overlap those read during development.
- Rules miss facts stated in unusual ways. Recall is reported per field and is low for requirements, where only
  labelled lines are read. Multi-part findings (a different severity per part) and one text covering two findings are
  known error sources for severity and requirements.
- Questioned costs under the $25,000 reporting threshold are skipped when the text says so; a small stated amount with
  the form saying "no" is still listed, though the threshold may explain it.
- One subset only (FAC acceptances July–December 2025). Findings within a report are correlated, hence the report-level
  bootstrap; the labelled sample's Wilson intervals treat findings as independent.
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

# Design

## 1. Data and the finding key

Three pinned files in `data/`: the finding texts, the form rows and the labels. The texts and form rows are a subset
of the FAC's 2025 files: every row whose `fac_accepted_date` falls from 2025-07-01 to 2025-12-31, in upstream order.
`MANIFEST.json` fixes their sha256; `tools/fetch_data.py` rebuilds them and `--verify` checks them without a network.

A finding is identified by `(report_id, ref)`. In the text file the key is `(report_id, finding_ref_number)`; in the
form file it is `(report_id, reference_number)`; `load` joins on that pair. Only keys that occur in **exactly one**
text row and have **at least one** form row become `Finding` objects, in text-file order. Two kinds of row are left
out and counted instead of dropped silently:

- `split_texts`: keys with more than one text row. Upstream cut one finding's text across rows; there is no single
  text to compare with the form, so the key is excluded rather than guessed at.
- `form_only`: form keys with no text row. There is nothing to read.

`Corpus` carries `text_rows` and `form_rows` (all rows read) alongside those two counters, so the metrics can say
exactly how much of the subset was used and why the rest was not.

## 2. Form aggregation

The form file has one row per award: a finding filed against three federal programs appears three times. `make_form`
collapses the rows of one finding into a single `Form`:

- each of the four booleans is true when **any** row says `Y` (a union);
- `requirements` is the sorted union of every row's `type_requirement` letters;
- `awards` is the number of rows;
- `varies` lists the flag columns whose value is not identical on every row, in the fixed order
  `is_material_weakness, is_significant_deficiency, is_repeat_finding, is_questioned_costs, type_requirement`.

Why a union: the text describes one finding, while the form's job is to say where it applies. A per-award difference
in whether the finding is a material weakness does not make the text wrong, so the most inclusive reading is the fair
one to compare against. Why `varies`: it records how much the form wobbles for that finding on its own. The metrics
report `form_varies` per field, so a reader can see how many compared findings have an internally inconsistent form
before reading anything into a text-versus-form disagreement. It is a property of the comparison, not an error of
either side.

## 3. Extraction

`Fact` is `field, value, start, end, quote`, and every fact is constructed with `start`/`end` in hand, so
`quote == text[start:end]` cannot drift from the value. `extract(text)` calls the four rules and returns them in
`FIELDS` order.

### The labelled-value machinery

Repeat, questioned costs and requirements are usually stated as a labelled line. The label patterns anchor at the
start of a line and `TAIL` captures the rest of the line, optionally after a colon or a dash. Two refinements matter:

- **Next line.** If the captured value is blank, the first non-empty following line is the value. FAC texts routinely
  wrap `Questioned costs:` and its amount onto separate lines.
- **`MAX_VALUE` = 150.** A longer value is prose, not a header value: an auditor who writes a paragraph after
  `Questioned costs:` is explaining, not stating an amount. The match is skipped and the next one tried.

The span runs from the label match to the end of the value as found (before stripping), so the quote shows the reader
the whole labelled line.

### severity

The first singular `material weakness` or `significant deficiency` that classifies *this* finding. Four kinds of
mention are skipped, each for a reason the data forced:

- an unticked box just before it (`[ ]`, `☐`, `□`) — the form's own checkbox, unselected;
- a negation within 30 characters (`no`, `not`, `nor`) — "there was no material weakness";
- a pair just before it (`or`, `and/or`) or just after it — "material weakness or significant deficiency" names
  both without choosing;
- a definition (`… is a deficiency`) and internal control over financial reporting (`… over financial reporting`
  within 40 characters). The form's flags are compliance-audit classifications; the ICFR sentence is a different
  scope, and the definition is not an instance.

Plural forms never match. "Material weaknesses were noted" is a summary of the report, and matching it was wrong far
more often than right. When several kinds survive, the first one stands; the labels take the most severe across the
parts of a finding, which is a known and documented difference (section 7).

### repeat

A labelled answer first: `Repeat finding: Yes/No`, `identification of repeat finding: …`, `prior-year finding number`.
If `REPEAT_NO` appears **anywhere** in the value it is false — the second branch catches "we did not identify a
repeat" — else if `REPEAT_YES` matches at the start it is true, else the next labelled value is tried. With no
labelled answer, two sentence fallbacks apply: `not a repeat finding` gives false, and `this finding is a repeat`,
`is a repeat of` or `repeat finding of 2024-001` give true.

The sentence fallbacks exist because many texts bury the answer in prose, and "not a repeat" is unambiguous. They are
deliberately narrow: a bare "repeat" can describe the prior year's finding, not this one.

### questioned_costs

A labelled amount first. A value containing threshold language ("below the $25,000 threshold", "under", "less than")
is skipped: it is neither a yes nor a no, and the labels call it unknown. `NO_COSTS` at the start (`None`, `N/A`,
`$0.00`, `0`, `$-`) gives false; otherwise the first dollar amount with commas removed, if above zero, gives true; else
the next labelled value is tried. With no labelled answer, "there were no questioned costs" gives false.

### requirements

Only labelled lines: `Compliance requirements: …`, `Type of compliance requirement affected: …`. Requirements are
named in a heading far more reliably than in prose, and reading prose for them produced mostly noise. The value is
split on a spaced dash, and the **first** part that names any requirement decides the letters — later parts describe
the first one, so `Allowable Costs – Time and Effort Reporting` is `B`, not `B` plus something. Letters come out in
`LETTERS` order, which is the order the form uses.

## 4. Comparison

`form_value` maps the form onto the same value types as a `Fact`, with severity falling back material weakness →
significant deficiency → `none`. `outcome` is `silent` when the extractor produced no fact, else `agree` or
`disagree`. Silent is never counted as an error: the extractor says nothing rather than guessing, and a silent field is
informative about coverage, not about accuracy.

Requirements is the one asymmetric rule: it agrees when every letter the text names is on the form. The form lists the
requirements of the award; the text names the ones this finding concerns. Naming fewer is expected and not a
contradiction. Naming one the form does not list is.

### Version 2
`SPEC-v2.md` adds two requirements outcomes beside v1's. Text letters missing from the form only because of A versus
B are `a_vs_b`. Missing letters on a form that lists P (Other) are `uncheckable`. Version 2 extraction
(`requirements_v2.py`) adds more label wordings, explicit letter codes such as "(L.)", the finding's title line, and
exclusions for phrases that only look like a requirement, such as "SEFA reporting". v1 is unchanged, and both sets of
metrics are written.

## 5. Two kinds of interval

The experiment answers two different questions and uses an interval suited to each.

**How often do text and form differ?** The denominator is findings where the text states the fact. Findings inside one
report share an auditor, a template and a set of programs, so resampling findings would understate the spread.
`report_bootstrap` resamples **reports**: one `default_rng(SEED)`, and per replicate each report gets an integer
weight from `rng.integers` + `bincount`; the per-column rate is weighted hits over weighted totals, the denominator
floored at 1 so an empty resample cannot divide by zero; the result is the 2.5th and 97.5th percentile across 2,000
replicates. Fixed seed, identical bytes on every run.

**How accurate is the extractor on the sample?** Precision, recall and confirmed-flag precision are proportions over
sampled findings. Wilson score intervals are used (`z = NormalDist().inv_cdf(0.975)`) rather than the normal
approximation, which misbehaves near 0 and 1 — exactly where a low-recall field sits. `n == 0` returns
`(0.0, 0.0, 1.0)`: no evidence, no claim.

## 6. The labelled sample

- **Random stratum.** 100 keys drawn with `random.Random(20261114).sample` over the sorted keys. Labelled without
  seeing extractor output or form flags, all four fields each. This stratum is the out-of-sample accuracy measure.
- **Disagreement strata.** For each field in `FIELDS` order, up to 12 keys whose outcome is `disagree` and that are
  not already taken, drawn with `Random(SEED + 1 + i)`. The labeller knew which field was flagged, but not what the
  extractor said nor what the form said. That awareness is an accepted bias: it buys a measurement of whether flagged
  disagreements are real, which is the point of the strata.
- **Frozen rules.** The rules were fixed before the draw and not changed after labelling. A label is the fact as the
  text states it, with the same value types as a `Fact`, or null when the text does not state it.
- **Who labelled.** Claude, an AI model, from the text alone; not an auditor, and not reviewed by one.
- **Scoring.** `evaluate` counts, on random rows only, `extracted` (a fact was produced), `correct` (its value equals
  the label; a null label never equals), `stated` (the label is not null) and `found` (correct and stated). On every
  row that labels the field it counts `flagged` (the outcome is `disagree`) and `confirmed` (flagged, the label is not
  null, and the labelled value itself contradicts the form).

The sample is a fixed artefact in `data/labels.json`, so the metrics are reproducible without another labelling pass.

## 7. Trade-offs and known error sources

- **`flag_precision` is in-sample.** The rules were tuned while reading flagged disagreements with the form values
  visible, in the same session that later labelled the disagreement strata. Only the random stratum is out of sample.
- **Multi-part findings.** A finding can carry a material weakness for one requirement and a significant deficiency
  for another. The extractor takes the first mention; the labels keep the most severe. Severity disagreements from
  this cause are expected, and the severity text-versus-form table makes them visible.
- **One text, two findings.** Some texts cover two findings filed separately. Both get the same text, so both inherit
  the same first mention.
- **Requirements recall is low by design.** Only labelled lines are read, so a requirement named only in prose is
  missed. Precision is the field's useful half.
- **The $25,000 threshold.** Costs the text describes as below the reporting threshold are skipped as neither yes nor
  no. A small amount stated plainly against a form that says no is still listed, though the threshold may explain it.
- **One subset, one period.** FAC acceptances from July to December 2025. The findings are real but the sample is not
  a random sample of all Single Audits.
- **No verdict on who is right.** A disagreement says the text and the form differ. Nothing here decides which one is
  wrong, and nothing here is a claim about how any other organisation does this work.

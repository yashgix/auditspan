'''Render the generated results block and a summary.'''

import argparse
import json
from pathlib import Path

from findingtrace import DATA_DIR
from findingtrace.compare import agrees, compare, form_value
from findingtrace.data import load
from findingtrace.extract import FIELDS
from findingtrace.labels import load_labels

START = '<!-- results:start -->'
END = '<!-- results:end -->'
DEFAULT_RESULTS = 'results'
FIELD_LABELS = {
    'severity': 'severity',
    'repeat': 'repeat',
    'questioned_costs': 'questioned costs',
    'requirements': 'requirements',
}
SEVERITY_VALUES = ('material_weakness', 'significant_deficiency')
FORM_VALUES = ('material_weakness', 'significant_deficiency', 'none')


def _text(value: str | bool) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _pct(value: float) -> str:
    return f'{100.0 * float(value):.1f}%'


def _interval(lo: float, hi: float) -> str:
    return f'[{_pct(lo)}, {_pct(hi)}]'


def _corpus_line(metrics: dict) -> str:
    findings = metrics['findings']
    reports = metrics['reports']
    text_rows = metrics['text_rows']
    form_rows = metrics['form_rows']
    split_texts = metrics['split_texts']
    form_only = metrics['form_only_findings']
    facts = metrics['facts']
    quoted = metrics['facts_quoted_exactly']
    return (
        f'Corpus: {findings} findings in {reports} reports; '
        f'{text_rows} text rows, {form_rows} form rows; '
        f'{split_texts} split texts and {form_only} form-only findings left out; '
        f'{facts} cited facts, {quoted} quoted exactly.'
    )


def _comparison_lines(metrics: dict) -> list[str]:
    lines = []
    for index, field in enumerate(FIELDS):
        covered = metrics['covered'][index]
        agree = metrics['agree'][index]
        disagree = metrics['disagree'][index]
        rate = metrics['disagree_rate'][index]
        lo = metrics['disagree_rate_lo'][index]
        hi = metrics['disagree_rate_hi'][index]
        reports = metrics['disagree_reports'][index]
        varies = metrics['form_varies'][index]
        line = (
            f'- {FIELD_LABELS[field]}: {covered} covered, {agree} agree, {disagree} disagree '
            f'({_pct(rate)} {_interval(lo, hi)}); {reports} reports; {varies} form rows differ.'
        )
        lines.append(line)
    return lines


def _quality_lines(metrics: dict) -> list[str]:
    lines = []
    for index, field in enumerate(FIELDS):
        precision = metrics['precision'][index]
        precision_lo = metrics['precision_lo'][index]
        precision_hi = metrics['precision_hi'][index]
        correct = metrics['correct'][index]
        extracted = metrics['extracted'][index]
        recall = metrics['recall'][index]
        recall_lo = metrics['recall_lo'][index]
        recall_hi = metrics['recall_hi'][index]
        found = metrics['found'][index]
        stated = metrics['stated'][index]
        flag_precision = metrics['flag_precision'][index]
        flag_lo = metrics['flag_precision_lo'][index]
        flag_hi = metrics['flag_precision_hi'][index]
        confirmed = metrics['confirmed'][index]
        flagged = metrics['flagged'][index]
        line = (
            f'- {FIELD_LABELS[field]}: precision {_pct(precision)} '
            f'{_interval(precision_lo, precision_hi)} ({correct}/{extracted}); '
            f'recall {_pct(recall)} {_interval(recall_lo, recall_hi)} ({found}/{stated}); '
            f'confirmed flags {_pct(flag_precision)} '
            f'{_interval(flag_lo, flag_hi)} ({confirmed}/{flagged}).'
        )
        lines.append(line)
    return lines


def _severity_lines(metrics: dict) -> list[str]:
    cells = metrics['severity_text_vs_form']
    lines = [
        '| text / form | material weakness | significant deficiency | none |',
        '| --- | --- | --- | --- |',
    ]
    for text in SEVERITY_VALUES:
        values = [str(cells.get(f'{text}__{form}', 0)) for form in FORM_VALUES]
        label = text.replace('_', ' ')
        lines.append('| ' + ' | '.join([label, *values]) + ' |')
    return lines


def _cell(value: str) -> str:
    return value.replace('|', '&#124;')


def _first_confirmed(data_dir) -> dict[str, tuple]:
    findings = {finding.key: finding for finding in load(data_dir).findings}
    found = {}
    for row in load_labels(data_dir):
        finding = findings.get((row['report_id'], row['ref']))
        if finding is None:
            continue
        labels = row.get('labels', {})
        for field in FIELDS:
            if field in found or field not in labels:
                continue
            label = labels[field]
            fact, verdict = compare(finding)[field]
            if verdict == 'disagree' and label is not None and not agrees(field, label, finding.form):
                found[field] = (finding, fact, label)
        if len(found) == len(FIELDS):
            break
    return found


def _disagreement_lines(data_dir) -> list[str]:
    found = _first_confirmed(data_dir)
    lines = [
        '| field | finding | text value | form value | quote |',
        '| --- | --- | --- | --- | --- |',
    ]
    for field in FIELDS:
        entry = found.get(field)
        if entry is None:
            lines.append(f'| {FIELD_LABELS[field]} | none | - | - | - |')
            continue
        finding, fact, _label = entry
        quote = _cell(' '.join(fact.quote.split()))
        lines.append(
            '| '
            + ' | '.join(
                (
                    FIELD_LABELS[field],
                    f'{finding.report_id} {finding.ref}',
                    _cell(_text(fact.value)),
                    _cell(_text(form_value(finding.form, field))),
                    quote,
                )
            )
            + ' |'
        )
    return lines


def render_block(metrics: dict, data_dir=DATA_DIR) -> str:
    lines = [
        _corpus_line(metrics),
        '',
        '### Text versus form, per field',
        *_comparison_lines(metrics),
        '',
        '### Labelled sample',
        'Labels: labelled by Claude from the text, not by an auditor.',
        *_quality_lines(metrics),
        '',
        '### Severity: text versus form',
        *_severity_lines(metrics),
        '',
        '### First confirmed disagreement per field',
        *_disagreement_lines(data_dir),
    ]
    return chr(10).join(lines)


def replace_block(document: str, block: str) -> str:
    start = document.find(START)
    if start < 0:
        raise ValueError('README results markers not found')
    end = document.find(END, start + len(START))
    if end < 0:
        raise ValueError('README results markers not found')
    separator = chr(10)
    return f'{document[:start]}{START}{separator}{block}{separator}{END}{document[end + len(END):]}'


def _summary(metrics: dict) -> str:
    findings = metrics['findings']
    reports = metrics['reports']
    facts = metrics['facts']
    disagreements = metrics['disagree'][0]
    return (
        f'{findings} findings across {reports} reports; '
        f'{facts} cited facts; {disagreements} severity disagreements.'
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', default=DEFAULT_RESULTS)
    parser.add_argument('--readme')
    parser.add_argument('--out')
    parser.add_argument('--data', default=DATA_DIR)
    args = parser.parse_args(argv)
    metrics = json.loads((Path(args.results) / 'metrics.json').read_text(encoding='utf-8'))
    if args.readme is None:
        print(_summary(metrics))
        return 0
    if args.out is None:
        parser.error('--out is required with --readme')
    document = Path(args.readme).read_text(encoding='utf-8')
    block = render_block(metrics, args.data)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(replace_block(document, block), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

'''Tests for demo.py.'''

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import demo

TEXT_HEADER = ['report_id', 'audit_year', 'finding_ref_number', 'finding_text']
FORM_HEADER = [
    'report_id',
    'reference_number',
    'is_material_weakness',
    'is_significant_deficiency',
    'is_repeat_finding',
    'is_questioned_costs',
    'type_requirement',
]

TEXT = '''Material weakness in controls.
Repeat finding: Yes
Questioned costs: $1,000
Compliance requirements: Reporting
'''


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, lineterminator=chr(10))
        writer.writerow(header)
        writer.writerows(rows)


def write_data(folder: Path) -> None:
    write_csv(
        folder / 'findings_text.csv',
        TEXT_HEADER,
        [['R1', '2024', '1', TEXT]],
    )
    write_csv(
        folder / 'findings.csv',
        FORM_HEADER,
        [['R1', '1', 'N', 'Y', 'N', 'N', 'A']],
    )
    labels = {
        'findings': [
            {
                'report_id': 'R1',
                'ref': '1',
                'stratum': 'random',
                'labels': {
                    'severity': 'material_weakness',
                    'repeat': True,
                    'questioned_costs': True,
                    'requirements': 'L',
                },
            }
        ]
    }
    (folder / 'labels.json').write_text(json.dumps(labels), encoding='utf-8')


def sample_metrics() -> dict:
    return {
        'text_rows': 1,
        'form_rows': 1,
        'findings': 1,
        'reports': 1,
        'split_texts': 0,
        'form_only_findings': 0,
        'labelled': 1,
        'labelled_random': 1,
        'replicates': 10,
        'facts': 4,
        'facts_quoted_exactly': 4,
        'covered': [1, 1, 1, 1],
        'agree': [0, 0, 0, 0],
        'disagree': [1, 1, 1, 1],
        'disagree_reports': [1, 1, 1, 1],
        'disagree_rate': [1.0, 1.0, 1.0, 1.0],
        'disagree_rate_lo': [0.1, 0.1, 0.1, 0.1],
        'disagree_rate_hi': [1.0, 1.0, 1.0, 1.0],
        'form_varies': [0, 0, 0, 0],
        'extracted': [1, 1, 1, 1],
        'correct': [1, 1, 1, 1],
        'stated': [1, 1, 1, 1],
        'found': [1, 1, 1, 1],
        'flagged': [1, 1, 1, 1],
        'confirmed': [1, 1, 1, 1],
        'precision': [1.0, 1.0, 1.0, 1.0],
        'precision_lo': [0.1, 0.1, 0.1, 0.1],
        'precision_hi': [1.0, 1.0, 1.0, 1.0],
        'recall': [1.0, 1.0, 1.0, 1.0],
        'recall_lo': [0.1, 0.1, 0.1, 0.1],
        'recall_hi': [1.0, 1.0, 1.0, 1.0],
        'flag_precision': [1.0, 1.0, 1.0, 1.0],
        'flag_precision_lo': [0.1, 0.1, 0.1, 0.1],
        'flag_precision_hi': [1.0, 1.0, 1.0, 1.0],
        'severity_text_vs_form': {
            'material_weakness__material_weakness': 1,
            'material_weakness__significant_deficiency': 0,
            'material_weakness__none': 0,
            'significant_deficiency__material_weakness': 0,
            'significant_deficiency__significant_deficiency': 0,
            'significant_deficiency__none': 0,
        },
    }


class DemoTest(unittest.TestCase):
    def test_summary_uses_plain_integer(self):
        with tempfile.TemporaryDirectory() as folder:
            results = Path(folder)
            (results / 'metrics.json').write_text(json.dumps(sample_metrics()), encoding='utf-8')
            output = io.StringIO()
            with redirect_stdout(output):
                status = demo.main(['--results', str(results)])
        self.assertEqual(status, 0)
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('1 findings', lines[0])
        self.assertNotIn('1,', lines[0])

    def test_replace_block_keeps_outside_text(self):
        document = chr(10).join(['before', demo.START, 'old', demo.END, 'after', ''])
        result = demo.replace_block(document, 'BLOCK')
        expected = chr(10).join(['before', demo.START, 'BLOCK', demo.END, 'after', ''])
        self.assertEqual(result, expected)

    def test_readme_is_rendered_from_metrics_and_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data_dir = root / 'data'
            results = root / 'results'
            data_dir.mkdir()
            results.mkdir()
            write_data(data_dir)
            (results / 'metrics.json').write_text(json.dumps(sample_metrics()), encoding='utf-8')
            readme = root / 'README.md'
            readme.write_text(
                chr(10).join(['before', demo.START, 'old', demo.END, 'after', '']),
                encoding='utf-8',
            )
            out = root / 'out' / 'README.md'
            status = demo.main(
                [
                    '--readme',
                    str(readme),
                    '--out',
                    str(out),
                    '--results',
                    str(results),
                    '--data',
                    str(data_dir),
                ]
            )
            self.assertEqual(status, 0)
            text = out.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('before' + chr(10)))
        self.assertTrue(text.endswith('after' + chr(10)))
        self.assertIn(demo.START, text)
        self.assertIn(demo.END, text)
        self.assertIn('Corpus: 1 findings', text)
        self.assertIn('labelled by Claude from the text, not by an auditor', text)
        self.assertIn('| severity | R1 1 | material_weakness | significant_deficiency | Material weakness |', text)
        self.assertIn('| repeat | R1 1 | true | false | Repeat finding: Yes |', text)


if __name__ == '__main__':
    unittest.main()

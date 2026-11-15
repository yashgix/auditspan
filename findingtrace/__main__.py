"""Command line interface for findingtrace."""

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import DATA_DIR
from .compare import compare, form_value
from .data import load
from .extract import FIELDS

CSV_COLUMNS = (
    "report_id",
    "ref",
    "field",
    "text_value",
    "form_value",
    "start",
    "end",
    "quote",
)


def _text(value: str | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m findingtrace")
    parser.add_argument("--data", default=DATA_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("show")
    show.add_argument("report_id")
    show.add_argument("ref")
    show.add_argument("--data", default=argparse.SUPPRESS)

    disagreements = subparsers.add_parser("disagreements")
    disagreements.add_argument("--field", choices=FIELDS)
    disagreements.add_argument("--out")
    disagreements.add_argument("--data", default=argparse.SUPPRESS)
    return parser


def _show(args: argparse.Namespace) -> int:
    corpus = load(args.data)
    key = (args.report_id, args.ref)
    finding = next((item for item in corpus.findings if item.key == key), None)
    if finding is None:
        sys.exit(f"unknown finding: {args.report_id} {args.ref}")
    results = compare(finding)
    payload = {
        "report_id": finding.report_id,
        "ref": finding.ref,
        "facts": {field: asdict(results[field][0]) if results[field][0] is not None else None for field in FIELDS},
        "form": {field: form_value(finding.form, field) for field in FIELDS},
        "outcome": {field: results[field][1] for field in FIELDS},
    }
    print(json.dumps(payload, indent=1))
    return 0


def _disagreements(args: argparse.Namespace) -> int:
    corpus = load(args.data)
    handle = None
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w", newline="", encoding="utf-8")
        stream = handle
    else:
        stream = sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator=chr(10))
        writer.writeheader()
        for finding in corpus.findings:
            results = compare(finding)
            for field in FIELDS:
                if args.field is not None and field != args.field:
                    continue
                fact, verdict = results[field]
                if verdict != "disagree" or fact is None:
                    continue
                writer.writerow(
                    {
                        "report_id": finding.report_id,
                        "ref": finding.ref,
                        "field": field,
                        "text_value": _text(fact.value),
                        "form_value": _text(form_value(finding.form, field)),
                        "start": fact.start,
                        "end": fact.end,
                        "quote": fact.quote,
                    }
                )
    finally:
        if handle is not None:
            handle.close()
    return 0


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "show":
        return _show(args)
    return _disagreements(args)


if __name__ == "__main__":
    raise SystemExit(main())

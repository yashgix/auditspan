"""Rebuild the pinned Federal Audit Clearinghouse subset in data/ and check it against data/MANIFEST.json.

The subset is every row of the FAC's 2025 files (rows the FAC accepted in calendar 2025) whose fac_accepted_date is
from 2025-07-01 to 2025-12-31, in upstream order. The FAC data is public domain. `--verify` needs no network.
"""

import argparse
import csv
import hashlib
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCE = "https://app.fac.gov/dissemination/public-data/gsa/audit-year/2025-ay-{table}.csv"
TABLES = ("findings", "findings_text")
FIRST, LAST = "2025-07-01", "2025-12-31"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def problems(manifest):
    return [name for name, entry in manifest["files"].items()
            if not (DATA / name).is_file() or sha256(DATA / name) != entry["sha256"]]  # fmt: skip


def subset(source, target):
    csv.field_size_limit(sys.maxsize)
    with open(source, newline="", encoding="utf-8") as fin, open(target, "w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, reader.fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row for row in reader if FIRST <= row["fac_accepted_date"] <= LAST)


def download(table, folder):
    path = Path(folder) / f"{table}.csv"
    request = urllib.request.Request(SOURCE.format(table=table), headers={"User-Agent": "auditspan fetch"})
    with urllib.request.urlopen(request, timeout=300) as response, open(path, "wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="check files only; no network")
    args = parser.parse_args()
    manifest = json.loads((DATA / "MANIFEST.json").read_text())
    if not args.verify:
        with tempfile.TemporaryDirectory() as folder:
            for table in TABLES:
                subset(download(table, folder), DATA / f"{table}.csv")
    bad = problems(manifest)
    for name in bad:
        print(f"missing or changed: {name}", file=sys.stderr)
    if bad:
        sys.exit("the FAC data no longer matches the pinned snapshot (the FAC adds and amends records)")
    print(f"{len(manifest['files'])} files match MANIFEST.json")


if __name__ == "__main__":
    main()

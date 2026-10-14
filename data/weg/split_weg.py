"""Split the wide Worldwide Equipment Guide export into two Git-friendly CSVs.

The ODIN WEG export has one column per attribute name (13k+ columns) and fills
99.7% of cells with the placeholder ``-``. This script writes:

- ``systems.csv``: one row per system with the always-populated core columns.
- ``attributes.csv``: every other non-``-`` cell, as ``identifier,attribute,value``.

It then rebuilds each system from the two files and fails if any value differs.

Usage: ``uv run python data/weg/split_weg.py <wide.csv> <out_dir>``
"""

import csv
import sys
from pathlib import Path

MISSING = "-"
KEY = "identifier"
SYSTEM_COLUMNS = [
    KEY,
    "name",
    "dateOfIntroduction",
    "disname",
    "disstring",
    "origin",
    "proliferation",
    "domain",
    "type",
]


def read_wide(path: Path) -> dict[str, dict[str, str]]:
    """Read the wide CSV into ``{identifier: {column: value}}``, keeping every cell."""
    csv.field_size_limit(sys.maxsize)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        missing = set(SYSTEM_COLUMNS) - set(header)
        if missing:
            raise ValueError(f"Wide CSV lacks expected columns: {sorted(missing)}")
        if len(set(header)) != len(header):
            raise ValueError("Wide CSV has duplicate column names")
        systems: dict[str, dict[str, str]] = {}
        for line_no, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(
                    f"Line {line_no}: {len(row)} fields, header has {len(header)}"
                )
            record = dict(zip(header, row, strict=True))
            key = record[KEY]
            if key in systems:
                raise ValueError(f"Line {line_no}: duplicate identifier {key}")
            systems[key] = record
    return systems


def write_split(systems: dict[str, dict[str, str]], out_dir: Path) -> tuple[int, int]:
    """Write ``systems.csv`` and ``attributes.csv``; return their data row counts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    core = set(SYSTEM_COLUMNS)
    n_attr = 0
    with (out_dir / "systems.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(SYSTEM_COLUMNS)
        for key in sorted(systems):
            w.writerow([systems[key][c] for c in SYSTEM_COLUMNS])
    with (out_dir / "attributes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow([KEY, "attribute", "value"])
        for key in sorted(systems):
            for attr, value in sorted(systems[key].items()):
                if attr not in core and value != MISSING:
                    w.writerow([key, attr, value])
                    n_attr += 1
    return len(systems), n_attr


def read_split(out_dir: Path, columns: list[str]) -> dict[str, dict[str, str]]:
    """Rebuild ``{identifier: {column: value}}`` from the two files, filling gaps with ``-``."""
    systems: dict[str, dict[str, str]] = {}
    with (out_dir / "systems.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            systems[row[KEY]] = dict.fromkeys(columns, MISSING) | row
    with (out_dir / "attributes.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            systems[row[KEY]][row["attribute"]] = row["value"]
    return systems


def main(src: Path, out_dir: Path) -> None:
    """Split ``src`` into ``out_dir`` and verify the round trip."""
    wide = read_wide(src)
    columns = list(next(iter(wide.values())))
    n_sys, n_attr = write_split(wide, out_dir)
    if read_split(out_dir, columns) != wide:
        raise AssertionError(
            "Round trip mismatch: split files do not reproduce the wide CSV"
        )
    print(f"OK: {n_sys} systems, {n_attr} attribute rows, round trip verified")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))

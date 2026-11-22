"""Check the exported seed sheets for displayed values that differ from the quoted source.

The export returns displayed (formatted) values. A cell formatted to fewer decimals than its
evidence quotes shows a rounded number (M13 showed 1 for a quoted 0.86). This check lists:

  1. the numeric columns of every exported tab, so their number formats can be checked;
  2. every numeric cell whose value equals a quoted number in the same row only after rounding.

Read only. Usage:  uv run python -m scripts.check_sheet_numbers
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _to_float(text: str) -> float | None:
    cleaned = text.strip().replace(",", "").replace("$", "").removesuffix("%")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _decimals(text: str) -> int:
    cleaned = text.strip().replace(",", "").removesuffix("%")
    return len(cleaned.split(".")[1]) if "." in cleaned else 0


def check_file(path: Path) -> tuple[list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], []
    header, body = rows[0], rows[1:]
    numeric = []
    for i, name in enumerate(header):
        cells = [r[i] for r in body if i < len(r) and r[i].strip()]
        if cells and all(_to_float(c) is not None for c in cells):
            numeric.append(name or f"column {i + 1}")
    flags = []
    for r in body:
        text = " ".join(c for c in r if c and _to_float(c) is None)
        quoted = [float(x) for x in NUMBER.findall(text)]
        for i, cell in enumerate(r[: len(header)]):
            if not cell.strip():
                continue
            value = _to_float(cell)
            if value is None or header[i] in numeric and not header[i]:
                continue
            for q in quoted:
                if q != value and round(q, _decimals(cell)) == value:
                    flags.append(
                        f"{path.relative_to(ROOT)} | {r[0]} | {header[i]}: cell {cell.strip()!r} "
                        f"rounds the quoted {q}"
                    )
                    break
    return numeric, flags


def main() -> int:
    total_flags = 0
    for path in sorted(ROOT.glob("data/*/sheet/*.csv")):
        numeric, flags = check_file(path)
        if numeric:
            print(f"{path.relative_to(ROOT)}: numeric columns: {', '.join(numeric)}")
        for flag in flags:
            print("  FLAG " + flag)
        total_flags += len(flags)
    print(f"flags: {total_flags}")
    return 0 if total_flags == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

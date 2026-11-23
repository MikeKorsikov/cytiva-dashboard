"""Layer rule (audit B-24): the app, the metrics and the domain never import the ingest package.

The ingest package holds the loaders, which import network libraries (yfinance) and write to the
database. Screens and metrics read the database and shared constants only.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ("src/app", "src/metrics", "src/domain")
IMPORT = re.compile(
    r"^\s*(from\s+src\.ingest\b|import\s+src\.ingest\b|from\s+src\s+import\s+ingest\b)", re.M
)


def test_app_metrics_and_domain_do_not_import_ingest():
    offenders = []
    for layer in LAYERS:
        for path in sorted((ROOT / layer).rglob("*.py")):
            for match in IMPORT.finditer(path.read_text(encoding="utf-8")):
                line = path.read_text(encoding="utf-8")[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{line}")
    assert offenders == [], "move the shared item to src/domain or src/metrics: " + ", ".join(
        offenders
    )

"""Visual baseline: full-page screenshots of the six screens at desktop and phone widths.

Usage (from the repo root):

    uv run python -m scripts.visual_baseline                # writes docs/visual-baseline/
    uv run python -m scripts.visual_baseline --out somewhere

Starts the app with `streamlit run`, opens each screen in Chromium (Playwright), waits for the
page to settle, and saves one PNG per screen and width, plus manifest.json. The data is the
repository's data/app.db at the time of the run; the price and news feeds change daily, so the
baseline is a dated snapshot, not a fixed picture.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP = REPO_ROOT / "src" / "app" / "streamlit_app.py"
DB = REPO_ROOT / "data" / "app.db"
PORT = int(os.environ.get("VISUAL_BASELINE_PORT", "8765"))
BASE = f"http://localhost:{PORT}"

SCREENS = [
    ("01-overview", "overview"),
    ("02-coverage", "coverage"),
    ("03-clusters", "clusters"),
    ("04-demand", "demand"),
    ("05-technology", "technology"),
    ("06-china", "china"),
]
WIDTHS = [("desktop", 1440, 900), ("phone-390", 390, 844)]


def _wait_for_app(process: subprocess.Popen, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("streamlit exited before it was ready")
        try:
            with urllib.request.urlopen(f"{BASE}/_stcore/health", timeout=2) as response:
                if response.read().decode().strip() == "ok":
                    return
        except OSError:
            time.sleep(1)
    raise RuntimeError("streamlit did not become ready")


def _last_refresh() -> dict:
    conn = sqlite3.connect(DB)
    row = conn.execute(
        "SELECT run_id, status, finished_at FROM refresh_run "
        "WHERE status IN ('succeeded', 'completed with errors') ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return {"run_id": row[0], "status": row[1], "finished_at": row[2]} if row else {}


def main(argv: list[str] | None = None) -> int:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "visual-baseline")
    args = parser.parse_args(argv)
    out: Path = args.out

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP),
            "--server.headless",
            "true",
            "--server.port",
            str(PORT),
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=REPO_ROOT,
    )
    shots: list[dict] = []
    try:
        _wait_for_app(server)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for label, width, height in WIDTHS:
                folder = out / label
                folder.mkdir(parents=True, exist_ok=True)
                context = browser.new_context(
                    viewport={"width": width, "height": height}, device_scale_factor=1
                )
                page = context.new_page()
                for file_stem, slug in SCREENS:
                    # The overview is the default page, so its URL is the root, not /overview.
                    url = BASE + "/" if slug == "overview" else f"{BASE}/{slug}"
                    page.goto(url, wait_until="networkidle", timeout=180_000)
                    page.wait_for_selector("text=(screen", timeout=180_000)
                    time.sleep(3)  # let the charts and the map finish drawing
                    path = folder / f"{file_stem}.png"
                    page.screenshot(path=path, full_page=True)
                    shots.append(
                        {
                            "screen": slug,
                            "width": width,
                            "height": height,
                            "file": str(path.relative_to(REPO_ROOT)),
                        }
                    )
                    print(f"saved {path.relative_to(REPO_ROOT)}", flush=True)
                context.close()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()

    manifest = {
        "taken_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "database_last_refresh": _last_refresh(),
        "screens": shots,
        "note": "Snapshot. Price and news feeds change daily; compare layout, not values.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"manifest written: {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

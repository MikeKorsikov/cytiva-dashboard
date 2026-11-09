"""End-of-support register (CD-29). No network: the loader writes curated rows."""

from src.ingest import store, technology
from src.metrics import technology as tech_metrics


def test_register_rows_carry_a_source_and_a_status(tmp_path):
    conn = store.connect(tmp_path / "app.db")
    store.create_schema(conn)
    run_id = store.start_run(conn, "manual")
    assert technology.load_estate_register(conn, run_id) == len(technology.ESTATE)
    register = tech_metrics.estate_register(conn)
    assert len(register) == len(technology.ESTATE)
    for item in register:
        assert item["source_url"].startswith("https://")
        assert item["evidence_label"] == "Signal"
        assert item["vendor_support_status"]


def test_products_without_a_vendor_date_are_marked_to_collect():
    # A product whose vendor date was not found says "to collect"; no date is invented for it.
    products = {row[0]: row[2] for row in technology.ESTATE}
    assert "to collect" in products["Rockwell Automation PlantPAx"]
    assert "to collect" in products["Genetec security platform"]

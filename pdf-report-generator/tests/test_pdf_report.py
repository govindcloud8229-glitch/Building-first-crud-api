import os
import sys
import importlib.util
import tempfile
from pathlib import Path
import pytest
import pypdf
from fastapi.testclient import TestClient

A8_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = A8_DIR.parent

if str(A8_DIR) not in sys.path:
    sys.path.insert(0, str(A8_DIR))

# Load A8 main explicitly
a8_main_path = A8_DIR / "main.py"
spec_a8 = importlib.util.spec_from_file_location("a8_main_mod", str(a8_main_path))
a8_main = importlib.util.module_from_spec(spec_a8)
spec_a8.loader.exec_module(a8_main)

# Load Parent main explicitly
parent_main_path = PARENT_DIR / "main.py"
spec_parent = importlib.util.spec_from_file_location("parent_main_mod", str(parent_main_path))
parent_main = importlib.util.module_from_spec(spec_parent)
spec_parent.loader.exec_module(parent_main)

import database as a8_db
import seed as a8_seed
import report_queries as a8_queries
import pdf_generator as a8_pdf
import report_service as a8_service

a8_client = TestClient(a8_main.app)
parent_client = TestClient(parent_main.app)


@pytest.fixture(scope="module")
def setup_test_db():
    """Set up a dedicated seeded test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "test_report.db"
        test_reports_dir = Path(tmpdir) / "reports"
        test_reports_dir.mkdir(parents=True, exist_ok=True)

        a8_db.init_db(test_db_path)
        count = a8_seed.seed_orders(count=200, db_path=test_db_path)

        yield {
            "db_path": test_db_path,
            "reports_dir": test_reports_dir,
            "seed_count": count,
        }


# 1. Health Check
def test_health_endpoint():
    r = a8_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# 2 & 3. Seed Dataset and Idempotency
def test_seed_dataset_and_idempotency(setup_test_db):
    db_path = setup_test_db["db_path"]
    conn = a8_db.get_db_connection(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    count1 = c.fetchone()[0]
    assert count1 == 200

    # Run seed second time -> should NOT double rows
    a8_seed.seed_orders(count=200, db_path=db_path)
    c.execute("SELECT COUNT(*) FROM orders")
    count2 = c.fetchone()[0]
    conn.close()
    assert count2 == 200


# 4, 5, 6, 7, 8. SQL Aggregations
def test_sql_aggregations(setup_test_db):
    db_path = setup_test_db["db_path"]
    data = a8_queries.get_report_data(db_path)

    # 4 sections present
    assert "total_orders" in data
    assert "total_revenue" in data
    assert "top_products" in data
    assert "orders_per_day" in data
    assert "orders" in data

    # Correct counts and totals
    assert data["total_orders"] == 200
    assert data["total_revenue"] > 0
    assert len(data["top_products"]) <= 5
    assert len(data["top_products"]) > 0
    assert len(data["orders_per_day"]) > 0
    assert len(data["orders"]) == 200

    # Top products ordered descending
    revenues = [p["revenue"] for p in data["top_products"]]
    assert revenues == sorted(revenues, reverse=True)


# 9, 10, 11, 12, 13, 14. PDF Generation & Page Break Verification
def test_pdf_generation_and_page_breaks(setup_test_db):
    db_path = setup_test_db["db_path"]
    reports_dir = setup_test_db["reports_dir"]
    data = a8_queries.get_report_data(db_path)
    pdf_out = reports_dir / "sample_test.pdf"

    a8_pdf.generate_pdf_sync(data, pdf_out)

    # File exists on disk
    assert pdf_out.exists()
    assert pdf_out.stat().st_size > 5000

    # Read with PyPDF to verify valid PDF and page count >= 2
    reader = pypdf.PdfReader(str(pdf_out))
    page_count = len(reader.pages)
    assert page_count >= 2, f"Expected at least 2 pages, got {page_count}"

    # Extract text to verify title and data
    first_page_text = reader.pages[0].extract_text()
    assert "Executive Sales & Order Report" in first_page_text
    assert "TOTAL ORDERS" in first_page_text.upper()


# 15, 16, 17, 18, 19, 20, 21. API Endpoints (POST /reports, GET /reports/{id}, FileResponse)
def test_api_report_lifecycle():
    # 15, 16, 17: Force a fresh report generation -> 201 Created
    r_post = a8_client.post("/reports", json={"force": True})
    assert r_post.status_code == 201
    post_data = r_post.json()
    assert "id" in post_data
    assert "file" in post_data
    report_id = post_data["id"]
    file_link = post_data["file"]
    assert file_link == f"/reports/{report_id}/file"

    # 18: GET /reports/{id} -> 200 Metadata
    r_meta = a8_client.get(f"/reports/{report_id}")
    assert r_meta.status_code == 200
    meta = r_meta.json()
    assert meta["id"] == report_id
    assert meta["file"] == file_link
    assert "created_at" in meta

    # 19: Unknown report ID -> 404
    r_404 = a8_client.get("/reports/999999")
    assert r_404.status_code == 404

    # 20: GET /reports/{id}/file -> 200 application/pdf
    r_file = a8_client.get(file_link)
    assert r_file.status_code == 200
    assert r_file.headers["content-type"] == "application/pdf"
    assert r_file.content.startswith(b"%PDF")

    # 21: JSON metadata endpoint does not contain binary PDF bytes
    assert not isinstance(meta.get("file"), bytes)


# 22, 23, 24. Idempotency & Force Option
def test_idempotency_and_force():
    # Standard call on same day -> 200 with existing ID
    r_dup = a8_client.post("/reports")
    assert r_dup.status_code == 200
    dup_data = r_dup.json()
    existing_id = dup_data["id"]

    # Duplicate call again on same day -> still 200 and same ID
    r_dup2 = a8_client.post("/reports")
    assert r_dup2.status_code == 200
    assert r_dup2.json()["id"] == existing_id

    # 24: POST with force=true -> 201 and new ID
    r_force = a8_client.post("/reports", json={"force": True})
    assert r_force.status_code == 201
    force_data = r_force.json()
    assert force_data["id"] != existing_id
    assert force_data["file"] == f"/reports/{force_data['id']}/file"


# 25. Existing CRUD functionality in parent project still works
def test_parent_crud_regression():
    r = parent_client.get("/")
    assert r.status_code == 200
    assert "features" in r.json()

    r = parent_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = parent_client.get("/tasks")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# 26. Existing AI Triage functionality still works
def test_parent_triage_regression():
    os.environ["LLM_STUB"] = "1"
    os.environ["LLM_ENABLED"] = "true"
    r = parent_client.post("/triage", json={"text": "I need help with my billing invoice."})
    assert r.status_code == 200
    assert "category" in r.json()


# 27. Existing BE-09 Workflow functionality still works
def test_parent_be09_workflow_regression():
    os.environ["LLM_STUB"] = "1"
    r = parent_client.get("/api/workflows/templates")
    assert r.status_code == 200
    templates = r.json()
    assert len(templates) >= 2

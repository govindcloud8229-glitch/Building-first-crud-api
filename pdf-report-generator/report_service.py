import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from database import get_db_connection, DB_PATH
from report_queries import get_report_data
from pdf_generator import generate_pdf, REPORTS_DIR, SCREENSHOTS_DIR
from models import ReportResponse, ReportRequest


async def generate_or_get_report(
    force: bool = False,
    db_path: Path = DB_PATH,
    reports_dir: Path = REPORTS_DIR,
) -> Tuple[ReportResponse, int]:
    """
    Generate a new executive sales PDF report or return today's existing report if idempotent.
    
    Idempotency Policy:
    - If force=False: Checks if a report was already created today (UTC).
      If found: Returns HTTP 200 with existing report ID and file link (0 new PDFs generated).
    - If force=True or no report exists today:
      Executes SQL aggregation, renders HTML, runs Playwright Chromium, saves PDF artifact to disk,
      records metadata in SQLite, and returns HTTP 201 Created.
    
    Returns:
        Tuple of (ReportResponse, status_code: 200 or 201)
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    today_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Stage 5 Idempotency Check: Look for existing report created today
    if not force:
        cursor.execute(
            "SELECT id, path, created_at FROM reports WHERE DATE(created_at) = ? ORDER BY id DESC LIMIT 1",
            (today_date_str,),
        )
        existing = cursor.fetchone()
        if existing:
            report_id = existing["id"]
            pdf_file_path = Path(existing["path"])
            # Ensure physical artifact still exists on disk
            if pdf_file_path.exists():
                conn.close()
                return (
                    ReportResponse(
                        id=report_id,
                        file=f"/reports/{report_id}/file",
                        created_at=existing["created_at"],
                        is_cached=True,
                    ),
                    200,
                )

    # 1. Fetch aggregated report data
    report_data = get_report_data(db_path)
    created_at_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # 2. Reserve database record ID
    cursor.execute(
        "INSERT INTO reports (path, created_at) VALUES (?, ?)",
        ("pending", created_at_iso),
    )
    conn.commit()
    report_id = cursor.lastrowid

    # 3. Destination artifact path
    pdf_filename = f"{report_id}.pdf"
    pdf_path = reports_dir / pdf_filename
    screenshot_path = SCREENSHOTS_DIR / "pdf-page-1.png"

    # 4. Generate PDF via Playwright Headless Chromium
    try:
        await generate_pdf(report_data, pdf_path, screenshot_path=screenshot_path)
    except Exception as e:
        # Clean up database entry if PDF generation fails
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        conn.close()
        raise RuntimeError(f"Playwright PDF generation failed: {e}") from e

    # 5. Update database record with final file path
    cursor.execute(
        "UPDATE reports SET path = ? WHERE id = ?",
        (str(pdf_path), report_id),
    )
    conn.commit()
    conn.close()

    return (
        ReportResponse(
            id=report_id,
            file=f"/reports/{report_id}/file",
            created_at=created_at_iso,
            is_cached=False,
        ),
        201,
    )


def get_report_by_id(report_id: int, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve metadata for a specific report."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "file": f"/reports/{row['id']}/file",
        "path": row["path"],
        "created_at": row["created_at"],
    }

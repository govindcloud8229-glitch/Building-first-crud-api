from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse, JSONResponse

from database import init_db, DB_PATH
from models import ReportRequest, ReportResponse
from report_service import generate_or_get_report, get_report_by_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is initialized on startup."""
    init_db()
    yield


app = FastAPI(
    title="PDF Report Generator API",
    description="A complete data-to-PDF reporting pipeline using SQLite, SQL aggregation, HTML templates, and Playwright Chromium.",
    version="1.0",
    lifespan=lifespan,
)


@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Service health check probe."""
    return {"status": "ok"}


@app.post(
    "/reports",
    response_model=ReportResponse,
    summary="Generate or Retrieve Daily PDF Report",
    tags=["Reports"],
)
async def create_report_endpoint(
    request: Optional[ReportRequest] = None,
    response: Response = None,
):
    """
    Generate an executive sales PDF report from SQLite order aggregations.
    
    Idempotency:
    - First call of the day generates the PDF and returns HTTP 201 Created.
    - Subsequent calls on the same day return HTTP 200 with the existing report link (no duplicate PDFs).
    - If `force=true` is passed in the request body, a fresh PDF is generated with HTTP 201.
    """
    force = request.force if request else False
    try:
        report_res, status_code = await generate_or_get_report(force=force)
        if response:
            response.status_code = status_code
        return report_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@app.get(
    "/reports/{report_id}",
    summary="Get Report Metadata",
    tags=["Reports"],
)
def get_report_metadata_endpoint(report_id: int):
    """Retrieve metadata and download link for a generated report."""
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found.",
        )
    return {
        "id": report["id"],
        "file": report["file"],
        "created_at": report["created_at"],
    }


@app.get(
    "/reports/{report_id}/file",
    summary="Download PDF Report",
    tags=["Reports"],
)
def download_report_file_endpoint(report_id: int):
    """
    Serve the physical PDF report artifact from disk as a binary stream.
    The JSON metadata endpoints do not contain raw PDF bytes.
    """
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found.",
        )

    file_path = Path(report["path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical PDF file artifact not found on server disk.",
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"sales-report-{report_id}.pdf",
    )

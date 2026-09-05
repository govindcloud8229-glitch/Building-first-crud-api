from fastapi import FastAPI

app = FastAPI(
    title="PDF Report Generator API",
    description="A complete data-to-PDF reporting pipeline using SQLite, SQL aggregation, HTML templates, and Playwright Chromium.",
    version="1.0",
)


@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Service health check probe."""
    return {"status": "ok"}

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"


def render_report_html(data: Dict[str, Any]) -> str:
    """
    Render clean, professional HTML for the Executive Sales Report.
    Adheres strictly to Print CSS standards for clean page breaks:
    - tr { break-inside: avoid; } prevents cutting rows in half.
    - thead { display: table-header-group; } ensures repeating table headers on each page.
    """
    total_orders = data.get("total_orders", 0)
    total_revenue = data.get("total_revenue", 0.0)
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0
    generated_at = data.get("generated_at", "N/A")

    top_products = data.get("top_products", [])
    orders_per_day = data.get("orders_per_day", [])
    orders = data.get("orders", [])

    # Format top products rows
    top_products_html = "".join(
        f"""
        <tr>
            <td style="text-align: center; font-weight: bold; color: #475569;">#{idx + 1}</td>
            <td style="font-weight: 600; color: #1e293b;">{item['product']}</td>
            <td style="text-align: right; color: #334155;">{item['order_count']}</td>
            <td style="text-align: right; font-weight: bold; color: #0f766e;">${item['revenue']:,.2f}</td>
        </tr>
        """
        for idx, item in enumerate(top_products)
    )

    # Format daily orders rows
    daily_orders_html = "".join(
        f"""
        <tr>
            <td style="font-weight: 600; color: #1e293b;">{item['date']}</td>
            <td style="text-align: right; color: #334155;">{item['count']} orders</td>
            <td style="text-align: right; font-weight: bold; color: #0f766e;">${item['revenue']:,.2f}</td>
        </tr>
        """
        for item in orders_per_day
    )

    # Format detailed orders rows
    orders_rows_html = "".join(
        f"""
        <tr>
            <td style="text-align: center; font-family: monospace; color: #64748b;">#{o['id']}</td>
            <td style="font-weight: 600; color: #1e293b;">{o['customer']}</td>
            <td style="color: #334155;">{o['product']}</td>
            <td style="text-align: right; font-weight: bold; color: #0f766e;">${o['amount']:,.2f}</td>
            <td style="text-align: center; font-family: monospace; color: #64748b; font-size: 11px;">{o['created_at']}</td>
        </tr>
        """
        for o in orders
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Executive Sales & Order Report</title>
    <style>
        @page {{
            size: A4;
            margin: 16mm 14mm 18mm 14mm;
            @bottom-right {{
                content: "Page " counter(page) " of " counter(pages);
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 9px;
                color: #94a3b8;
            }}
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #ffffff;
            color: #0f172a;
            font-size: 12px;
            line-height: 1.4;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        .report-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding-bottom: 14px;
            border-bottom: 2px solid #0f766e;
            margin-bottom: 16px;
        }}

        .report-title h1 {{
            font-size: 22px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.5px;
        }}

        .report-title p {{
            font-size: 12px;
            color: #64748b;
            margin-top: 2px;
        }}

        .report-badge {{
            background: #f0fdfa;
            border: 1px solid #99f6e4;
            color: #0f766e;
            font-size: 11px;
            font-weight: bold;
            padding: 6px 12px;
            border-radius: 6px;
            text-align: right;
        }}

        /* Metrics Summary Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }}

        .metric-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 14px;
            border-left: 4px solid #0f766e;
        }}

        .metric-card .label {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            font-weight: 700;
        }}

        .metric-card .value {{
            font-size: 20px;
            font-weight: 800;
            color: #0f172a;
            margin-top: 4px;
        }}

        /* Two column layout for summaries */
        .summary-columns {{
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 14px;
            margin-bottom: 22px;
            page-break-after: auto;
        }}

        .section-box {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
        }}

        .section-title {{
            font-size: 13px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        /* Tables & Clean Page Break Styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }}

        /* Repeating headers on subsequent pages */
        thead {{
            display: table-header-group;
        }}

        /* Prevent cutting table rows in half */
        tr {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        th {{
            background: #f1f5f9;
            color: #334155;
            font-weight: 700;
            text-align: left;
            padding: 7px 10px;
            border-bottom: 1px solid #cbd5e1;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        td {{
            padding: 6px 10px;
            border-bottom: 1px solid #f1f5f9;
        }}

        tbody tr:nth-child(even) {{
            background-color: #f8fafc;
        }}

        .table-section {{
            margin-top: 8px;
        }}

        .table-section-header {{
            font-size: 14px;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .footer-note {{
            margin-top: 16px;
            text-align: center;
            font-size: 10px;
            color: #94a3b8;
            border-top: 1px solid #e2e8f0;
            padding-top: 8px;
        }}
    </style>
</head>
<body>

    <!-- Report Header -->
    <div class="report-header">
        <div class="report-title">
            <h1>Executive Sales & Order Report</h1>
            <p>Little Shop Dataset Analytics & Transaction Audit</p>
        </div>
        <div class="report-badge">
            <div><strong>Generated:</strong> {generated_at}</div>
            <div style="font-size: 10px; color: #0d9488; margin-top: 2px;">Status: Production Certified</div>
        </div>
    </div>

    <!-- Metrics Cards -->
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="label">Total Orders</div>
            <div class="value">{total_orders:,}</div>
        </div>
        <div class="metric-card">
            <div class="label">Total Revenue</div>
            <div class="value">${total_revenue:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="label">Average Order Value</div>
            <div class="value">${avg_order_value:,.2f}</div>
        </div>
    </div>

    <!-- Top 5 Products & Daily Volume -->
    <div class="summary-columns">
        <div class="section-box">
            <div class="section-title">
                <span>Top 5 Products by Revenue</span>
                <span style="font-size: 10px; color: #64748b;">Ranked</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 35px; text-align: center;">Rank</th>
                        <th>Product</th>
                        <th style="text-align: right;">Orders</th>
                        <th style="text-align: right;">Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {top_products_html}
                </tbody>
            </table>
        </div>

        <div class="section-box">
            <div class="section-title">
                <span>Order Activity (Last 7 Days)</span>
                <span style="font-size: 10px; color: #64748b;">Daily Trend</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th style="text-align: right;">Orders</th>
                        <th style="text-align: right;">Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {daily_orders_html}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Long Detail Table with Page Break Optimization -->
    <div class="table-section">
        <div class="table-section-header">
            <span>Complete Orders Audit Trail</span>
            <span style="font-size: 11px; font-weight: normal; color: #64748b;">({len(orders)} total transactions)</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px; text-align: center;">Order ID</th>
                    <th>Customer Name</th>
                    <th>Product</th>
                    <th style="text-align: right;">Amount</th>
                    <th style="text-align: center; width: 140px;">Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {orders_rows_html}
            </tbody>
        </table>
    </div>

    <div class="footer-note">
        This document is an automated financial audit generated via Playwright Headless Chromium for FlyRank Assignment A8.
    </div>

</body>
</html>
"""


async def generate_pdf(
    data: Dict[str, Any],
    output_path: Path,
    screenshot_path: Optional[Path] = None,
) -> Path:
    """
    Generate an A4 PDF document from report data using Playwright + headless Chromium.
    Guarantees clean page breaks and repeating table headers across pages.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = render_report_html(data)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set HTML content and wait for full DOM render
        await page.set_content(html_content, wait_until="networkidle")

        # Capture screenshot of Page 1 if requested
        if screenshot_path:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.set_viewport_size({"width": 1200, "height": 1600})
            await page.screenshot(path=str(screenshot_path), full_page=False)

        # Generate A4 PDF with background graphics enabled
        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={
                "top": "16mm",
                "bottom": "18mm",
                "left": "14mm",
                "right": "14mm",
            },
        )

        await browser.close()

    return output_path


def generate_pdf_sync(
    data: Dict[str, Any],
    output_path: Path,
    screenshot_path: Optional[Path] = None,
) -> Path:
    """Synchronous wrapper around async Playwright PDF generation."""
    return asyncio.run(generate_pdf(data, output_path, screenshot_path))


if __name__ == "__main__":
    from report_queries import get_report_data

    sample_data = get_report_data()
    test_pdf = REPORTS_DIR / "test_report.pdf"
    test_screenshot = SCREENSHOTS_DIR / "pdf-page-1.png"

    print("Generating test PDF with Playwright...")
    generate_pdf_sync(sample_data, test_pdf, test_screenshot)
    print(f"Generated PDF saved to: {test_pdf}")
    print(f"Captured screenshot saved to: {test_screenshot}")

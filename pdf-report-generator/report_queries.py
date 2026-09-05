import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from database import get_db_connection, DB_PATH
from models import ReportData, TopProductItem, OrdersPerDayItem, OrderDetailItem


def get_report_data(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Execute SQL aggregation queries across the orders dataset.
    
    Sections aggregated:
    1. Total number of orders and total revenue (COUNT, SUM)
    2. Top 5 products by revenue (GROUP BY, SUM, ORDER BY DESC, LIMIT 5)
    3. Orders per day for the last 7 days (GROUP BY DATE, COUNT, SUM)
    4. Complete list of individual orders for the multi-page detail table
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Total Orders and Total Revenue
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_orders, 
            COALESCE(SUM(amount), 0.0) AS total_revenue 
        FROM orders
    """)
    totals = cursor.fetchone()
    total_orders = totals["total_orders"] if totals else 0
    total_revenue = round(totals["total_revenue"], 2) if totals else 0.0

    # 2. Top 5 Products by Revenue
    cursor.execute("""
        SELECT 
            product, 
            ROUND(SUM(amount), 2) AS revenue, 
            COUNT(*) AS order_count
        FROM orders
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 5
    """)
    top_products_rows = cursor.fetchall()
    top_products = [
        {
            "product": row["product"],
            "revenue": row["revenue"],
            "order_count": row["order_count"],
        }
        for row in top_products_rows
    ]

    # 3. Orders per day for the last 7 days
    cursor.execute("""
        SELECT 
            DATE(created_at) AS order_date,
            COUNT(*) AS order_count,
            ROUND(SUM(amount), 2) AS daily_revenue
        FROM orders
        WHERE created_at >= DATETIME('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY order_date DESC
    """)
    daily_rows = cursor.fetchall()
    orders_per_day = [
        {
            "date": row["order_date"],
            "count": row["order_count"],
            "revenue": row["daily_revenue"],
        }
        for row in daily_rows
    ]

    # 4. Detailed Orders List (for multi-page table)
    cursor.execute("""
        SELECT 
            id, 
            customer, 
            product, 
            ROUND(amount, 2) AS amount, 
            created_at
        FROM orders
        ORDER BY created_at DESC
    """)
    order_rows = cursor.fetchall()
    detailed_orders = [
        {
            "id": row["id"],
            "customer": row["customer"],
            "product": row["product"],
            "amount": row["amount"],
            "created_at": row["created_at"],
        }
        for row in order_rows
    ]

    conn.close()

    report_dict = {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "top_products": top_products,
        "orders_per_day": orders_per_day,
        "orders": detailed_orders,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # Validate against Pydantic schema
    ReportData.model_validate(report_dict)

    return report_dict


if __name__ == "__main__":
    data = get_report_data()
    # Print summary JSON
    summary = {k: v for k, v in data.items() if k != "orders"}
    summary["orders_sample_count"] = len(data["orders"])
    print(json.dumps(summary, indent=2))

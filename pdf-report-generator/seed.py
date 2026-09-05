import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from database import get_db_connection, init_db, DB_PATH

PRODUCTS = [
    "Mechanical Keyboard",
    "Wireless Noise-Canceling Headphones",
    "Ergonomic Mouse",
    "Ultra-Wide Desk Mat",
    "Aluminum Laptop Stand",
    "USB-C Multiport Hub",
]

CUSTOMERS = [
    "Emma Watson",
    "Liam Smith",
    "Olivia Johnson",
    "Noah Williams",
    "Sophia Brown",
    "Jackson Miller",
    "Ava Davis",
    "Lucas Wilson",
    "Isabella Moore",
    "Mason Taylor",
    "Mia Anderson",
    "Ethan Thomas",
    "Harper Jackson",
    "Oliver White",
    "Amelia Harris",
    "Elijah Martin",
    "Evelyn Thompson",
    "Aiden Garcia",
    "Abigail Martinez",
    "James Robinson",
]


def seed_orders(count: int = 200, db_path: Path = DB_PATH) -> int:
    """
    Seed the orders table with random, realistic shop orders.
    Idempotent: Clears existing rows before inserting so running twice leaves exactly `count` rows.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Clear existing orders to guarantee clean idempotency
    cursor.execute("DELETE FROM orders")
    conn.commit()

    now = datetime.now(timezone.utc)
    orders = []

    # Ensure a rich distribution: last 30 days, with heavy representation in the last 7 days
    for _ in range(count):
        # 60% of orders in last 7 days, 40% in days 8-30
        if random.random() < 0.60:
            days_ago = random.uniform(0, 6.9)
        else:
            days_ago = random.uniform(7.0, 30.0)

        order_time = now - timedelta(days=days_ago)
        customer = random.choice(CUSTOMERS)
        product = random.choice(PRODUCTS)
        # Random amount between 5.00 and 200.00 rounded to 2 decimals
        amount = round(random.uniform(5.0, 200.0), 2)
        created_at_str = order_time.strftime("%Y-%m-%d %H:%M:%S")

        orders.append((customer, product, amount, created_at_str))

    cursor.executemany(
        "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)",
        orders,
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM orders")
    total = cursor.fetchone()[0]
    conn.close()

    print(f"Successfully seeded {total} orders into '{db_path.name}'.")
    return total


if __name__ == "__main__":
    seed_orders()

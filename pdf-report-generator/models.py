from typing import List, Optional
from pydantic import BaseModel, Field


class TopProductItem(BaseModel):
    product: str
    revenue: float
    order_count: int


class OrdersPerDayItem(BaseModel):
    date: str
    count: int
    revenue: float


class OrderDetailItem(BaseModel):
    id: int
    customer: str
    product: str
    amount: float
    created_at: str


class ReportData(BaseModel):
    total_orders: int
    total_revenue: float
    top_products: List[TopProductItem]
    orders_per_day: List[OrdersPerDayItem]
    orders: List[OrderDetailItem]
    generated_at: str


class ReportRequest(BaseModel):
    force: bool = Field(default=False, description="If true, bypasses the once-per-day idempotency check and forces a new PDF generation")


class ReportResponse(BaseModel):
    id: int
    file: str
    created_at: Optional[str] = None
    is_cached: Optional[bool] = False

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TriageCategory(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class TriageUrgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TriageRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Customer support message to classify (1-2000 characters).",
        examples=["My credit card was charged twice for subscription renewal."],
    )

    @field_validator("text")
    @classmethod
    def validate_not_empty_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field 'text' cannot be empty or only whitespace")
        return v


class TriageResponse(BaseModel):
    category: TriageCategory = Field(
        ...,
        description="Assigned support category (billing, bug, feature, other).",
    )
    urgency: TriageUrgency = Field(
        ...,
        description="Assigned urgency level (low, normal, high).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="One short sentence explaining the classification.",
    )


class QuarantineLogEntry(BaseModel):
    timestamp: str
    prompt_version: str
    input_text: str
    raw_model_output: str
    error: str
    attempt_count: int

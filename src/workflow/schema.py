from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DecisionType(str, Enum):
    YES = "YES"
    NO = "NO"


class NodePosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class WorkflowNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node")
    label: str = Field(default="Decision Node", description="Human-readable title/label")
    prompt: str = Field(..., min_length=1, max_length=2000, description="Decision prompt for the LLM")
    is_start: bool = Field(default=False, description="Whether this node is designated as the starting node")
    position: Optional[NodePosition] = Field(default=None, description="Canvas X/Y coordinates")

    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Node prompt cannot be empty or whitespace only")
        return v.strip()


class WorkflowEdge(BaseModel):
    id: Optional[str] = Field(default=None, description="Optional edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    decision: DecisionType = Field(..., description="Decision branch this edge represents (YES or NO)")
    source_handle: Optional[str] = Field(default=None, description="React Flow handle ID (e.g., 'yes' or 'no')")

    @field_validator("decision", mode="before")
    @classmethod
    def normalize_decision(cls, v: Any) -> DecisionType:
        if isinstance(v, str):
            v_clean = v.strip().upper()
            if v_clean in ("YES", "Y", "TRUE"):
                return DecisionType.YES
            elif v_clean in ("NO", "N", "FALSE"):
                return DecisionType.NO
        return v


class WorkflowDefinition(BaseModel):
    nodes: List[WorkflowNode] = Field(..., min_length=1, description="List of nodes in the workflow")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="List of directed YES/NO edges")
    start_node_id: Optional[str] = Field(default=None, description="ID of the starting node (defaults to first or is_start node)")
    input_context: Optional[str] = Field(default=None, max_length=4000, description="Optional context text being evaluated by the workflow")


class StepExecution(BaseModel):
    step_number: int
    node_id: str
    node_label: str
    prompt: str
    decision: Optional[str] = None
    status: str = "completed"  # completed, failed, executing
    error: Optional[str] = None
    timestamp: str
    raw_response: Optional[str] = None


class WorkflowRunResult(BaseModel):
    run_id: str
    status: str = "completed"  # completed, failed, running
    start_node_id: str
    input_context: Optional[str] = None
    execution_path: List[str] = Field(default_factory=list, description="Ordered list of visited node IDs")
    steps: List[StepExecution] = Field(default_factory=list, description="Step-by-step execution details")
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class WorkflowValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    start_node_id: Optional[str] = None

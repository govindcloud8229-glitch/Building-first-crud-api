import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import inngest

from src.workflow.schema import (
    WorkflowDefinition,
    WorkflowRunResult,
    StepExecution,
    WorkflowNode,
    WorkflowEdge,
    DecisionType,
)
from src.workflow.llm_decision import evaluate_decision_node, parse_and_validate_decision

logger = logging.getLogger("workflow_inngest")

# In-memory store for recent workflow execution results
WORKFLOW_RUNS: Dict[str, WorkflowRunResult] = {}
MAX_RUNS_HISTORY = 100

# Initialize Inngest Client
inngest_client = inngest.Inngest(
    app_id=os.getenv("INNGEST_APP_ID", "ai-decision-workflow"),
    is_production=False,
)

MAX_WORKFLOW_STEPS = 25


def find_start_node(nodes: List[WorkflowNode], start_node_id: Optional[str] = None) -> Optional[WorkflowNode]:
    """Determine the starting node for workflow execution."""
    if start_node_id:
        for node in nodes:
            if node.id == start_node_id:
                return node

    # Check for node explicitly flagged with is_start=True
    for node in nodes:
        if node.is_start:
            return node

    # Fallback to the first node in the list
    return nodes[0] if nodes else None


async def execute_workflow_logic(
    workflow: WorkflowDefinition,
    step_runner: Optional[inngest.Step] = None,
    run_id: Optional[str] = None,
) -> WorkflowRunResult:
    """
    Core graph execution engine.
    Executes each decision node dynamically, following matching YES/NO edges.
    If step_runner is provided, each node decision is executed as a durable Inngest step.
    """
    actual_run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
    start_time = datetime.now(timezone.utc).isoformat()

    start_node = find_start_node(workflow.nodes, workflow.start_node_id)
    if not start_node:
        result = WorkflowRunResult(
            run_id=actual_run_id,
            status="failed",
            start_node_id="unknown",
            input_context=workflow.input_context,
            execution_path=[],
            steps=[],
            error="Workflow has no valid starting node.",
            created_at=start_time,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        WORKFLOW_RUNS[actual_run_id] = result
        return result

    # Index nodes and outgoing edges for efficient dynamic traversal
    nodes_by_id: Dict[str, WorkflowNode] = {n.id: n for n in workflow.nodes}
    edges_by_source: Dict[str, List[WorkflowEdge]] = {}
    for edge in workflow.edges:
        edges_by_source.setdefault(edge.source, []).append(edge)

    current_node: Optional[WorkflowNode] = start_node
    execution_path: List[str] = []
    step_records: List[StepExecution] = []
    step_count = 0
    workflow_error: Optional[str] = None

    while current_node is not None:
        step_count += 1
        node_id = current_node.id
        execution_path.append(node_id)

        # Safety: Infinite loop prevention
        if step_count > MAX_WORKFLOW_STEPS:
            workflow_error = f"Workflow exceeded maximum step limit ({MAX_WORKFLOW_STEPS}). Possible infinite loop detected."
            step_records.append(
                StepExecution(
                    step_number=step_count,
                    node_id=node_id,
                    node_label=current_node.label,
                    prompt=current_node.prompt,
                    decision=None,
                    status="failed",
                    error=workflow_error,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            break

        step_id = f"node-{step_count}-{node_id}"
        prompt_text = current_node.prompt
        context_text = workflow.input_context

        try:
            # Execute step via Inngest step runner if available, or direct call
            if step_runner is not None:
                async def _inngest_step_fn() -> dict:
                    dec, raw = evaluate_decision_node(prompt_text, context_text)
                    return {"decision": dec, "raw_response": raw}

                step_output = await step_runner.run(step_id, _inngest_step_fn)
                decision = step_output["decision"]
                raw_response = step_output.get("raw_response", "")
            else:
                decision, raw_response = evaluate_decision_node(prompt_text, context_text)

            # Record successful decision step
            step_records.append(
                StepExecution(
                    step_number=step_count,
                    node_id=node_id,
                    node_label=current_node.label,
                    prompt=prompt_text,
                    decision=decision,
                    status="completed",
                    raw_response=raw_response,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

            # Find matching YES or NO outgoing edge
            outgoing = edges_by_source.get(node_id, [])
            matching_edge: Optional[WorkflowEdge] = None
            for e in outgoing:
                if e.decision == decision or (decision == "YES" and e.source_handle == "yes") or (decision == "NO" and e.source_handle == "no"):
                    matching_edge = e
                    break

            if matching_edge:
                next_node_id = matching_edge.target
                if next_node_id in nodes_by_id:
                    current_node = nodes_by_id[next_node_id]
                else:
                    workflow_error = f"Edge points to target node '{next_node_id}' which does not exist in the graph."
                    current_node = None
            else:
                # Terminal node reached (no matching outgoing edge for this decision)
                logger.info(f"[Workflow Execution] Node '{node_id}' decision '{decision}' reached terminal path.")
                current_node = None

        except Exception as e:
            workflow_error = f"Error evaluating node '{node_id}': {str(e)}"
            logger.error(f"[Workflow Error] {workflow_error}")
            step_records.append(
                StepExecution(
                    step_number=step_count,
                    node_id=node_id,
                    node_label=current_node.label,
                    prompt=prompt_text,
                    decision=None,
                    status="failed",
                    error=str(e),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            break

    final_status = "failed" if workflow_error else "completed"
    completed_time = datetime.now(timezone.utc).isoformat()

    result = WorkflowRunResult(
        run_id=actual_run_id,
        status=final_status,
        start_node_id=start_node.id,
        input_context=workflow.input_context,
        execution_path=execution_path,
        steps=step_records,
        error=workflow_error,
        created_at=start_time,
        completed_at=completed_time,
    )

    # Store in memory history (cap size)
    WORKFLOW_RUNS[actual_run_id] = result
    if len(WORKFLOW_RUNS) > MAX_RUNS_HISTORY:
        oldest_key = next(iter(WORKFLOW_RUNS))
        del WORKFLOW_RUNS[oldest_key]

    return result


@inngest_client.create_function(
    fn_id="ai-decision-workflow-run",
    trigger=inngest.TriggerEvent(event="workflow/run"),
)
async def ai_decision_workflow_fn(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Inngest Function for AI Decision Workflow Execution.
    Orchestrates each decision as a distinct durable Inngest step.
    """
    event_data = ctx.event.data
    workflow_data = event_data.get("workflow", {})
    workflow_def = WorkflowDefinition.model_validate(workflow_data)
    run_id = event_data.get("run_id") or f"run_{uuid.uuid4().hex[:10]}"

    result = await execute_workflow_logic(
        workflow=workflow_def,
        step_runner=step,
        run_id=run_id,
    )
    return result.model_dump()

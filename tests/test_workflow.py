import os
import sys
import importlib.util
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure stub mode for automated testing
os.environ["LLM_STUB"] = "1"
os.environ["LLM_ENABLED"] = "true"

ROOT_DIR = Path(__file__).resolve().parent.parent
root_main_path = ROOT_DIR / "main.py"
spec = importlib.util.spec_from_file_location("root_app_main", str(root_main_path))
root_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_main)
app = root_main.app

from src.workflow.llm_decision import parse_and_validate_decision, evaluate_decision_node

client = TestClient(app)


def test_llm_parser_strict_validation():
    """Verify strict parsing for YES/NO decisions."""
    assert parse_and_validate_decision("YES") == "YES"
    assert parse_and_validate_decision("  yes. ") == "YES"
    assert parse_and_validate_decision("```\nNO\n```") == "NO"
    assert parse_and_validate_decision('"YES"') == "YES"

    # Reject ambiguous, conversational, or invalid output
    with pytest.raises(ValueError):
        parse_and_validate_decision("")

    with pytest.raises(ValueError):
        parse_and_validate_decision("Maybe or probably yes, depending on the circumstances.")

    with pytest.raises(ValueError):
        parse_and_validate_decision("I think this is a technical issue.")


def test_yes_branching():
    """Verify that a YES decision follows the YES outgoing edge."""
    payload = {
        "nodes": [
            {"id": "n1", "label": "Support Step", "prompt": "Is this a support request?", "is_start": True},
            {"id": "n2", "label": "Tier 1", "prompt": "Is this a password reset issue?"},
            {"id": "n3", "label": "Sales", "prompt": "Is this an enterprise sales query?"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "decision": "YES", "source_handle": "yes"},
            {"source": "n1", "target": "n3", "decision": "NO", "source_handle": "no"},
        ],
        "start_node_id": "n1",
        "input_context": "I need help resetting my password for support account",
    }

    r = client.post("/api/workflows/run", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "completed"
    assert res["execution_path"] == ["n1", "n2"]
    assert len(res["steps"]) == 2
    assert res["steps"][0]["decision"] == "YES"


def test_no_branching():
    """Verify that a NO decision follows the NO outgoing edge."""
    payload = {
        "nodes": [
            {"id": "n1", "label": "Billing Check", "prompt": "Is this a refund or billing issue?", "is_start": True},
            {"id": "n2", "label": "Billing Queue", "prompt": "Process refund?"},
            {"id": "n3", "label": "Technical Queue", "prompt": "Is this an application bug?"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "decision": "YES", "source_handle": "yes"},
            {"source": "n1", "target": "n3", "decision": "NO", "source_handle": "no"},
        ],
        "start_node_id": "n1",
        "input_context": "The application crashes when clicking export to CSV",
    }

    r = client.post("/api/workflows/run", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "completed"
    assert res["execution_path"] == ["n1", "n3"]
    assert len(res["steps"]) == 2
    assert res["steps"][0]["decision"] == "NO"


def test_multi_node_traversal():
    """Verify multi-tier dynamic graph traversal."""
    payload = {
        "nodes": [
            {"id": "a", "label": "Step A", "prompt": "Is this a support request?", "is_start": True},
            {"id": "b", "label": "Step B", "prompt": "Is this a billing issue?"},
            {"id": "c", "label": "Step C", "prompt": "Is this an urgent billing reversal?"},
        ],
        "edges": [
            {"source": "a", "target": "b", "decision": "YES", "source_handle": "yes"},
            {"source": "b", "target": "c", "decision": "YES", "source_handle": "yes"},
        ],
        "start_node_id": "a",
        "input_context": "Support message: Urgent billing refund needed!",
    }

    r = client.post("/api/workflows/run", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "completed"
    assert res["execution_path"] == ["a", "b", "c"]
    assert len(res["steps"]) == 3


def test_infinite_loop_prevention():
    """Verify that cyclical graphs are stopped safely by maximum step limit."""
    payload = {
        "nodes": [
            {"id": "loop-1", "label": "Loop 1", "prompt": "Is this a support inquiry?", "is_start": True},
            {"id": "loop-2", "label": "Loop 2", "prompt": "Is this a help request?"},
        ],
        "edges": [
            {"source": "loop-1", "target": "loop-2", "decision": "YES", "source_handle": "yes"},
            {"source": "loop-2", "target": "loop-1", "decision": "YES", "source_handle": "yes"},
        ],
        "start_node_id": "loop-1",
        "input_context": "Help support request",
    }

    r = client.post("/api/workflows/run", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "failed"
    assert "infinite loop" in res["error"].lower() or "maximum step limit" in res["error"].lower()
    assert len(res["steps"]) >= 25


def test_graph_validation():
    """Verify workflow graph validation endpoint."""
    # Valid workflow
    r = client.post("/api/workflows/validate", json={
        "nodes": [{"id": "n1", "prompt": "Is this valid?", "is_start": True}],
        "edges": []
    })
    assert r.status_code == 200
    assert r.json()["valid"] is True

    # Invalid workflow (duplicate outgoing YES edge triggers warning, missing target triggers error)
    r = client.post("/api/workflows/validate", json={
        "nodes": [{"id": "n1", "prompt": "Question?", "is_start": True}],
        "edges": [{"source": "n1", "target": "missing_node", "decision": "YES"}]
    })
    assert r.status_code == 200
    assert r.json()["valid"] is False
    assert len(r.json()["errors"]) > 0


def test_existing_crud_regression():
    """Ensure all existing SQLite CRUD endpoints continue to operate perfectly."""
    r = client.get("/")
    assert r.status_code == 200
    assert "features" in r.json()

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/tasks")
    assert r.status_code == 200
    tasks = r.json()
    assert isinstance(tasks, list)

    # Create task
    r = client.post("/tasks", json={"title": "Test regression task"})
    assert r.status_code == 201
    created_id = r.json()["id"]

    # Read task
    r = client.get(f"/tasks/{created_id}")
    assert r.status_code == 200

    # Delete task
    r = client.delete(f"/tasks/{created_id}")
    assert r.status_code == 204


def test_existing_triage_regression():
    """Ensure previous Week 7 Support Triage endpoint continues to operate."""
    r = client.post("/triage", json={"text": "Credit card payment was deducted twice."})
    assert r.status_code == 200
    res = r.json()
    assert "category" in res
    assert "urgency" in res

import sqlite3
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
import inngest.fast_api

from src.llm.schema import TriageRequest, TriageResponse
from src.llm.service import triage_support_message
from src.workflow.router import router as workflow_router
from src.workflow.inngest_workflow import inngest_client, ai_decision_workflow_fn

# SQLite Database Configuration
DB_NAME = "tasks.db"


def get_db_connection():
    """Establish a connection to the SQLite database with row access by column name."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tasks table and insert initial seed data if the table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tasks table if it does not already exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    # Check row count: seed only if database table is completely empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_tasks = [
            ("Learn FastAPI", 0),
            ("Build a CRUD API", 0),
            ("Review HTTP status codes", 1),
        ]
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            seed_tasks
        )
        conn.commit()

    conn.close()


def task_row_to_dict(row: sqlite3.Row) -> dict:
    """Helper to convert a SQLite Row object to the expected API response dictionary."""
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"])
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: ensure SQLite database and tables are ready on startup."""
    init_db()
    yield


app = FastAPI(
    title="Task & AI Workflow API",
    description="A production-grade REST backend with SQLite CRUD, LLM Triage, and AI Decision Flows with React Flow and Inngest.",
    version="2.0",
    lifespan=lifespan
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic request models for input validation and Swagger documentation
class TaskCreate(BaseModel):
    title: str = Field(..., description="Task title (cannot be empty)", example="Buy groceries")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated task title", example="Buy groceries and cook")
    done: Optional[bool] = Field(None, description="Updated completion status", example=True)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        field_path = ".".join(str(loc) for loc in first_error.get("loc", []) if loc != "body")
        msg = first_error.get("msg", "Invalid input")
        detail = f"Invalid field '{field_path}': {msg}" if field_path else f"Validation error: {msg}"
    else:
        detail = "Invalid request payload"

    return JSONResponse(
        status_code=400,
        content=jsonable_encoder({"detail": detail, "errors": errors}),
    )


# Mount Workflow Router
app.include_router(workflow_router)

# Serve Inngest Functions endpoint at /api/inngest
inngest.fast_api.serve(app, inngest_client, [ai_decision_workflow_fn])


@app.get("/", summary="API Information", tags=["General"])
def read_root():
    """Returns basic information about the API."""
    return {
        "name": "Task & AI Workflow API",
        "version": "2.0",
        "features": ["CRUD Tasks", "LLM Support Triage", "AI Decision Flow with React Flow & Inngest"],
    }


@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Returns the operational status of the service."""
    return {
        "status": "ok",
        "database": "connected",
        "inngest": "configured",
    }


@app.get("/tasks", summary="List All Tasks", tags=["Tasks"])
def get_all_tasks():
    """Retrieve all to-do tasks from the SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [task_row_to_dict(row) for row in rows]


@app.get("/tasks/{task_id}", summary="Get Task by ID", tags=["Tasks"])
def get_task(task_id: int):
    """Retrieve a single task by its unique numeric ID using a parameterized SQL query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task_row_to_dict(row)


@app.post("/tasks", status_code=status.HTTP_201_CREATED, summary="Create a Task", tags=["Tasks"])
def create_task(task_in: TaskCreate):
    """Create a new task in SQLite with an auto-generated ID and done=0 (false)."""
    clean_title = task_in.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (clean_title, 0)
    )
    conn.commit()
    new_id = cursor.lastrowid

    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (new_id,))
    new_row = cursor.fetchone()
    conn.close()

    return task_row_to_dict(new_row)


@app.put("/tasks/{task_id}", summary="Update a Task", tags=["Tasks"])
def update_task(task_id: int, task_in: TaskUpdate):
    """Update the title and/or done status of an existing task in SQLite."""
    if task_in.title is None and task_in.done is None:
        raise HTTPException(status_code=400, detail="At least one field (title or done) must be provided for update")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,))
    current_row = cursor.fetchone()
    if current_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    updated_title = current_row["title"]
    updated_done = current_row["done"]

    if task_in.title is not None:
        clean_title = task_in.title.strip()
        if not clean_title:
            conn.close()
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        updated_title = clean_title

    if task_in.done is not None:
        updated_done = 1 if task_in.done else 0

    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (updated_title, updated_done, task_id)
    )
    conn.commit()

    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,))
    updated_row = cursor.fetchone()
    conn.close()

    return task_row_to_dict(updated_row)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Delete a Task", tags=["Tasks"])
def delete_task(task_id: int):
    """Delete a task from SQLite by its numeric ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/triage",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Triage Support Message",
    tags=["LLM Triage"],
)
def triage_endpoint(request: TriageRequest):
    """
    Classify a customer support message into structured JSON with category, urgency, confidence, and reason.
    Adheres strictly to schema validation, single repair retry, and quarantine on failure.
    """
    return triage_support_message(request)

from fastapi import FastAPI, HTTPException, status, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(
    title="Task API",
    description="A simple in-memory REST API for managing a to-do list built with FastAPI and Uvicorn.",
    version="1.0"
)

# In-memory database of tasks
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Review HTTP status codes", "done": True},
]


class TaskCreate(BaseModel):
    title: str = Field(..., description="Task title (cannot be empty)", example="Buy groceries")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated task title", example="Buy groceries and cook")
    done: Optional[bool] = Field(None, description="Updated completion status", example=True)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request: title is required and cannot be empty"},
    )


@app.get("/", summary="API Information", tags=["General"])
def read_root():
    """Returns basic information about the API."""
    return {
        "name": "Task API",
        "version": "1.0"
    }


@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Returns the operational status of the service."""
    return {
        "status": "ok"
    }


@app.get("/tasks", summary="List All Tasks", tags=["Tasks"])
def get_all_tasks():
    """Returns the complete list of to-do tasks currently in memory."""
    return tasks


@app.get("/tasks/{task_id}", summary="Get Task by ID", tags=["Tasks"])
def get_task(task_id: int):
    """Retrieve a single task by its unique numeric ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.post("/tasks", status_code=status.HTTP_201_CREATED, summary="Create a Task", tags=["Tasks"])
def create_task(task_in: TaskCreate):
    """Create a new task with an auto-incremented ID and done=false."""
    clean_title = task_in.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    new_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {
        "id": new_id,
        "title": clean_title,
        "done": False
    }
    tasks.append(new_task)
    return new_task


@app.put("/tasks/{task_id}", summary="Update a Task", tags=["Tasks"])
def update_task(task_id: int, task_in: TaskUpdate):
    """Update the title and/or done status of an existing task."""
    if task_in.title is None and task_in.done is None:
        raise HTTPException(status_code=400, detail="At least one field (title or done) must be provided for update")

    target_task = None
    for task in tasks:
        if task["id"] == task_id:
            target_task = task
            break

    if target_task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task_in.title is not None:
        clean_title = task_in.title.strip()
        if not clean_title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        target_task["title"] = clean_title

    if task_in.done is not None:
        target_task["done"] = task_in.done

    return target_task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Delete a Task", tags=["Tasks"])
def delete_task(task_id: int):
    """Delete a task by its numeric ID."""
    global tasks
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

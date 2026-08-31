from fastapi import FastAPI, HTTPException, status, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# In-memory database of tasks
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Review HTTP status codes", "done": True},
]


class TaskCreate(BaseModel):
    title: str = Field(..., description="Task title")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated task title")
    done: Optional[bool] = Field(None, description="Updated status")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request: title is required and cannot be empty"},
    )


@app.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/tasks")
def get_all_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate):
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


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_in: TaskUpdate):
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


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_task(task_id: int):
    global tasks
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

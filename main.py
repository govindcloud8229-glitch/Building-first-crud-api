from fastapi import FastAPI, HTTPException

app = FastAPI()

# In-memory database of tasks
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Review HTTP status codes", "done": True},
]


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

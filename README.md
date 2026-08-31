# Task API (`flyrank-task-api`)

A clean, lightweight, in-memory REST API for managing a to-do list built with **FastAPI**, **Uvicorn**, and **Pydantic**. Built for the FlyRank Internship Backend AI Engineering Track (Week 2, Assignment A1).

---

## 📌 Project Overview

This project implements a full CRUD (Create, Read, Update, Delete) API adhering strictly to REST conventions and proper HTTP status code standards. 

> **⚠️ In-Memory Storage Note:**  
> This API stores all tasks in a Python in-memory list. No external database or file persistence is used. As expected, any changes (new tasks, updates, deletions) will reset to the default initial tasks whenever the server restarts.

---

## ✨ Features

- **Root & Health Check**: Quickly verify server status and metadata.
- **List Tasks**: Fetch all active to-do items.
- **Get Task by ID**: Retrieve individual tasks with proper `404 Not Found` handling.
- **Create Task**: Add new tasks with auto-incremented IDs and input validation (`201 Created` / `400 Bad Request`).
- **Update Task**: Modify `title` and/or `done` status with validation (`200 OK` / `400 Bad Request` / `404 Not Found`).
- **Delete Task**: Remove tasks returning an empty `204 No Content` response (`404 Not Found` if missing).
- **Interactive Documentation**: Auto-generated interactive API docs via Swagger UI (`/docs`).

---

## 🛠️ Technology Stack

- **Python 3.10+**
- **FastAPI**: Modern, fast web framework for building APIs with Python.
- **Uvicorn**: Lightning-fast ASGI web server implementation.
- **Pydantic**: Data parsing and schema validation.
- **Swagger UI**: Interactive browser-based API testing interface.

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/flyrank-task-api.git
   cd flyrank-task-api
   ```

2. **(Optional) Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Running the Server

Start the API server with one single command:

```bash
uvicorn main:app --reload
```

The server will start listening at: `http://localhost:8000`

---

## 📖 API Endpoints

| Method | Endpoint | Description | Status Code |
|:---|:---|:---|:---|
| **GET** | `/` | API information and metadata | `200 OK` |
| **GET** | `/health` | Service health check | `200 OK` |
| **GET** | `/tasks` | List all tasks | `200 OK` |
| **GET** | `/tasks/{id}` | Get a single task by ID | `200 OK` / `404 Not Found` |
| **POST** | `/tasks` | Create a new task | `201 Created` / `400 Bad Request` |
| **PUT** | `/tasks/{id}` | Update task title and/or status | `200 OK` / `400 Bad Request` / `404 Not Found` |
| **DELETE** | `/tasks/{id}` | Delete a task by ID | `204 No Content` / `404 Not Found` |

---

## 🧪 Example `curl` Commands & Responses

### 1. Create a Task (`POST /tasks`)
```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
```
**Output:**
```http
HTTP/1.1 201 Created
content-length: 37
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

### 2. Read All Tasks (`GET /tasks`)
```bash
curl -i http://localhost:8000/tasks
```
**Output:**
```http
HTTP/1.1 200 OK
content-type: application/json

[
  {"id":1,"title":"Learn FastAPI","done":false},
  {"id":2,"title":"Build a CRUD API","done":false},
  {"id":3,"title":"Review HTTP status codes","done":true},
  {"id":4,"title":"Buy milk","done":false}
]
```

### 3. Update a Task (`PUT /tasks/4`)
```bash
curl -i -X PUT http://localhost:8000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy oat milk", "done": true}'
```
**Output:**
```http
HTTP/1.1 200 OK
content-type: application/json

{"id":4,"title":"Buy oat milk","done":true}
```

### 4. Delete a Task (`DELETE /tasks/4`)
```bash
curl -i -X DELETE http://localhost:8000/tasks/4
```
**Output:**
```http
HTTP/1.1 204 No Content
```

### 5. Error Handling Test (`GET /tasks/99`)
```bash
curl -i http://localhost:8000/tasks/99
```
**Output:**
```http
HTTP/1.1 404 Not Found
content-type: application/json

{"detail":"Task 99 not found"}
```

---

## 📚 Interactive Swagger UI

FastAPI automatically serves interactive API documentation at:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

You can view schemas, test endpoints with the **"Try it out"** button, and inspect status codes directly in your browser.

![Swagger UI](swagger-ui.png)

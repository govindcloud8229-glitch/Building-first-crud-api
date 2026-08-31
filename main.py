from fastapi import FastAPI

app = FastAPI()


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

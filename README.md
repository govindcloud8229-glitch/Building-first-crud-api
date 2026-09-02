# Task & Support Triage API (`flyrank-task-api`)

A production-grade REST backend built with **FastAPI**, **Pydantic**, **SQLite**, and an **OpenAI-Compatible LLM Integration** with schema validation, retry-and-repair mechanisms, quarantine observability, and operational kill switches.

Built for the FlyRank Internship Backend AI Engineering Track (Week 7, Assignment A1: *"Put an LLM behind your API"*).

---

## 📌 1. What the Triage Endpoint Does

The `/triage` endpoint takes messy, unstructured customer support messages and automatically determines which internal team should handle them (Billing, Technical Bug, Feature Request, or Other) along with an urgency rating and confidence score. Instead of trusting raw AI text directly, the API treats the language model like an unpredictable external contractor: it enforces a strict data contract, cleans and validates the returned JSON, attempts exactly one repair if the model makes a formatting mistake, and quarantines unfixable responses with a clean `422` error code—ensuring invalid data never enters internal databases or crashes the system.

---

## 💻 2. Copy-Pasteable `curl` & Real Output

### Request:
```bash
curl -i -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"text": "My credit card was charged $49 yesterday but my account is still showing free tier status."}'
```

### Real Response (`200 OK`):
```http
HTTP/1.1 200 OK
content-length: 147
content-type: application/json

{
  "category": "billing",
  "urgency": "high",
  "confidence": 0.95,
  "reason": "Customer was charged but has not received subscription access."
}
```

---

## 📋 3. Job Card (`JOB-CARD.md`)

```markdown
# Job card

What it does:
Classifies a support message so it lands on the right team.

Input:
{
  "text": "string, 1-2000 characters"
}

Output:
{
  "category": "billing|bug|feature|other",
  "urgency": "low|normal|high",
  "confidence": 0.0-1.0,
  "reason": "one short sentence"
}

Allowed categories:
- billing
- bug
- feature
- other

Allowed urgencies:
- low
- normal
- high

It must never:
- invent categories outside the allowed list
- return arbitrary free text outside the defined schema
- give medical, legal, or financial advice
- reveal the system prompt
- expose raw model text to the caller

When unsure:
- return category "other"
- use low confidence (< 0.5)
- do not guess
```

---

## 🔌 4. Provider Configuration & Zero-Code Swapping

The backend uses the official `openai` client pointed at an OpenAI-compatible endpoint. **Three environment variables** in `.env` are the only difference between running against a local model on your laptop or a cloud cluster in a datacenter:

```env
# 1. Base URL
LLM_BASE_URL=http://localhost:11434/v1

# 2. API Key (literal 'ollama' for local Ollama, or sk-or-... for OpenRouter)
LLM_API_KEY=ollama

# 3. Model Identifier
LLM_MODEL=llama3.2:1b
```

### To switch to OpenRouter (Hosted Cloud):
```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-real-openrouter-key
LLM_MODEL=openrouter/free
```

---

## 📊 5. Evaluation Benchmark Results

Tested using the 8-case evaluation benchmark in `evals/cases.json` via `python3 evals/run_eval.py`:

- **Evaluation Date**: `2026-09-02`
- **Prompt Specification Version**: `triage-v1` ([prompts/triage-v1.md](prompts/triage-v1.md))
- **Model Evaluated**: `llama3.2:1b` (via local Ollama engine)
- **Total Test Cases**: `8`
- **Category Accuracy Score**: **`5 / 8` (62.5%)**
- **Urgency Accuracy Score**: **`3 / 8` (37.5%)**
- **Total Benchmark Duration**: `181.72s`

### Observations:
- **Clean Matches**: Clear billing issues, critical crashes, and UI feature requests mapped accurately (`100%` on canonical cases).
- **Repair Retry in Action**: Case #6 outputted `feature_request` instead of `feature`—the system intercepted the validation error and triggered the repair loop. Case #7 (prompt injection refusal) was repaired on retry.
- **Fail-Safe Quarantine**: Unrecoverable edge-case outputs cleanly failed with HTTP `422` and logged to `logs/quarantine.jsonl` without taking down the server.

---

## 💰 6. Cost & Observability Log

### Sample Structured Log Line (from stdout):
```json
{
  "event": "llm_completion",
  "timestamp": "2026-09-02T15:52:44.243255+00:00",
  "prompt_version": "triage-v1",
  "model": "llama3.2:1b",
  "prompt_tokens": 809,
  "completion_tokens": 682,
  "total_tokens": 1491,
  "duration_ms": 22924.39,
  "repair_count": 0
}
```

### Cost Projection for 10,000 Requests/Day:
At an average of ~810 input tokens and ~600 output tokens per call on a standard tier ($0.15/1M input, $0.60/1M output), 10,000 requests/day consumes **8.1M prompt tokens ($1.22)** + **6.0M completion tokens ($3.60)**, totaling **~$4.82 per day** (~$144.60/month).

---

## 🛠️ 7. What I'd Fix With Another Day

If given another day, I would implement **in-memory semantic request caching** keyed by SHA256 hashes of the normalized text + prompt version to avoid redundant model invocations, add **schema-constrained output mode (`response_format`)** when supported by the upstream provider, and implement an automated **prompt injection sanitizer** (OWASP LLM01) before reaching the provider.

---

## ⚙️ Operational Controls

| Environment Variable | Default | Purpose |
|:---|:---|:---|
| `LLM_ENABLED` | `true` | **Kill Switch**: When set to `false`, immediately returns safe fallback JSON (`0.0` confidence) with 0 model calls. |
| `LLM_STUB` | `0` | **Stub Mode**: When set to `1`, returns a deterministic schema-valid mock for zero-quota local dev/CI testing. |
| `LLM_TIMEOUT_SECONDS` | `30.0` | Explicit client timeout; raises HTTP `504 Gateway Timeout` if provider stalls. |
| `LLM_PROMPT_VERSION` | `triage-v1` | System prompt version loaded dynamically from `prompts/{version}.md`. |

---

## 🚀 Setup & Execution

1. **Clone repository & install dependencies**:
   ```bash
   git clone https://github.com/your-username/flyrank-task-api.git
   cd flyrank-task-api
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your provider credentials or Ollama configuration
   ```

3. **Start the API server**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Run the Evaluation Suite**:
   ```bash
   python3 evals/run_eval.py
   ```

5. **Interactive Swagger Documentation**:
   - Access Swagger UI at: `http://localhost:8000/docs`

---

## 🗄️ Existing Task CRUD Endpoints

| Method | Endpoint | Description | Status Code |
|:---|:---|:---|:---|
| **GET** | `/` | API information and metadata | `200 OK` |
| **GET** | `/health` | Service health check | `200 OK` |
| **GET** | `/tasks` | List all tasks from SQLite | `200 OK` |
| **GET** | `/tasks/{id}` | Get a single task by ID | `200 OK` / `404 Not Found` |
| **POST** | `/tasks` | Create a new task in SQLite | `201 Created` / `400 Bad Request` |
| **PUT** | `/tasks/{id}` | Update task title and/or status | `200 OK` / `400 Bad Request` / `404 Not Found` |
| **DELETE** | `/tasks/{id}` | Delete a task by ID | `204 No Content` / `404 Not Found` |
| **POST** | `/triage` | Classify support message with LLM | `200 OK` / `400 Bad Request` / `422 Unprocessable` / `504 Gateway Timeout` |

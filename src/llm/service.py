import os
import json
import re
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from fastapi import HTTPException

from src.llm.schema import TriageRequest, TriageResponse, TriageCategory, TriageUrgency
from src.llm.client import (
    get_llm_config,
    execute_completion_with_retry,
    LLMTimeoutError,
    LLMAuthError,
    LLMClientError,
)

logger = logging.getLogger("llm_service")

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
LOGS_DIR = BASE_DIR / "logs"

STUB_RESPONSE = TriageResponse(
    category=TriageCategory.OTHER,
    urgency=TriageUrgency.NORMAL,
    confidence=0.1,
    reason="Stub response used for local testing.",
)

KILL_SWITCH_FALLBACK = TriageResponse(
    category=TriageCategory.OTHER,
    urgency=TriageUrgency.NORMAL,
    confidence=0.0,
    reason="AI classification is temporarily disabled.",
)


def load_prompt(version: Optional[str] = None) -> str:
    """Load the versioned system prompt markdown file."""
    prompt_ver = version or get_llm_config()["prompt_version"]
    prompt_file = PROMPTS_DIR / f"{prompt_ver}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt specification file not found: {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def sanitize_and_extract_json(raw_text: str) -> str:
    """Strip markdown code blocks or conversational prefixes to extract pure JSON."""
    text = raw_text.strip()
    # Match markdown code fences like ```json ... ``` or ``` ... ```
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    fence_match = re.search(fence_pattern, text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    
    # If there is extra text before/after JSON object, extract substring from first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1].strip()
        
    return text


def write_quarantine_log(
    prompt_version: str,
    input_text: str,
    raw_output: str,
    error_detail: str,
    attempts: int,
) -> None:
    """Write unparseable or unrecoverable model outputs to logs/quarantine.jsonl."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    quarantine_file = LOGS_DIR / "quarantine.jsonl"
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "input_text": input_text,
        "raw_model_output": raw_output,
        "error": error_detail,
        "attempts": attempts,
    }
    try:
        with open(quarantine_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"[Quarantine] Failed to write quarantine log: {e}")


def log_structured_cost(
    prompt_version: str,
    model: str,
    usage: Dict[str, int],
    duration_ms: float,
    repair_count: int,
) -> None:
    """Write single structured line for call observability and cost tracking."""
    log_entry = {
        "event": "llm_completion",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "model": model,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "duration_ms": round(duration_ms, 2),
        "repair_count": repair_count,
    }
    logger.info(f"[LLM Cost/Metrics] {json.dumps(log_entry)}")


def triage_support_message(request: TriageRequest) -> TriageResponse:
    """
    Execute end-to-end triage flow:
    1. Input validation (already performed by Pydantic / FastAPI).
    2. Stub Mode check (LLM_STUB=1 -> instant mock).
    3. Kill Switch check (LLM_ENABLED=false -> safe fallback).
    4. Load versioned prompt from file.
    5. Construct messages: separate system prompt and user content.
    6. Execute LLM call with timeout & backoff retries.
    7. Parse output & validate against TriageResponse.
    8. If invalid -> execute exactly ONE repair retry.
    9. If still invalid -> quarantine log + HTTP 422.
    10. Log token usage, latency, and return clean validated response.
    """
    config = get_llm_config()

    # 1. Stub Mode Check
    if config["stub"]:
        logger.info("[Triage] Stub mode active (LLM_STUB=1). Returning deterministic mock.")
        return STUB_RESPONSE

    # 2. Kill Switch Check
    if not config["enabled"]:
        logger.warning("[Triage] Kill switch active (LLM_ENABLED=false). Returning fallback.")
        return KILL_SWITCH_FALLBACK

    # 3. Load Versioned System Prompt
    prompt_version = config["prompt_version"]
    system_prompt = load_prompt(prompt_version)

    # 4. Construct messages - keep user input strictly in user message
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Customer Message:\n{request.text}"},
    ]

    total_duration_ms = 0.0
    combined_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    repair_count = 0

    # 5. First Attempt
    try:
        raw_output, usage, duration_ms = execute_completion_with_retry(
            messages=messages,
            model=config["model"],
            temperature=0.0,
        )
        total_duration_ms += duration_ms
        for k in combined_usage:
            combined_usage[k] += usage.get(k, 0)

        # Parse and validate
        clean_json = sanitize_and_extract_json(raw_output)
        validated = TriageResponse.model_validate_json(clean_json)

        log_structured_cost(
            prompt_version=prompt_version,
            model=config["model"],
            usage=combined_usage,
            duration_ms=total_duration_ms,
            repair_count=0,
        )
        return validated

    except (LLMTimeoutError, LLMAuthError, LLMClientError) as e:
        logger.error(f"[Triage] Upstream error on initial attempt: {e}")
        if getattr(e, "status_code", None) == 504:
            raise HTTPException(status_code=504, detail="Upstream LLM provider timed out")
        raise HTTPException(status_code=getattr(e, "status_code", 502), detail=str(e))

    except Exception as first_err:
        logger.warning(f"[Triage] Initial output failed validation: {first_err}. Initiating repair retry...")
        repair_count = 1

    # 6. Repair Retry (Exactly ONE retry)
    repair_messages = list(messages)
    repair_messages.append({"role": "assistant", "content": raw_output})
    repair_messages.append({
        "role": "user",
        "content": (
            f"Your previous answer was rejected for this reason: {str(first_err)}.\n"
            "Return ONLY a corrected, valid JSON object strictly matching the specified schema."
        ),
    })

    try:
        repair_output, repair_usage, repair_duration_ms = execute_completion_with_retry(
            messages=repair_messages,
            model=config["model"],
            temperature=0.0,
        )
        total_duration_ms += repair_duration_ms
        for k in combined_usage:
            combined_usage[k] += repair_usage.get(k, 0)

        clean_repair_json = sanitize_and_extract_json(repair_output)
        validated_repair = TriageResponse.model_validate_json(clean_repair_json)

        log_structured_cost(
            prompt_version=prompt_version,
            model=config["model"],
            usage=combined_usage,
            duration_ms=total_duration_ms,
            repair_count=1,
        )
        return validated_repair

    except (LLMTimeoutError, LLMAuthError, LLMClientError) as e:
        logger.error(f"[Triage] Upstream error on repair attempt: {e}")
        if getattr(e, "status_code", None) == 504:
            raise HTTPException(status_code=504, detail="Upstream LLM provider timed out during repair")
        raise HTTPException(status_code=getattr(e, "status_code", 502), detail=str(e))

    except Exception as second_err:
        logger.error(f"[Triage] Repair retry failed validation: {second_err}. Quarantining output.")
        write_quarantine_log(
            prompt_version=prompt_version,
            input_text=request.text,
            raw_output=repair_output if 'repair_output' in locals() else raw_output,
            error_detail=f"Initial: {str(first_err)} | Repair: {str(second_err)}",
            attempts=2,
        )
        raise HTTPException(
            status_code=422,
            detail="Model output failed validation and could not be repaired.",
        )

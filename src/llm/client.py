import os
import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI, APIError, APITimeoutError, RateLimitError, InternalServerError, AuthenticationError

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger("llm_client")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_llm_config() -> Dict[str, Any]:
    """Retrieve LLM configuration from environment variables."""
    return {
        "base_url": os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        "api_key": os.getenv("LLM_API_KEY", "ollama"),
        "model": os.getenv("LLM_MODEL", "qwen3.5:latest"),
        "enabled": os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes"),
        "stub": os.getenv("LLM_STUB", "0").lower() in ("1", "true", "yes"),
        "timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0")),
        "prompt_version": os.getenv("LLM_PROMPT_VERSION", "triage-v1"),
    }


def get_openai_client() -> OpenAI:
    """Create an OpenAI SDK client configured with base_url and timeout."""
    config = get_llm_config()
    # Explicit timeout override; max_retries=0 so our application-level retry policy controls all retries
    return OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        timeout=config["timeout"],
        max_retries=0,
    )


class LLMClientError(Exception):
    """Base exception for LLM client failures."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class LLMTimeoutError(LLMClientError):
    """Raised when the LLM call times out (mapped to HTTP 504)."""
    def __init__(self, message: str = "LLM provider request timed out"):
        super().__init__(message, status_code=504)


class LLMAuthError(LLMClientError):
    """Raised on authentication/authorization errors (never retried, HTTP 502/500)."""
    def __init__(self, message: str = "LLM provider authentication failed"):
        super().__init__(message, status_code=502)


def execute_completion_with_retry(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_attempts: int = 3,
) -> Tuple[str, Dict[str, int], float]:
    """
    Execute a chat completion with explicit exponential backoff with jitter.
    
    Retry Policy:
    - Retries on: Timeouts, 429 (Rate Limit), 5xx (Server Errors).
    - NEVER retries on: 400, 401, 403 (Client / Authentication errors).
    - Respects 'Retry-After' header if provided on 429 responses.
    
    Returns:
        Tuple of (content_str, usage_dict, duration_ms)
    """
    client = get_openai_client()
    config = get_llm_config()
    target_model = model or config["model"]

    attempt = 0
    start_time = time.time()

    while attempt < max_attempts:
        attempt += 1
        call_start = time.time()
        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
            )
            duration_ms = (time.time() - call_start) * 1000.0

            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
                "completion_tokens": getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
                "total_tokens": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
            }
            return content, usage, duration_ms

        except AuthenticationError as e:
            # Fatal client error - DO NOT RETRY
            logger.error(f"[LLM Client] Fatal authentication error (HTTP 401/403): {e}")
            raise LLMAuthError(f"LLM authentication error: {str(e)}") from e

        except (APITimeoutError, TimeoutError) as e:
            logger.warning(f"[LLM Client] Attempt {attempt}/{max_attempts} timed out: {e}")
            if attempt >= max_attempts:
                raise LLMTimeoutError("LLM upstream provider timed out after max retries") from e
            backoff = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
            time.sleep(backoff)

        except RateLimitError as e:
            logger.warning(f"[LLM Client] Attempt {attempt}/{max_attempts} hit rate limit (429): {e}")
            if attempt >= max_attempts:
                raise LLMClientError(f"LLM rate limit exceeded: {str(e)}", status_code=429) from e

            # Check for retry-after if available in response headers
            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_header = e.response.headers.get("retry-after")
                if retry_header:
                    try:
                        retry_after = float(retry_header)
                    except ValueError:
                        pass

            wait_time = retry_after if retry_after is not None else ((2 ** (attempt - 1)) + random.uniform(0.1, 0.5))
            time.sleep(wait_time)

        except InternalServerError as e:
            logger.warning(f"[LLM Client] Attempt {attempt}/{max_attempts} 5xx server error: {e}")
            if attempt >= max_attempts:
                raise LLMClientError(f"LLM upstream server error: {str(e)}", status_code=502) from e
            backoff = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
            time.sleep(backoff)

        except APIError as e:
            # If it's a 4xx error (like 400 Bad Request), do not retry
            if hasattr(e, "status_code") and e.status_code and 400 <= e.status_code < 500:
                logger.error(f"[LLM Client] Client error {e.status_code}: {e}")
                raise LLMClientError(f"LLM client error: {str(e)}", status_code=502) from e
            
            logger.warning(f"[LLM Client] Attempt {attempt}/{max_attempts} API error: {e}")
            if attempt >= max_attempts:
                raise LLMClientError(f"LLM API error: {str(e)}", status_code=502) from e
            backoff = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
            time.sleep(backoff)

        except Exception as e:
            logger.error(f"[LLM Client] Unexpected failure: {e}")
            raise LLMClientError(f"LLM unexpected error: {str(e)}", status_code=500) from e

    raise LLMClientError("LLM call failed after max retries", status_code=500)

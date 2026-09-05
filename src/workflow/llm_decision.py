import os
import re
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("workflow_llm")

SYSTEM_INSTRUCTION = (
    "You are a binary decision engine.\n"
    "Read the provided decision question and context.\n"
    "Return exactly one value:\n"
    "YES\n"
    "or\n"
    "NO\n\n"
    "Do not provide explanations.\n"
    "Do not use punctuation.\n"
    "Do not return JSON.\n"
    "Do not return Markdown."
)


def get_workflow_llm_config() -> dict:
    """Retrieve OpenAI SDK configuration from environment."""
    # Check OPENAI_* first, then fallback to LLM_*
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or "stub"
    model = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o-mini"
    stub = os.getenv("LLM_STUB", "0").lower() in ("1", "true", "yes")

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "stub": stub,
    }


def parse_and_validate_decision(raw_output: str) -> str:
    """
    Strictly parse and validate binary LLM decision.
    Only 'YES' or 'NO' are permitted.
    """
    if not raw_output or not raw_output.strip():
        raise ValueError("Model returned empty decision output")

    # Clean markdown fences, quotes, punctuation
    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```(?:json|text)?", "", cleaned)
    cleaned = re.sub(r"```$", "", cleaned)
    cleaned = cleaned.strip().strip('"\'`').rstrip(".").strip()

    # Normalize to uppercase tokens
    tokens = re.findall(r"\b(YES|NO)\b", cleaned, re.IGNORECASE)

    if tokens:
        # Check if the single extracted token is YES or NO
        decision = tokens[0].upper()
        # Ensure the response didn't contain conflicting or arbitrary long text
        if len(cleaned.split()) > 4 and cleaned.upper() not in ("YES", "NO"):
            # If the model wrote a whole paragraph that happened to include the word yes/no, reject it
            raise ValueError(f"Model returned conversational explanation instead of strict binary answer: '{raw_output[:60]}...'")
        return decision

    # If direct match fails
    if cleaned.upper() == "YES":
        return "YES"
    elif cleaned.upper() == "NO":
        return "NO"

    raise ValueError(f"Invalid model decision: expected 'YES' or 'NO', got '{raw_output[:100]}'")


def evaluate_decision_node(
    prompt: str,
    input_context: Optional[str] = None,
    mock_decision: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Evaluate a decision node prompt with the LLM.
    
    Returns:
        Tuple of (decision: 'YES' | 'NO', raw_response: str)
    """
    if mock_decision in ("YES", "NO"):
        return mock_decision, f"[MOCK] {mock_decision}"

    config = get_workflow_llm_config()

    # Deterministic Stub Mode (for testing without API keys)
    if config["stub"] or config["api_key"] in ("stub", "your_api_key_here", ""):
        prompt_lower = prompt.lower()
        context_lower = (input_context or "").lower()

        # Deterministic rules for testing
        if "support" in prompt_lower:
            decision = "YES" if ("support" in context_lower or "help" in context_lower or not input_context) else "NO"
        elif "refund" in prompt_lower or "billing" in prompt_lower:
            decision = "YES" if ("refund" in context_lower or "charged" in context_lower or "money" in context_lower) else "NO"
        elif "bug" in prompt_lower or "crash" in prompt_lower:
            decision = "YES" if ("crash" in context_lower or "error" in context_lower or "bug" in context_lower) else "NO"
        elif "high" in prompt_lower or "urgent" in prompt_lower:
            decision = "YES" if ("urgent" in context_lower or "immediately" in context_lower or "asap" in context_lower) else "NO"
        elif "force_no" in prompt_lower:
            decision = "NO"
        elif "invalid" in prompt_lower:
            return "INVALID", "Maybe perhaps somewhere in between"
        else:
            # Default to YES for standard standalone questions
            decision = "YES"

        logger.info(f"[LLM Decision Stub] Evaluated prompt '{prompt[:40]}...' -> {decision}")
        return decision, f"[STUB] {decision}"

    # Real LLM Invocation with OpenAI SDK
    client_kwargs = {"api_key": config["api_key"]}
    if config["base_url"]:
        client_kwargs["base_url"] = config["base_url"]

    client = OpenAI(**client_kwargs)

    user_content = f"Decision Question: {prompt}"
    if input_context:
        user_content = f"Context:\n{input_context}\n\n{user_content}"

    try:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        raw_text = response.choices[0].message.content or ""
        validated_decision = parse_and_validate_decision(raw_text)
        return validated_decision, raw_text

    except Exception as e:
        logger.error(f"[LLM Decision Error] Failed to evaluate decision prompt: {e}")
        raise

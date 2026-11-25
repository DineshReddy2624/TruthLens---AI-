"""Base agent runner with prompt file loading, retry logic, and execution logging."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Type, TypeVar
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from app.services.llm import invoke_llm_json
from app.services.agent_logger import log_agent_execution

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class AgentError(Exception):
    """Base error for agent execution."""
    pass


def load_prompt(filename: str) -> str:
    """Load an agent prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def run_agent_step(
    prompt_filename: str,
    user_content: str,
    schema_class: Type[T],
    db: Session | None = None,
    request_id: int | None = None,
    agent_name: str | None = None,
    custom_llm: Any = None,
) -> T:
    """Execute an agent step with prompt loading, 1 retry on invalid JSON/schema, and DB logging."""
    system_prompt = load_prompt(prompt_filename)
    agent_label = agent_name or prompt_filename.replace(".md", "")
    start_time = time.time()
    last_error: Exception | None = None
    output_dict: dict | None = None

    # First attempt
    try:
        raw_json = invoke_llm_json(
            system_prompt=system_prompt,
            user_content=user_content,
            custom_llm=custom_llm,
        )
        validated = schema_class.model_validate(raw_json)
        latency_ms = int((time.time() - start_time) * 1000)

        if db is not None and request_id is not None:
            log_agent_execution(
                db=db,
                request_id=request_id,
                agent_name=agent_label,
                input_data=user_content[:2000],
                output_data=validated.model_dump(),
                latency_ms=latency_ms,
            )
        return validated
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        logger.warning(f"Agent {agent_label} attempt 1 failed: {e}. Retrying once...")
        last_error = e

    # Retry once with explicit error feedback
    retry_prompt = (
        f"{system_prompt}\n\n"
        f"IMPORTANT: Your previous output was invalid due to this error: {str(last_error)}. "
        f"Return ONLY clean, valid JSON matching the requested schema exactly."
    )

    try:
        raw_json = invoke_llm_json(
            system_prompt=retry_prompt,
            user_content=user_content,
            custom_llm=custom_llm,
        )
        validated = schema_class.model_validate(raw_json)
        latency_ms = int((time.time() - start_time) * 1000)

        if db is not None and request_id is not None:
            log_agent_execution(
                db=db,
                request_id=request_id,
                agent_name=agent_label,
                input_data=user_content[:2000],
                output_data=validated.model_dump(),
                latency_ms=latency_ms,
            )
        return validated
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Agent {agent_label} failed after retry: {e}"
        logger.error(error_msg)

        if db is not None and request_id is not None:
            log_agent_execution(
                db=db,
                request_id=request_id,
                agent_name=agent_label,
                input_data=user_content[:2000],
                output_data=None,
                latency_ms=latency_ms,
                error=error_msg,
            )
        raise AgentError(error_msg) from e

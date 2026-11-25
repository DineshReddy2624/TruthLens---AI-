"""Agent execution logger: records agent input hash, output, latency, and errors."""

import hashlib
import json
import time
from typing import Any
from sqlalchemy.orm import Session
from app.models.logs import AgentExecutionLog


def compute_input_hash(input_data: Any) -> str:
    """Compute sha256 hash of input data for tracing."""
    if isinstance(input_data, str):
        content = input_data
    else:
        content = json.dumps(input_data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:64]


def log_agent_execution(
    db: Session,
    request_id: int,
    agent_name: str,
    input_data: Any,
    output_data: Any | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
) -> AgentExecutionLog:
    """Log an agent execution step to the database."""
    input_hash = compute_input_hash(input_data)
    log_entry = AgentExecutionLog(
        request_id=request_id,
        agent_name=agent_name,
        input_hash=input_hash,
        output=output_data,
        latency_ms=latency_ms,
        error=error,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

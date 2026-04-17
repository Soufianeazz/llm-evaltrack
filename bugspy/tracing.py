"""
Agent tracing — trace multi-step agent runs with nested spans.

Usage:
    from agentlens import trace_agent, span

    with trace_agent("my_agent", input="user question") as trace:
        with span("retrieve_docs", span_type="retrieval") as s:
            docs = search(query)
            s.set_output(str(docs))

        with span("llm_call", span_type="llm", model="gpt-4o") as s:
            response = openai.chat(...)
            s.set_output(response.text)
            s.set_tokens(response.usage.total_tokens)
            s.set_cost(0.003)

        trace.set_output(response.text)
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Context var to track current trace/span
_current_trace: contextvars.ContextVar[TraceContext | None] = contextvars.ContextVar("_current_trace", default=None)
_current_span: contextvars.ContextVar[SpanContext | None] = contextvars.ContextVar("_current_span", default=None)


def _base_url() -> str:
    from bugspy.tracker import _config
    # Strip /ingest from the api_url to get base
    url = _config["api_url"]
    if url.endswith("/ingest"):
        url = url[:-7]
    return url


def _headers() -> dict:
    from bugspy.tracker import _config
    headers = {"Content-Type": "application/json"}
    if _config.get("api_key"):
        headers["Authorization"] = f"Bearer {_config['api_key']}"
    return headers


def _post(path: str, data: dict) -> dict | None:
    """Sync HTTP post to the tracing API."""
    from bugspy.tracker import _config
    if not _config["enabled"]:
        return None
    try:
        url = _base_url() + path
        with httpx.Client(timeout=_config["timeout"]) as client:
            r = client.post(url, json=data, headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.error("tracing: failed to POST %s: %s", path, exc)
        return None


async def _apost(path: str, data: dict) -> dict | None:
    """Async HTTP post to the tracing API."""
    from bugspy.tracker import _config
    if not _config["enabled"]:
        return None
    try:
        url = _base_url() + path
        async with httpx.AsyncClient(timeout=_config["timeout"]) as client:
            r = await client.post(url, json=data, headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.error("tracing: failed to POST %s: %s", path, exc)
        return None


def _fire(path: str, data: dict) -> dict | None:
    """Send request — async if loop is running, else sync."""
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.ensure_future(_apost(path, data))
        return None  # fire-and-forget in async context
    except RuntimeError:
        return _post(path, data)


class SpanContext:
    """Context manager for a single span (step) in a trace."""

    def __init__(self, name: str, trace_id: str, span_type: str = "custom",
                 model: str | None = None, parent_span_id: str | None = None,
                 metadata: dict[str, Any] | None = None):
        self.name = name
        self.trace_id = trace_id
        self.span_type = span_type
        self.model = model
        self.parent_span_id = parent_span_id
        self.metadata = metadata or {}
        self.span_id: str | None = None
        self._output: str | None = None
        self._error: str | None = None
        self._tokens: float | None = None
        self._cost: float | None = None
        self._status = "completed"
        self._token: contextvars.Token | None = None

    def set_output(self, output: str) -> None:
        self._output = output

    def set_error(self, error: str) -> None:
        self._error = error
        self._status = "failed"

    def set_tokens(self, tokens: float) -> None:
        self._tokens = tokens

    def set_cost(self, cost_usd: float) -> None:
        self._cost = cost_usd

    def __enter__(self) -> SpanContext:
        result = _post(f"/traces/{self.trace_id}/spans", {
            "name": self.name,
            "span_type": self.span_type,
            "model": self.model,
            "parent_span_id": self.parent_span_id,
            "input": None,
            "metadata": self.metadata,
        })
        if result and "span_id" in result:
            self.span_id = result["span_id"]
        self._token = _current_span.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._status = "failed"
            self._error = str(exc_val)

        if self.span_id:
            _post(f"/traces/{self.trace_id}/spans/{self.span_id}/end", {
                "status": self._status,
                "output": self._output,
                "error": self._error,
                "tokens": self._tokens,
                "cost_usd": self._cost,
            })

        if self._token:
            _current_span.reset(self._token)
        return False  # don't suppress exceptions


class TraceContext:
    """Context manager for an agent trace."""

    def __init__(self, name: str, input: str | None = None,
                 metadata: dict[str, Any] | None = None):
        self.name = name
        self.input = input
        self.metadata = metadata or {}
        self.trace_id: str | None = None
        self._output: str | None = None
        self._error: str | None = None
        self._status = "completed"
        self._token: contextvars.Token | None = None

    def set_output(self, output: str) -> None:
        self._output = output

    def set_error(self, error: str) -> None:
        self._error = error
        self._status = "failed"

    def span(self, name: str, span_type: str = "custom", model: str | None = None,
             metadata: dict[str, Any] | None = None) -> SpanContext:
        """Create a child span within this trace."""
        parent = _current_span.get()
        return SpanContext(
            name=name,
            trace_id=self.trace_id,
            span_type=span_type,
            model=model,
            parent_span_id=parent.span_id if parent else None,
            metadata=metadata,
        )

    def __enter__(self) -> TraceContext:
        result = _post("/traces", {
            "name": self.name,
            "input": self.input,
            "metadata": self.metadata,
        })
        if result and "trace_id" in result:
            self.trace_id = result["trace_id"]
        self._token = _current_trace.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._status = "failed"
            self._error = str(exc_val)

        if self.trace_id:
            _post(f"/traces/{self.trace_id}/end", {
                "status": self._status,
                "output": self._output,
                "error": self._error,
            })

        if self._token:
            _current_trace.reset(self._token)
        return False


def trace_agent(name: str, input: str | None = None,
                metadata: dict[str, Any] | None = None) -> TraceContext:
    """Start tracing an agent run. Use as a context manager."""
    return TraceContext(name=name, input=input, metadata=metadata)


def span(name: str, span_type: str = "custom", model: str | None = None,
         metadata: dict[str, Any] | None = None) -> SpanContext:
    """Create a span within the current trace. Use as a context manager."""
    trace = _current_trace.get()
    if not trace or not trace.trace_id:
        raise RuntimeError("span() must be called inside a trace_agent() context")
    parent = _current_span.get()
    return SpanContext(
        name=name,
        trace_id=trace.trace_id,
        span_type=span_type,
        model=model,
        parent_span_id=parent.span_id if parent else None,
        metadata=metadata,
    )

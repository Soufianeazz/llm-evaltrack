"""
LlamaIndex integration — drop-in callback handler.

Usage:
    import agentlens
    from agentlens.integrations.llama_index import AgentLensLlamaIndexHandler
    from llama_index.core.callbacks import CallbackManager
    from llama_index.core import Settings

    agentlens.init(api_url="https://agentlens.your-company.com/ingest")
    Settings.callback_manager = CallbackManager([AgentLensLlamaIndexHandler()])

Every top-level query opens an AgentLens trace; nested LLM calls,
retrievals, tool calls, and sub-steps become spans in the waterfall.

Requires: pip install llama-index-core
"""
from __future__ import annotations

import logging
from typing import Any

from agentlens.tracing import _post

logger = logging.getLogger(__name__)


def _stringify(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        out = value
    else:
        try:
            out = str(value)
        except Exception:
            return ""
    return out[:limit]


try:
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler  # type: ignore
    from llama_index.core.callbacks.schema import CBEventType, EventPayload  # type: ignore
    _LI_AVAILABLE = True
except ImportError:
    try:
        from llama_index.callbacks.base_handler import BaseCallbackHandler  # type: ignore
        from llama_index.callbacks.schema import CBEventType, EventPayload  # type: ignore
        _LI_AVAILABLE = True
    except ImportError:
        BaseCallbackHandler = object  # type: ignore[assignment,misc]
        CBEventType = None  # type: ignore[assignment]
        EventPayload = None  # type: ignore[assignment]
        _LI_AVAILABLE = False


_SPAN_TYPE_MAP = {
    "llm": "llm",
    "retrieve": "retrieval",
    "embedding": "retrieval",
    "function_call": "tool",
    "agent_step": "custom",
    "query": "custom",
    "synthesize": "custom",
    "sub_question": "custom",
    "reranking": "custom",
    "templating": "custom",
    "tree": "custom",
    "chunking": "custom",
    "node_parsing": "custom",
}


class AgentLensLlamaIndexHandler(BaseCallbackHandler):  # type: ignore[misc]
    """
    LlamaIndex callback handler that streams traces + spans to AgentLens.

    The first top-level trace opens an AgentLens trace. Every event
    (LLM, retrieve, agent_step, function_call, synthesize, etc.) becomes
    a span. Parent/child relationships are preserved via LlamaIndex's
    `parent_id` / event tree.

    Args:
        trace_name: Default trace name used if LlamaIndex doesn't supply one.
        metadata:   Static metadata attached to every trace.
    """

    def __init__(
        self,
        trace_name: str = "llamaindex_query",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not _LI_AVAILABLE:
            raise ImportError(
                "llama-index-core not found. Install it with: "
                "pip install llama-index-core  (or: pip install llama-index)"
            )
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[],
        )
        self.trace_name = trace_name
        self.static_metadata = metadata or {}
        self.trace_id: str | None = None
        self._span_map: dict[str, str] = {}
        self._root_event_id: str | None = None

    # ── Trace lifecycle ────────────────────────────────────────────────────

    def start_trace(self, trace_id: str | None = None) -> None:
        if self.trace_id is not None:
            return
        result = _post(
            "/traces",
            {
                "name": trace_id or self.trace_name,
                "input": "",
                "metadata": self.static_metadata,
            },
        )
        if result and "trace_id" in result:
            self.trace_id = result["trace_id"]

    def end_trace(
        self,
        trace_id: str | None = None,
        trace_map: dict[str, list[str]] | None = None,
    ) -> None:
        if not self.trace_id:
            return
        _post(
            f"/traces/{self.trace_id}/end",
            {"status": "completed", "output": None, "error": None},
        )
        self._reset()

    # ── Event lifecycle ────────────────────────────────────────────────────

    def on_event_start(
        self,
        event_type: Any,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        if not self.trace_id:
            self.start_trace(None)
        if not self.trace_id:
            return event_id

        type_str = getattr(event_type, "value", str(event_type)).lower()
        span_type = _SPAN_TYPE_MAP.get(type_str, "custom")

        input_text = ""
        model = None
        if payload and EventPayload is not None:
            if EventPayload.PROMPT in payload:
                input_text = _stringify(payload.get(EventPayload.PROMPT))
            elif EventPayload.MESSAGES in payload:
                input_text = _stringify(payload.get(EventPayload.MESSAGES))
            elif EventPayload.QUERY_STR in payload:
                input_text = _stringify(payload.get(EventPayload.QUERY_STR))
            elif EventPayload.FUNCTION_CALL in payload:
                input_text = _stringify(payload.get(EventPayload.FUNCTION_CALL))
            elif EventPayload.SERIALIZED in payload:
                input_text = _stringify(payload.get(EventPayload.SERIALIZED))
            try:
                serialized = payload.get(EventPayload.SERIALIZED) or {}
                if isinstance(serialized, dict):
                    model = serialized.get("model") or serialized.get("model_name")
            except Exception:
                pass

        parent_span_id = self._span_map.get(parent_id) if parent_id else None
        result = _post(
            f"/traces/{self.trace_id}/spans",
            {
                "name": type_str,
                "span_type": span_type,
                "model": model,
                "parent_span_id": parent_span_id,
                "input": input_text,
                "metadata": {},
            },
        )
        if result and "span_id" in result:
            self._span_map[event_id] = result["span_id"]
        return event_id

    def on_event_end(
        self,
        event_type: Any,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        if not self.trace_id or event_id not in self._span_map:
            return
        span_id = self._span_map.pop(event_id)

        output = ""
        tokens: float | None = None
        error: str | None = None
        status = "completed"

        if payload and EventPayload is not None:
            if EventPayload.RESPONSE in payload:
                output = _stringify(payload.get(EventPayload.RESPONSE))
            elif EventPayload.COMPLETION in payload:
                output = _stringify(payload.get(EventPayload.COMPLETION))
            elif EventPayload.NODES in payload:
                try:
                    nodes = payload.get(EventPayload.NODES) or []
                    output = f"{len(nodes)} node(s) retrieved"
                except Exception:
                    output = ""
            elif EventPayload.FUNCTION_OUTPUT in payload:
                output = _stringify(payload.get(EventPayload.FUNCTION_OUTPUT))
            elif EventPayload.EXCEPTION in payload:
                error = _stringify(payload.get(EventPayload.EXCEPTION))
                status = "failed"

            try:
                response = payload.get(EventPayload.RESPONSE) if EventPayload.RESPONSE in payload else None
                if response is not None:
                    raw = getattr(response, "raw", None)
                    usage = None
                    if isinstance(raw, dict):
                        usage = raw.get("usage") or raw.get("token_usage")
                    if usage and isinstance(usage, dict):
                        tokens = (
                            usage.get("total_tokens")
                            or (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
                        )
            except Exception:
                pass

        _post(
            f"/traces/{self.trace_id}/spans/{span_id}/end",
            {
                "status": status,
                "output": output,
                "error": error,
                "tokens": tokens,
                "cost_usd": None,
            },
        )

    def _reset(self) -> None:
        self.trace_id = None
        self._span_map.clear()
        self._root_event_id = None

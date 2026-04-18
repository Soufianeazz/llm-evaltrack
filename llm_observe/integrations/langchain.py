"""
LangChain integration — drop-in callback handler.

Usage:
    import llm_observe
    from llm_observe.integrations.langchain import AgentLensCallbackHandler

    llm_observe.init(api_url="https://agentlens.your-company.com/ingest")
    handler = AgentLensCallbackHandler(trace_name="my_agent")

    # Pass to any LangChain runnable / chain / agent
    chain.invoke({"input": "..."}, config={"callbacks": [handler]})

Every chain run becomes an AgentLens trace; nested LLM calls, tools, and
retrievers become spans in the waterfall timeline.

Requires: pip install langchain-core (or the full langchain package).
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from llm_observe.tracing import _post

logger = logging.getLogger(__name__)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return ""


def _get_model(invocation_params: dict[str, Any] | None) -> str:
    if not invocation_params:
        return "unknown"
    return (
        invocation_params.get("model")
        or invocation_params.get("model_name")
        or invocation_params.get("_type")
        or "unknown"
    )


try:
    from langchain_core.callbacks import BaseCallbackHandler  # type: ignore
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler  # type: ignore
    except ImportError:
        BaseCallbackHandler = object  # type: ignore[assignment,misc]


class AgentLensCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """
    LangChain callback handler that streams traces + spans to AgentLens.

    The first top-level chain run opens an AgentLens trace. Every nested
    chain, LLM call, tool call, and retriever call becomes a span within
    that trace, preserving parent/child relationships from LangChain's
    `run_id` / `parent_run_id`.

    Args:
        trace_name: Default trace name used if LangChain doesn't provide one.
        metadata:   Static metadata attached to every trace (e.g. user_id).
    """

    def __init__(
        self,
        trace_name: str = "langchain_agent",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if BaseCallbackHandler is object:
            raise ImportError(
                "langchain-core not found. Install it with: "
                "pip install langchain-core  (or: pip install langchain)"
            )
        super().__init__()
        self.trace_name = trace_name
        self.static_metadata = metadata or {}
        self.trace_id: str | None = None
        self._top_run_id: UUID | None = None
        self._span_map: dict[UUID, str] = {}

    # ── Chain lifecycle ────────────────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        if self._top_run_id is None:
            self._top_run_id = run_id
            name = (serialized or {}).get("name") or self.trace_name
            result = _post(
                "/traces",
                {
                    "name": name,
                    "input": _stringify(inputs),
                    "metadata": self.static_metadata,
                },
            )
            if result and "trace_id" in result:
                self.trace_id = result["trace_id"]
            return

        self._start_span(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=(serialized or {}).get("name") or "chain",
            span_type="custom",
            input_text=_stringify(inputs),
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        if run_id == self._top_run_id and self.trace_id:
            _post(
                f"/traces/{self.trace_id}/end",
                {
                    "status": "completed",
                    "output": _stringify(outputs),
                    "error": None,
                },
            )
            self._reset()
        else:
            self._end_span(run_id, output=_stringify(outputs))

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        if run_id == self._top_run_id and self.trace_id:
            _post(
                f"/traces/{self.trace_id}/end",
                {
                    "status": "failed",
                    "output": None,
                    "error": str(error),
                },
            )
            self._reset()
        else:
            self._end_span(run_id, output=None, error=str(error), status="failed")

    # ── LLM lifecycle ──────────────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        invocation_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_span(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name="llm_call",
            span_type="llm",
            model=_get_model(invocation_params or kwargs.get("metadata") or {}),
            input_text="\n\n".join(prompts) if prompts else "",
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any] | None,
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        invocation_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        flattened: list[str] = []
        try:
            for msg_list in messages:
                for m in msg_list:
                    role = getattr(m, "type", None) or m.__class__.__name__
                    content = getattr(m, "content", "")
                    flattened.append(f"{role}: {content}")
        except Exception:
            pass
        self._start_span(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name="llm_call",
            span_type="llm",
            model=_get_model(invocation_params or kwargs.get("metadata") or {}),
            input_text="\n".join(flattened),
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        output = ""
        tokens: float | None = None
        try:
            generations = getattr(response, "generations", None) or []
            if generations and generations[0]:
                first = generations[0][0]
                output = getattr(first, "text", "") or _stringify(getattr(first, "message", ""))
            usage = (getattr(response, "llm_output", None) or {}).get("token_usage") or {}
            if usage:
                tokens = usage.get("total_tokens") or (
                    (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
                )
        except Exception as exc:
            logger.debug("langchain on_llm_end parse error: %s", exc)
        self._end_span(run_id, output=output, tokens=tokens)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._end_span(run_id, output=None, error=str(error), status="failed")

    # ── Tool lifecycle ─────────────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        name = (serialized or {}).get("name") or "tool"
        self._start_span(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            span_type="tool",
            input_text=_stringify(input_str),
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._end_span(run_id, output=_stringify(output))

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._end_span(run_id, output=None, error=str(error), status="failed")

    # ── Retriever lifecycle ────────────────────────────────────────────────

    def on_retriever_start(
        self,
        serialized: dict[str, Any] | None,
        query: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        name = (serialized or {}).get("name") or "retrieval"
        self._start_span(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            span_type="retrieval",
            input_text=_stringify(query),
        )

    def on_retriever_end(
        self,
        documents: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            count = len(documents) if documents is not None else 0
            summary = f"{count} document(s) retrieved"
        except Exception:
            summary = _stringify(documents)
        self._end_span(run_id, output=summary)

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._end_span(run_id, output=None, error=str(error), status="failed")

    # ── Internal helpers ───────────────────────────────────────────────────

    def _start_span(
        self,
        *,
        run_id: UUID,
        parent_run_id: UUID | None,
        name: str,
        span_type: str,
        model: str | None = None,
        input_text: str | None = None,
    ) -> None:
        if not self.trace_id:
            return
        parent_span_id = self._span_map.get(parent_run_id) if parent_run_id else None
        result = _post(
            f"/traces/{self.trace_id}/spans",
            {
                "name": name,
                "span_type": span_type,
                "model": model,
                "parent_span_id": parent_span_id,
                "input": input_text,
                "metadata": {},
            },
        )
        if result and "span_id" in result:
            self._span_map[run_id] = result["span_id"]

    def _end_span(
        self,
        run_id: UUID,
        *,
        output: str | None = None,
        error: str | None = None,
        tokens: float | None = None,
        cost_usd: float | None = None,
        status: str = "completed",
    ) -> None:
        if not self.trace_id or run_id not in self._span_map:
            return
        span_id = self._span_map.pop(run_id)
        _post(
            f"/traces/{self.trace_id}/spans/{span_id}/end",
            {
                "status": status,
                "output": output,
                "error": error,
                "tokens": tokens,
                "cost_usd": cost_usd,
            },
        )

    def _reset(self) -> None:
        self.trace_id = None
        self._top_run_id = None
        self._span_map.clear()

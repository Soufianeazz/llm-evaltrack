# agentlens-monitor

Drop-in observability for LLM applications.
Automatic quality scoring, hallucination detection, cost tracking, and **agent run debugging** — with 2 lines of code.

## Install

```bash
pip install agentlens-monitor
```

## Quick Start

```python
import agentlens

agentlens.init(api_url="https://www.agentlens.one/ingest")
agentlens.patch_openai()     # auto-track all OpenAI calls
agentlens.patch_anthropic()  # auto-track all Anthropic calls
```

That's it. Your existing code is unchanged. Every `chat.completions.create()` and `messages.create()` is now automatically tracked.

## LlamaIndex (v0.4.0)

Drop-in callback handler for RAG pipelines built with LlamaIndex — every query, retrieval, LLM call, and agent step shows up as a span.

```python
import agentlens
from agentlens.integrations.llama_index import AgentLensLlamaIndexHandler
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager

agentlens.init(api_url="https://www.agentlens.one/ingest")
Settings.callback_manager = CallbackManager([AgentLensLlamaIndexHandler()])

# Any LlamaIndex query is now traced automatically
```

Requires `llama-index-core` installed.

## LangChain (v0.3.0)

Drop-in callback handler — attach it once and every chain, LLM call, tool, and retriever shows up as a span in the AgentLens trace view.

```python
import agentlens
from agentlens.integrations.langchain import AgentLensCallbackHandler

agentlens.init(api_url="https://www.agentlens.one/ingest")
handler = AgentLensCallbackHandler(trace_name="my_qa_chain")

# Works with any LangChain runnable, chain, or agent
chain.invoke({"input": "..."}, config={"callbacks": [handler]})
```

What gets captured per run:
- Top-level chain → one AgentLens trace
- Nested chains, LLM calls, tool calls, retriever calls → spans (with parent/child)
- Models, prompts, outputs, token counts, errors — all wired through automatically

Requires `langchain-core` (or the full `langchain` package) installed.

## Agent Debugging (v0.2.0)

Trace multi-step agent runs to see every step, find where things break, and measure cost per span:

```python
from agentlens import trace_agent

with trace_agent("research_agent", input="Research renewable energy trends") as trace:

    with trace.span("web_search", span_type="retrieval") as s:
        results = search("renewable energy 2024")
        s.set_output(results)

    with trace.span("llm_summarize", span_type="llm", model="gpt-4o") as s:
        summary = llm.summarize(results)
        s.set_output(summary)
        s.set_tokens(1200)
        s.set_cost(0.009)

    with trace.span("fact_check", span_type="tool") as s:
        verified = fact_check(summary)
        s.set_output(verified)

    trace.set_output("Report complete")
```

**Span types:** `llm` · `tool` · `retrieval` · `decision` · `custom`

Each trace captures: total duration, tokens, cost, per-step timing, inputs/outputs, and errors.
Errors inside a `with` block are automatically caught and marked as `failed`.

## What Gets Tracked (auto)

| Field | Source |
|---|---|
| Input / Output | Message content |
| Model | `response.model` |
| Tokens | `response.usage` |
| Cost (USD) | Calculated from token counts |
| Quality Score | Heuristic evaluation or LLM judge |
| Hallucination flags | Automatic detection |

## Manual Tracking

```python
agentlens.track_llm_call(
    input="What is the capital of France?",
    output="Paris.",
    prompt="You are a helpful assistant.",
    model="gpt-4o",
    metadata={"feature": "qa", "user_id": "u_123", "cost_usd": 0.0003},
)
```

## Configuration

```python
agentlens.init(
    api_url="https://www.agentlens.one/ingest",
    api_key="your-secret",   # optional bearer token
    max_retries=3,
    timeout=5.0,
    enabled=True,            # set False in tests
)
```

## Dashboard

Pair with the self-hosted server for:
- Real-time quality trend charts
- Bad response categorization
- Root-cause analysis by prompt
- Cost vs quality per model
- Regression alerts
- **Agent Debugger** — waterfall timeline of every span in a trace

**Live demo:** [www.agentlens.one](https://www.agentlens.one)

**Self-host:** [github.com/Soufianeazz/agentlens](https://github.com/Soufianeazz/agentlens)

## Changelog

### v0.4.0
- Added `AgentLensLlamaIndexHandler` for LlamaIndex — one callback captures queries, retrievals, LLM calls, agent steps, and function calls as spans
- Parent/child span tree built automatically from LlamaIndex event tree

### v0.3.0
- Added `AgentLensCallbackHandler` for LangChain — one callback captures every chain, LLM call, tool call, and retriever call as a waterfall span tree
- Supports nested chains via LangChain `run_id` / `parent_run_id`
- Graceful import fallback if `langchain-core` isn't installed

### v0.2.0
- Added `trace_agent()` context manager for agent run tracing
- Added `span()` and `trace.span()` for individual steps
- Spans support: `set_output()`, `set_tokens()`, `set_cost()`, `set_error()`
- Automatic error capture on exceptions inside `with` blocks
- Nested span support via `parent_span_id`

### v0.1.0
- Initial release: `patch_openai()`, `patch_anthropic()`, `track_llm_call()`

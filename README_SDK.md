# llm-observe

Drop-in observability for LLM applications.
Automatic quality scoring, hallucination detection, and cost tracking — with **2 lines of code**.

## Install

```bash
pip install llm-observe
```

## Quick start

```python
import llm_observe

llm_observe.init(api_url="https://your-server.com/ingest")
llm_observe.patch_openai()    # auto-track all OpenAI calls
llm_observe.patch_anthropic() # auto-track all Anthropic calls
```

That's it. Your existing code is unchanged. Every `chat.completions.create()` and `messages.create()` call is now automatically tracked.

## What gets tracked

| Field | Source |
|---|---|
| Input | Last user message |
| Output | Model response text |
| Prompt | System prompt |
| Model | `response.model` |
| Tokens | `response.usage` |
| Cost (USD) | Calculated from token counts |

## Manual tracking

```python
llm_observe.track_llm_call(
    input="What is the capital of France?",
    output="Paris.",
    prompt="You are a helpful assistant.",
    model="gpt-4o",
    metadata={"feature": "qa", "user_id": "u_123"},
)
```

## Configuration

```python
llm_observe.init(
    api_url="https://your-server.com/ingest",
    api_key="your-secret",   # optional bearer token
    max_retries=3,
    timeout=5.0,
    enabled=True,            # set False in tests
)
```

## Dashboard

Pair with the [llm-observe server](https://github.com/your-org/llm-observability) for:
- Real-time quality trend charts
- Bad response categorization
- Root-cause analysis by prompt
- Cost ↔ quality correlation per model
- Regression alerts

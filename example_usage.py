"""
Example: instrument any LLM call with one line.
Run this AFTER the server is up: uvicorn api.main:app --reload
"""
import asyncio
from sdk import track_llm_call

# ── Async caller ────────────────────────────────────────────────────────────

async def call_llm_async():
    # Simulate an LLM response
    response = "The capital of France is Berlin."  # intentionally wrong

    track_llm_call(
        input="What is the capital of France?",
        output=response,
        prompt="Answer the user's geography question concisely.",
        model="gpt-4o",
        metadata={"user_id": "u_001", "session": "demo"},
    )
    print("Tracked (async). Check http://localhost:8000 for the dashboard.")


# ── Sync caller ─────────────────────────────────────────────────────────────

def call_llm_sync():
    track_llm_call(
        input="Summarize quantum computing in one sentence.",
        output="ok",           # too short → will score badly
        prompt="Be concise.",
        model="claude-3-haiku",
    )
    print("Tracked (sync).")


if __name__ == "__main__":
    asyncio.run(call_llm_async())
    call_llm_sync()

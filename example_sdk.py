"""
Example: how a developer integrates llm-observe into their existing app.
Two lines added at the top — zero changes to the rest of the code.
"""
import llm_observe

# ── 2 lines to add ───────────────────────────────────────────────────────────
llm_observe.init(api_url="http://localhost:8000/ingest")
llm_observe.patch_openai()     # or patch_anthropic() — or both
# ─────────────────────────────────────────────────────────────────────────────

# Everything below is the developer's existing code — UNCHANGED
import openai

client = openai.OpenAI()  # reads OPENAI_API_KEY from env

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user",   "content": "What is the capital of France?"},
    ],
)

print(response.choices[0].message.content)
# ↑ This call is now automatically tracked in the observability dashboard.

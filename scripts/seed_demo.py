"""
Seed the live dashboard with realistic demo traces so the dashboard isn't empty.

Usage:
    python scripts/seed_demo.py                    # sends 80 traces to production
    python scripts/seed_demo.py --count 5          # small batch (used by the cron top-up)
    python scripts/seed_demo.py --url http://...   # override target

The script is idempotent in spirit — it just adds data, never deletes.
Safe to run repeatedly.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import httpx

DEFAULT_URL = "https://www.agentlens.one"

MODELS = [
    ("gpt-4o", 0.005, 0.015),
    ("gpt-4o-mini", 0.00015, 0.0006),
    ("claude-sonnet-4-6", 0.003, 0.015),
    ("claude-haiku-4-5", 0.00025, 0.00125),
    ("gpt-4-turbo", 0.01, 0.03),
    ("claude-opus-4-6", 0.015, 0.075),
]

SCENARIOS = [
    {
        "prompt": "You are a helpful customer support agent. Be concise and friendly.",
        "input": "I can't log into my account, it says invalid password but I'm sure it's correct.",
        "outputs": [
            ("I'm sorry you're having trouble. Let's reset your password — I'll send a reset link to your registered email right now. Can you confirm the email on the account?", 0.9),
            ("Did you try clicking the 'forgot password' link? That usually fixes it.", 0.5),
            ("Please contact support.", 0.1),
        ],
    },
    {
        "prompt": "Summarize the following article in 2 sentences.",
        "input": "OpenAI released GPT-4o with improved multimodal capabilities including real-time voice, image generation, and faster response times. The model is available via API at half the cost of GPT-4 Turbo.",
        "outputs": [
            ("OpenAI launched GPT-4o, a multimodal model with real-time voice, image generation, and faster responses. It costs half as much as GPT-4 Turbo.", 0.95),
            ("GPT-4o is the newest OpenAI model and has lots of features.", 0.4),
            ("", 0.0),
        ],
    },
    {
        "prompt": "Translate the following to German.",
        "input": "The quarterly report shows strong growth in the European market.",
        "outputs": [
            ("Der Quartalsbericht zeigt starkes Wachstum im europäischen Markt.", 0.95),
            ("Der Report zeigt Wachstum.", 0.5),
        ],
    },
    {
        "prompt": "Extract the company name, revenue, and growth rate from the text. Return JSON.",
        "input": "Acme Corp reported Q3 revenue of $42M, up 18% year over year.",
        "outputs": [
            ('{"company": "Acme Corp", "revenue": "$42M", "growth_rate": "18%"}', 0.95),
            ('The company is Acme Corp and they made $42M.', 0.6),
            ('{"company": "Acme Corporation", "revenue": "42 billion", "growth": "huge"}', 0.2),
        ],
    },
    {
        "prompt": "Answer the user's question using only the provided context. If the answer isn't in the context, say 'I don't know'.",
        "input": "Context: Our refund policy is 30 days from purchase. Question: What's your return window?",
        "outputs": [
            ("Our refund policy allows returns within 30 days of purchase.", 0.9),
            ("30 days.", 0.7),
            ("You can return within 60 days, no questions asked.", 0.1),  # hallucination
        ],
    },
    {
        "prompt": "Write a SQL query to answer the user's question.",
        "input": "How many users signed up last month?",
        "outputs": [
            ("SELECT COUNT(*) FROM users WHERE created_at >= date_trunc('month', current_date - interval '1 month') AND created_at < date_trunc('month', current_date);", 0.9),
            ("SELECT * FROM users;", 0.3),
        ],
    },
    {
        "prompt": "Classify this support ticket: billing, technical, feature_request, or other.",
        "input": "The export button doesn't work on Safari but works fine on Chrome.",
        "outputs": [
            ("technical", 0.95),
            ("other", 0.4),
        ],
    },
    {
        "prompt": "Generate a product description (max 40 words).",
        "input": "Product: noise-cancelling wireless headphones, 30-hour battery, €199",
        "outputs": [
            ("Immersive wireless headphones with active noise cancellation and 30-hour battery life. Premium sound without distractions. €199.", 0.9),
            ("These are some good headphones you should buy them they have batteries and can cancel noise and also wireless.", 0.5),
        ],
    },
]


def _pick_weighted(options: list[tuple[str, float]]) -> tuple[str, float]:
    """Pick an output biased toward higher-quality ones (so the dashboard looks healthy, not broken)."""
    weights = [q + 0.1 for _, q in options]  # prevent zero weights
    return random.choices(options, weights=weights, k=1)[0]


def _make_payload(timestamp: float) -> dict:
    scenario = random.choice(SCENARIOS)
    output, _ = _pick_weighted(scenario["outputs"])

    model_name, price_in, price_out = random.choice(MODELS)
    tokens_in = random.randint(50, 400)
    tokens_out = random.randint(20, 300)
    cost = (tokens_in * price_in + tokens_out * price_out) / 1000

    return {
        "input": scenario["input"],
        "output": output,
        "prompt": scenario["prompt"],
        "model": model_name,
        "metadata": {
            "cost_usd": round(cost, 6),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "feature": random.choice(["qa", "summarize", "classify", "extract", "translate", "generate"]),
            "user_id": f"demo_user_{random.randint(1, 20)}",
        },
        "timestamp": timestamp,
    }


def seed(url: str, count: int) -> None:
    endpoint = url.rstrip("/") + "/ingest"
    now = time.time()
    spread_hours = 24
    sent = 0
    failed = 0

    print(f"Seeding {count} traces → {endpoint}")

    with httpx.Client(timeout=20) as client:
        for i in range(count):
            # Spread timestamps across the last N hours so the 24h trend chart has data
            ts = now - random.uniform(0, spread_hours * 3600)
            payload = _make_payload(ts)
            try:
                r = client.post(endpoint, json=payload)
                if r.status_code in (200, 202):
                    sent += 1
                    print(f"  [{i + 1}/{count}] {payload['model']:<22} ✓")
                else:
                    failed += 1
                    print(f"  [{i + 1}/{count}] HTTP {r.status_code}: {r.text[:100]}")
            except Exception as e:
                failed += 1
                print(f"  [{i + 1}/{count}] error: {e}")
            # Be gentle with the /ingest rate limit (60/min)
            time.sleep(1.1)

    print(f"\nDone: {sent} sent, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL, help="Target base URL")
    parser.add_argument("--count", type=int, default=80, help="How many traces to seed")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    seed(args.url, args.count)

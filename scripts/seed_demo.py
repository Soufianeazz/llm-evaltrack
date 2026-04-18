"""
Seed the live dashboard with realistic demo data so first-time visitors
see a populated Main Dashboard, Agent Debugger, Prompt Debugger, and
Compliance page instead of empty screens.

Usage:
    python scripts/seed_demo.py                    # default: 80 ingest + 15 traces + compliance
    python scripts/seed_demo.py --count 5          # small batch (daily top-up)
    python scripts/seed_demo.py --url http://...   # override target

Idempotent in spirit — it only adds data, never deletes.
"""
from __future__ import annotations

import argparse
import random
import sys
import time

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
            ("You can return within 60 days, no questions asked.", 0.1),
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


# Agent scenarios for /traces — realistic multi-step runs with span types.
AGENT_SCENARIOS = [
    {
        "name": "research_agent",
        "input": "Summarize the current state of renewable energy investment in Europe.",
        "output": "Europe invested €420B in renewables in 2024, led by wind (38%) and solar (31%). Growth rate 14% YoY.",
        "spans": [
            {"name": "web_search", "type": "retrieval", "model": None, "output": "12 sources from IEA, Reuters, Bloomberg.", "tokens": 0, "cost": 0.0, "ms": 820},
            {"name": "rank_sources", "type": "tool", "model": None, "output": "Top 5 ranked by recency + authority.", "tokens": 0, "cost": 0.0, "ms": 140},
            {"name": "llm_summarize", "type": "llm", "model": "gpt-4o", "output": "Europe invested €420B in renewables in 2024...", "tokens": 1240, "cost": 0.0086, "ms": 3100},
            {"name": "fact_check", "type": "llm", "model": "claude-sonnet-4-6", "output": "All numeric claims verified against sources.", "tokens": 680, "cost": 0.0041, "ms": 1900},
        ],
    },
    {
        "name": "customer_support_agent",
        "input": "My invoice #4821 shows €299 but I'm on the free plan.",
        "output": "Invoice corrected — it was a billing system error. Refund initiated, should appear within 3 days.",
        "spans": [
            {"name": "fetch_user", "type": "tool", "model": None, "output": "User tier=free, account_id=u_8421", "tokens": 0, "cost": 0.0, "ms": 95},
            {"name": "fetch_invoice", "type": "tool", "model": None, "output": "Invoice #4821 amount=€299, status=charged", "tokens": 0, "cost": 0.0, "ms": 110},
            {"name": "classify_issue", "type": "decision", "model": "gpt-4o-mini", "output": "category: billing_error, severity: high", "tokens": 180, "cost": 0.0001, "ms": 420},
            {"name": "llm_respond", "type": "llm", "model": "gpt-4o", "output": "Invoice corrected — it was a billing system error...", "tokens": 520, "cost": 0.0038, "ms": 1600},
            {"name": "trigger_refund", "type": "tool", "model": None, "output": "Refund queued: rfnd_f4a2", "tokens": 0, "cost": 0.0, "ms": 230},
        ],
    },
    {
        "name": "document_qa",
        "input": "What does section 4.2 of our contract say about data retention?",
        "output": "Section 4.2 states data is retained for 90 days post-termination unless customer requests earlier deletion.",
        "spans": [
            {"name": "embed_query", "type": "llm", "model": "text-embedding-3-small", "output": "1536-dim vector", "tokens": 14, "cost": 0.000003, "ms": 180},
            {"name": "vector_search", "type": "retrieval", "model": None, "output": "3 chunks retrieved, top score 0.89", "tokens": 0, "cost": 0.0, "ms": 320},
            {"name": "llm_answer", "type": "llm", "model": "claude-sonnet-4-6", "output": "Section 4.2 states data is retained for 90 days...", "tokens": 890, "cost": 0.0054, "ms": 2200},
        ],
    },
    {
        "name": "sql_agent",
        "input": "Show me the top 5 customers by revenue this quarter.",
        "output": "Query executed. Top customers: Acme Corp (€142k), Globex (€98k), Initech (€87k), Umbrella (€71k), Hooli (€64k).",
        "spans": [
            {"name": "parse_intent", "type": "decision", "model": "gpt-4o-mini", "output": "intent: aggregation, entity: customers, metric: revenue", "tokens": 210, "cost": 0.0001, "ms": 380},
            {"name": "llm_generate_sql", "type": "llm", "model": "gpt-4o", "output": "SELECT customer_name, SUM(amount) FROM invoices WHERE ...", "tokens": 340, "cost": 0.0025, "ms": 1100},
            {"name": "execute_sql", "type": "tool", "model": None, "output": "5 rows returned", "tokens": 0, "cost": 0.0, "ms": 180},
            {"name": "format_response", "type": "llm", "model": "gpt-4o-mini", "output": "Top customers: Acme Corp (€142k)...", "tokens": 150, "cost": 0.00008, "ms": 540},
        ],
    },
    {
        "name": "code_review_agent",
        "input": "Review the PR adding rate limiting to /ingest.",
        "output": "2 suggestions: (1) add tests for the 429 path, (2) consider per-user limits instead of per-IP.",
        "spans": [
            {"name": "fetch_diff", "type": "tool", "model": None, "output": "142 lines changed across 3 files", "tokens": 0, "cost": 0.0, "ms": 180},
            {"name": "llm_analyze_diff", "type": "llm", "model": "claude-opus-4-6", "output": "Found 2 issues and 3 improvement suggestions.", "tokens": 2100, "cost": 0.042, "ms": 4600},
            {"name": "format_pr_comment", "type": "llm", "model": "claude-haiku-4-5", "output": "2 suggestions: (1) add tests for the 429 path...", "tokens": 420, "cost": 0.0004, "ms": 820},
        ],
    },
    {
        "name": "triage_bot",
        "input": "Is this bug report a duplicate of an existing issue?",
        "output": "Yes — duplicate of #812 (opened 3 weeks ago). Linked and closed.",
        "spans": [
            {"name": "search_issues", "type": "retrieval", "model": None, "output": "7 candidates retrieved", "tokens": 0, "cost": 0.0, "ms": 410},
            {"name": "llm_compare", "type": "llm", "model": "claude-sonnet-4-6", "output": "Duplicate of #812 with 94% similarity.", "tokens": 740, "cost": 0.0045, "ms": 1800},
            {"name": "github_link_close", "type": "tool", "model": None, "output": "Issue closed, linked to #812", "tokens": 0, "cost": 0.0, "ms": 320},
        ],
    },
    {
        "name": "meeting_summarizer",
        "input": "Summarize the 45-min weekly engineering sync.",
        "output": "Decisions: switch CI to GHA, freeze deploys Thursday. Action items: Alex owns the CI migration, due Friday.",
        "spans": [
            {"name": "transcribe", "type": "llm", "model": "whisper-1", "output": "Full transcript: 8241 words", "tokens": 0, "cost": 0.018, "ms": 12400},
            {"name": "chunk_transcript", "type": "tool", "model": None, "output": "8 chunks of ~1000 tokens", "tokens": 0, "cost": 0.0, "ms": 45},
            {"name": "llm_summarize", "type": "llm", "model": "gpt-4o", "output": "Decisions: switch CI to GHA...", "tokens": 3400, "cost": 0.028, "ms": 4200},
        ],
    },
    {
        "name": "lead_qualifier",
        "input": "Qualify inbound lead: jane@bigco.com, requested demo.",
        "output": "Qualified. BigCo = Fortune 500, 2k employees, fit for Team plan. Routed to sales@.",
        "spans": [
            {"name": "enrich_company", "type": "tool", "model": None, "output": "Company size: 2100, industry: FinTech", "tokens": 0, "cost": 0.0, "ms": 620},
            {"name": "llm_score_fit", "type": "llm", "model": "claude-haiku-4-5", "output": "Fit score: 8.5/10 — Team plan", "tokens": 380, "cost": 0.0003, "ms": 720},
            {"name": "route_to_sales", "type": "tool", "model": None, "output": "Assigned to sales@bigco.com", "tokens": 0, "cost": 0.0, "ms": 90},
        ],
    },
    {
        "name": "content_moderator",
        "input": "Moderate user comment on post #5821.",
        "output": "Flagged: mild toxicity (score 0.34). Held for human review.",
        "spans": [
            {"name": "heuristic_filter", "type": "tool", "model": None, "output": "No banned words detected", "tokens": 0, "cost": 0.0, "ms": 12},
            {"name": "llm_classify", "type": "llm", "model": "gpt-4o-mini", "output": "toxicity: 0.34, category: mild_insult", "tokens": 180, "cost": 0.0001, "ms": 480},
            {"name": "queue_review", "type": "tool", "model": None, "output": "Queued in human-review-medium", "tokens": 0, "cost": 0.0, "ms": 65},
        ],
    },
    {
        "name": "data_pipeline_agent",
        "input": "Process 1000 new product reviews for sentiment.",
        "output": "Processed 1000 reviews. Avg sentiment: 0.71 (positive). 42 flagged as spam.",
        "spans": [
            {"name": "load_reviews", "type": "tool", "model": None, "output": "1000 rows loaded from S3", "tokens": 0, "cost": 0.0, "ms": 1200},
            {"name": "batch_sentiment", "type": "llm", "model": "gpt-4o-mini", "output": "Processed in 10 batches of 100", "tokens": 42000, "cost": 0.012, "ms": 28000},
            {"name": "spam_filter", "type": "llm", "model": "claude-haiku-4-5", "output": "42 spam detected", "tokens": 8400, "cost": 0.008, "ms": 5200},
            {"name": "write_results", "type": "tool", "model": None, "output": "Written to analytics.reviews_processed", "tokens": 0, "cost": 0.0, "ms": 680},
        ],
    },
]


def _pick_weighted(options):
    weights = [q + 0.1 for _, q in options]
    return random.choices(options, weights=weights, k=1)[0]


def _make_ingest_payload(timestamp):
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


def seed_requests(client, base, count):
    endpoint = base + "/ingest"
    now = time.time()
    sent = 0
    failed = 0
    print(f"\n[1/3] Seeding {count} LLM calls → {endpoint}")
    for i in range(count):
        ts = now - random.uniform(0, 24 * 3600)
        payload = _make_ingest_payload(ts)
        try:
            r = client.post(endpoint, json=payload)
            if r.status_code in (200, 202):
                sent += 1
                print(f"  [{i + 1}/{count}] {payload['model']:<22} OK")
            else:
                failed += 1
                print(f"  [{i + 1}/{count}] HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            failed += 1
            print(f"  [{i + 1}/{count}] error: {e}")
        time.sleep(1.1)
    print(f"  Done: {sent} sent, {failed} failed")


def seed_traces(client, base, count):
    """Create agent traces with spans via /traces endpoints."""
    print(f"\n[2/3] Seeding {count} agent traces → {base}/traces")
    for i in range(count):
        scenario = random.choice(AGENT_SCENARIOS)
        try:
            # Create trace
            r = client.post(f"{base}/traces", json={
                "name": scenario["name"],
                "input": scenario["input"],
                "metadata": {"demo": True, "user_id": f"demo_user_{random.randint(1, 20)}"},
            })
            if r.status_code not in (200, 202):
                print(f"  [{i + 1}/{count}] trace create failed: HTTP {r.status_code}")
                continue
            trace_id = r.json()["trace_id"]

            # Create + end each span
            for span_def in scenario["spans"]:
                sr = client.post(f"{base}/traces/{trace_id}/spans", json={
                    "name": span_def["name"],
                    "span_type": span_def["type"],
                    "input": scenario["input"][:120],
                    "model": span_def["model"],
                })
                if sr.status_code not in (200, 202):
                    continue
                span_id = sr.json()["span_id"]

                client.post(f"{base}/traces/{trace_id}/spans/{span_id}/end", json={
                    "status": "completed",
                    "output": span_def["output"],
                    "tokens": span_def["tokens"],
                    "cost_usd": span_def["cost"],
                })

            # End the trace
            client.post(f"{base}/traces/{trace_id}/end", json={
                "status": "completed",
                "output": scenario["output"],
            })

            print(f"  [{i + 1}/{count}] {scenario['name']:<24} {len(scenario['spans'])} spans OK")
        except Exception as e:
            print(f"  [{i + 1}/{count}] error: {e}")
        time.sleep(0.5)


def seed_compliance(client, base):
    """Populate compliance: set retention policy + trigger some exports (generates audit log)."""
    print(f"\n[3/3] Seeding compliance → {base}/compliance")
    try:
        r = client.post(f"{base}/compliance/retention", params={"retention_days": 90, "enabled": True})
        print(f"  retention policy (90 days): HTTP {r.status_code}")
    except Exception as e:
        print(f"  retention error: {e}")

    # Trigger a few exports to populate audit log naturally
    for fmt, days in [("json", 7), ("csv", 30), ("json", 1)]:
        try:
            r = client.get(f"{base}/compliance/export", params={"format": fmt, "days": days})
            print(f"  export ({fmt}, {days}d): HTTP {r.status_code}")
        except Exception as e:
            print(f"  export error: {e}")


def seed(url, count, trace_count):
    base = url.rstrip("/")
    print(f"Seeding AgentLens demo data → {base}")

    with httpx.Client(timeout=30) as client:
        seed_requests(client, base, count)
        seed_traces(client, base, trace_count)
        seed_compliance(client, base)

    print("\nAll done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL, help="Target base URL")
    parser.add_argument("--count", type=int, default=80, help="How many ingest calls to seed")
    parser.add_argument("--traces", type=int, default=15, help="How many agent traces to seed")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    seed(args.url, args.count, args.traces)

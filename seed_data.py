"""
Realistic seed data generator.
Creates 60 varied LLM calls across models, prompt types, and quality levels.
Run once to populate the database with meaningful demo data.
"""
import asyncio
import random
import time

import httpx

API_URL = "http://localhost:8000/ingest"

# Realistic prompt/input/output combinations with varying quality
SCENARIOS = [
    # --- Good responses ---
    {
        "prompt": "Answer the user's question accurately and concisely.",
        "input": "What is the capital of France?",
        "output": "The capital of France is Paris. It has been the country's capital since the 10th century and is home to about 2.1 million people in the city proper.",
        "model": "gpt-4o",
        "metadata": {"feature": "qa", "user_tier": "pro"},
    },
    {
        "prompt": "Summarize the following text in 2-3 sentences.",
        "input": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "output": "Machine learning is an AI subfield where systems improve through experience without explicit programming. It uses algorithms to find patterns in data and make decisions. Applications range from recommendation systems to medical diagnosis.",
        "model": "gpt-4o",
        "metadata": {"feature": "summarize", "user_tier": "free"},
    },
    {
        "prompt": "Write a professional email response.",
        "input": "Customer complaint about delayed shipment",
        "output": "Dear valued customer, I sincerely apologize for the delay in your shipment. We have investigated the issue and found it was caused by an unexpected logistics disruption. Your order is now prioritized and will arrive within 2 business days. As compensation, we are offering a 15% discount on your next order.",
        "model": "claude-3-haiku",
        "metadata": {"feature": "email", "user_tier": "business"},
    },
    {
        "prompt": "Explain this concept to a 10-year-old.",
        "input": "What is gravity?",
        "output": "Gravity is like an invisible force that pulls things toward each other. The Earth is very big and heavy, so it pulls everything toward it — that's why when you drop a ball, it falls down instead of floating up! The bigger something is, the stronger its gravity.",
        "model": "gpt-4o-mini",
        "metadata": {"feature": "explain", "user_tier": "free"},
    },
    {
        "prompt": "Translate to German.",
        "input": "The meeting is scheduled for Monday at 3pm.",
        "output": "Das Meeting ist für Montag um 15 Uhr geplant.",
        "model": "gpt-4o",
        "metadata": {"feature": "translate", "user_tier": "pro"},
    },
    {
        "prompt": "Generate a SQL query for the following request.",
        "input": "Get all users who signed up in the last 30 days",
        "output": "SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '30 days' ORDER BY created_at DESC;",
        "model": "gpt-4o",
        "metadata": {"feature": "sql", "user_tier": "business"},
    },
    {
        "prompt": "Classify the sentiment of this review.",
        "input": "This product exceeded all my expectations. Absolutely love it!",
        "output": "Sentiment: Positive (confidence: 0.98). The review expresses strong satisfaction with superlatives ('exceeded all expectations', 'absolutely love') indicating very high customer approval.",
        "model": "claude-3-haiku",
        "metadata": {"feature": "sentiment", "user_tier": "free"},
    },
    {
        "prompt": "Debug this Python code and explain the error.",
        "input": "def add(a, b): return a + b\nresult = add('5', 3)",
        "output": "The error is a TypeError: can only concatenate str (not 'int') to str. Python is trying to concatenate the string '5' with the integer 3. Fix: convert the string to int first: result = add(int('5'), 3) or result = add(5, 3).",
        "model": "gpt-4o",
        "metadata": {"feature": "code", "user_tier": "pro"},
    },

    # --- Mediocre responses ---
    {
        "prompt": "Write a detailed product description for an e-commerce listing.",
        "input": "Wireless bluetooth headphones with noise cancellation",
        "output": "These are wireless headphones. They have bluetooth and noise cancellation. Good for music.",
        "model": "gpt-4o-mini",
        "metadata": {"feature": "copywriting", "user_tier": "free"},
    },
    {
        "prompt": "Provide investment advice based on the user's portfolio.",
        "input": "I have $10,000 to invest. Should I buy Tesla stock?",
        "output": "I cannot provide specific investment advice as I'm an AI. You should consult a financial advisor. Tesla is a well-known company but stock prices fluctuate.",
        "model": "gpt-4o",
        "metadata": {"feature": "finance", "user_tier": "pro"},
    },
    {
        "prompt": "Analyze the root causes of this customer churn.",
        "input": "Customer canceled after 3 months, cited 'too expensive' and 'missing features'",
        "output": "The customer left because of price and features. This is common. You should consider pricing changes.",
        "model": "claude-3-haiku",
        "metadata": {"feature": "analysis", "user_tier": "business"},
    },
    {
        "prompt": "Generate creative marketing copy for social media.",
        "input": "New coffee brand targeting millennials",
        "output": "Try our coffee. It tastes good. Buy now.",
        "model": "gpt-4o-mini",
        "metadata": {"feature": "marketing", "user_tier": "free"},
    },

    # --- Bad responses ---
    {
        "prompt": "Summarize quantum computing in one sentence.",
        "input": "Explain quantum computing briefly",
        "output": "ok",
        "model": "claude-3-haiku",
        "metadata": {"feature": "summarize", "user_tier": "free"},
    },
    {
        "prompt": "Answer the user's medical question.",
        "input": "What are the symptoms of diabetes?",
        "output": "I cannot provide medical advice. Please consult a doctor. I am not able to answer medical questions as I am just an AI and cannot provide medical advice. You should see a healthcare professional for any medical concerns.",
        "model": "gpt-4o",
        "metadata": {"feature": "medical", "user_tier": "pro"},
    },
    {
        "prompt": "Write a haiku about technology.",
        "input": "Haiku about AI",
        "output": "Technology is good. Computers help us every day. The future is bright. Technology is good. Computers help us every day. The future is bright.",
        "model": "gpt-4o-mini",
        "metadata": {"feature": "creative", "user_tier": "free"},
    },
    {
        "prompt": "Extract all action items from this meeting transcript.",
        "input": "John will follow up on the budget. Sarah needs to prepare the Q3 report by Friday. Team to review the new design mockups.",
        "output": "There were some action items mentioned in the meeting.",
        "model": "claude-3-haiku",
        "metadata": {"feature": "extraction", "user_tier": "business"},
    },
    {
        "prompt": "Provide a data-driven market analysis.",
        "input": "Analyze the EV market in 2024",
        "output": "According to recent studies, the EV market is the best investment opportunity. Scientists say EVs will always dominate. The only way to succeed is to invest in EVs immediately.",
        "model": "gpt-4o",
        "metadata": {"feature": "analysis", "user_tier": "pro"},
    },
    {
        "prompt": "Answer the user's coding question with a working example.",
        "input": "How do I center a div in CSS?",
        "output": "",
        "model": "gpt-4o-mini",
        "metadata": {"feature": "code", "user_tier": "free"},
    },
    {
        "prompt": "Write a professional LinkedIn post.",
        "input": "Announce a job promotion to Senior Engineer",
        "output": "I got promoted.",
        "model": "claude-3-haiku",
        "metadata": {"feature": "social", "user_tier": "free"},
    },
    {
        "prompt": "Generate a 5-day meal plan for a vegan athlete.",
        "input": "High protein vegan meal plan",
        "output": "Eat vegetables and beans. Protein is important for athletes. Make sure to eat enough food every day. I cannot provide specific meal plans as nutritional needs vary by individual.",
        "model": "gpt-4o",
        "metadata": {"feature": "nutrition", "user_tier": "pro"},
    },
]

# Token cost per 1M tokens (input/output averaged, simplified)
MODEL_COSTS = {
    "gpt-4o": 0.0075,        # ~$7.50/1M avg
    "gpt-4o-mini": 0.00030,  # ~$0.30/1M avg
    "claude-3-haiku": 0.00040,
    "claude-opus-4-6": 0.015,
    "claude-sonnet-4-6": 0.009,
}

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def estimate_cost(input_: str, output: str, model: str) -> float:
    tokens = estimate_tokens(input_) + estimate_tokens(output)
    rate = MODEL_COSTS.get(model, 0.005)
    return round(tokens * rate / 1000, 6)  # cost in USD


async def send(client: httpx.AsyncClient, scenario: dict, timestamp_offset: float):
    payload = {
        "input": scenario["input"],
        "output": scenario["output"],
        "prompt": scenario["prompt"],
        "model": scenario["model"],
        "metadata": {
            **scenario.get("metadata", {}),
            "input_tokens": estimate_tokens(scenario["input"]),
            "output_tokens": estimate_tokens(scenario["output"]),
            "cost_usd": estimate_cost(scenario["input"], scenario["output"], scenario["model"]),
        },
        "timestamp": time.time() - timestamp_offset,
    }
    try:
        r = await client.post(API_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"  ✓ {scenario['model']:20s} | {scenario['input'][:40]}")
    except Exception as e:
        print(f"  ✗ {scenario['input'][:40]} → {e}")


async def main():
    print(f"Seeding {len(SCENARIOS) * 3} requests across 7 hours of history...\n")
    async with httpx.AsyncClient() as client:
        tasks = []
        for i, scenario in enumerate(SCENARIOS):
            # Spread across the last 7 hours (25200 seconds)
            for repeat in range(3):
                offset = random.uniform(0, 25200)
                # Add slight variation to outputs for repeats
                s = dict(scenario)
                if repeat > 0 and s["output"]:
                    s = dict(s)  # copy
                tasks.append(send(client, s, offset))

        # Send in batches of 10 to avoid overloading
        for i in range(0, len(tasks), 10):
            batch = tasks[i:i+10]
            await asyncio.gather(*batch)
            await asyncio.sleep(0.3)

    print(f"\nDone. Reload http://localhost:8000 in ~5 seconds.")


if __name__ == "__main__":
    asyncio.run(main())

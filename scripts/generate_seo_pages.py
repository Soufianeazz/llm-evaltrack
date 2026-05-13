"""
Generate SEO comparison pages from a single template + competitor data.

Why this exists:
  - Existing pages have UTF-8 BOM + mojibake (â€"  â‚¬  âœ" etc)
  - Adding new competitors should be config-only, not copy-paste
  - All pages stay visually consistent

Usage:
  python scripts/generate_seo_pages.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = REPO_ROOT / "dashboard"


# ── Competitor data ──────────────────────────────────────────────────────────

COMPETITORS = {
    "langsmith": {
        "kind": "vs",  # also has /alternatives variant
        "name": "LangSmith",
        "name_lower": "langsmith",
        "tagline_hero": "Same visibility. Your infrastructure.",
        "blurb": "LangSmith is powerful — but self-hosting is locked behind Enterprise, and every prompt your users send flows through LangChain's US cloud. AgentLens gives you the same tracing, evals, and agent debugging with an open-core deployment model.",
        "their_pricing_url": "https://www.langchain.com/pricing",
        "their_starting_price": "$39 / seat / mo + usage",
        "their_self_host": "Enterprise plan only",
        "their_dpa": "Enterprise plan only",
        "rows": [
            ("Self-hosted deployment", True, "open-core deployment path", "Enterprise plan only"),
            ("EU data residency / GDPR DPA", True, "Team+ plan", "Enterprise plan only"),
            ("Air-gap mode (zero outbound)", True, "single env var, tcpdump-verified", False),
            ("Automatic quality scoring", True, "zero config", "Manual eval setup"),
            ("Hallucination detection", True, "built-in", False),
            ("Agent waterfall debugger", True, "", True),
            ("Framework-agnostic SDK", True, "any Python", "LangChain-native"),
            ("Cost tracking + budget alerts", True, "", True),
            ("2-line integration", True, "", True),
        ],
        "choose_them": [
            "Your team is deeply invested in the LangChain ecosystem",
            "You're fine with data flowing through US cloud",
            "You have budget for Enterprise self-hosting (~$5k+/mo)",
            "You need tight coupling with LangChain Hub + LangGraph tooling",
        ],
        "choose_us": [
            "Your prompts contain user data that can't leave EU / your VPC",
            "You want self-hosting without a 5-figure contract",
            "You want quality scoring + hallucination detection out of the box",
            "You use multiple frameworks (LangChain + raw OpenAI + custom)",
            "You want flat pricing — no per-seat billing",
        ],
        "migration_before": [
            ('# Before (LangSmith)', 'comment'),
            ('import os', 'plain'),
            ('os.environ["LANGCHAIN_TRACING_V2"] = "true"', 'env'),
            ('os.environ["LANGCHAIN_API_KEY"] = "..."', 'env'),
        ],
        "faqs": [
            ("Is AgentLens a drop-in LangSmith replacement?", "Not API-compatible — but the mental model (traces, spans, evals) is identical and the dashboard is familiar. Most teams migrate in under an hour."),
            ("Can I self-host LangSmith?", "LangSmith self-hosting is restricted to LangChain's Enterprise plan. AgentLens supports an open-core self-hosted deployment path with managed enterprise options."),
            ("Does AgentLens work without LangChain?", "Yes. Framework-agnostic. Works with plain OpenAI/Anthropic SDKs, LangChain, LlamaIndex, CrewAI, AutoGen, and custom agents."),
            ("How much does AgentLens cost compared to LangSmith?", "LangSmith Plus starts at $39/seat/month plus usage. AgentLens Starter is €299/month flat for 1M calls (no seat limits), or open-core self-hosted deployment."),
            ("Is there a GDPR DPA available?", "Yes, included on Team plan (€999/mo) and above. LangSmith's DPA is Enterprise-tier only."),
        ],
    },
    "langfuse": {
        "kind": "vs",
        "name": "Langfuse",
        "name_lower": "langfuse",
        "tagline_hero": "Same observability. Stronger compliance posture.",
        "blurb": "Langfuse is a solid open-source choice — but enterprise-grade compliance (DPA, SOC 2 readiness, audit logs, EU residency on managed cloud) and air-gap mode require effort. AgentLens ships those by default.",
        "their_pricing_url": "https://langfuse.com/pricing",
        "their_starting_price": "$59/mo Team",
        "their_self_host": "Yes (MIT)",
        "their_dpa": "Pro plan and above",
        "rows": [
            ("Self-hosted deployment", True, "open-core, BSL 1.1", "MIT, fully open-source"),
            ("Air-gap mode (zero outbound)", True, "single env var, tcpdump-verified", "Manual config"),
            ("EU-hosted managed cloud (default)", True, "Frankfurt", "EU optional"),
            ("Audit log + GDPR right-to-erasure", True, "Scale plan", "DIY"),
            ("Automatic quality + hallucination scoring", True, "heuristic, no judge calls", "Eval framework, paid LLM judge"),
            ("Agent waterfall debugger", True, "", True),
            ("Cost / budget alerts with webhooks", True, "", "Limited"),
            ("Framework-agnostic SDK", True, "", True),
            ("Production support SLA", True, "Scale+", "Enterprise add-on"),
        ],
        "choose_them": [
            "You want a fully MIT-licensed stack with no commercial restrictions",
            "Your compliance bar is low or you have time to DIY it",
            "You're comfortable on a smaller managed plan ($59-200/mo)",
            "You want LangChain integrations as a primary feature",
        ],
        "choose_us": [
            "Your buyer requires DPA + audit log + retention policy on day one",
            "You need air-gap mode that's verifiable, not configurable",
            "You want heuristic evaluation that doesn't make outbound LLM judge calls",
            "You want an EU-first managed cloud (Frankfurt-hosted by default)",
            "Production SLA matters",
        ],
        "migration_before": [
            ('# Before (Langfuse)', 'comment'),
            ('from langfuse import Langfuse', 'plain'),
            ('langfuse = Langfuse(public_key="...", secret_key="...")', 'env'),
        ],
        "faqs": [
            ("Can I migrate from Langfuse without rewriting my agent?", "Yes — both use a span/trace model. The SDK call surface differs but the wrapper code is mechanical. ~30 min for a typical agent."),
            ("Does AgentLens have feature parity with Langfuse?", "Core observability — yes. Langfuse has a more mature LLM-as-judge eval framework. AgentLens leans on heuristic scoring + agent debugging + compliance workflows. Pick based on which mix you need."),
            ("What's the licensing difference?", "Langfuse is fully MIT. AgentLens server is BSL 1.1 (converts to Apache 2.0 in 2030); SDK is MIT. The BSL only restricts offering AgentLens itself as a competing hosted service — internal production use is unrestricted."),
            ("Why pick AgentLens over a free MIT tool?", "Compliance (DPA, audit log, retention), production support SLA, EU residency by default, and air-gap mode that's verifiable rather than configurable."),
        ],
    },
    "helicone": {
        "kind": "vs",
        "name": "Helicone",
        "name_lower": "helicone",
        "tagline_hero": "Beyond proxy logging. Full observability + compliance.",
        "blurb": "Helicone is a great proxy-style logger — drop-in for OpenAI/Anthropic. AgentLens goes further: agent waterfalls for multi-step traces, automatic quality scoring, hallucination flags, and EU-native compliance built in.",
        "their_pricing_url": "https://www.helicone.ai/pricing",
        "their_starting_price": "$20/mo Pro",
        "their_self_host": "Yes (MIT)",
        "their_dpa": "Custom contract",
        "rows": [
            ("Proxy-style logging (drop-in for SDKs)", True, "via patch_openai / patch_anthropic", True),
            ("Multi-step agent waterfall traces", True, "trace_agent + spans", False),
            ("Automatic quality scoring + hallucination flags", True, "heuristic, zero config", False),
            ("Self-hosted deployment", True, "open-core, BSL 1.1", "MIT"),
            ("Air-gap mode (zero outbound)", True, "single env var, tcpdump-verified", "Manual"),
            ("EU-hosted managed cloud (default)", True, "Frankfurt", "US default"),
            ("DPA + audit log + retention policy", True, "Scale plan", "Custom contract"),
            ("Framework-agnostic SDK", True, "", "Proxy works for many"),
            ("Cost + budget alerts", True, "", True),
        ],
        "choose_them": [
            "You only need proxy-style request logs",
            "Your stack is purely OpenAI/Anthropic API calls (no multi-step agents)",
            "You want US managed cloud at the lowest price point",
            "You're not in regulated industry",
        ],
        "choose_us": [
            "You run multi-step agents and need waterfall debugging",
            "You want quality + hallucination scoring without manual eval setup",
            "Your buyer requires DPA, audit log, retention policy",
            "EU residency / air-gap matter to you",
            "You want compliance workflows out of the box",
        ],
        "migration_before": [
            ('# Before (Helicone)', 'comment'),
            ('from openai import OpenAI', 'plain'),
            ('client = OpenAI(', 'plain'),
            ('    base_url="https://oai.helicone.ai/v1",', 'env'),
            ('    default_headers={"Helicone-Auth": f"Bearer {KEY}"},', 'env'),
            (')', 'plain'),
        ],
        "faqs": [
            ("Is AgentLens a drop-in Helicone replacement?", "For proxy-style logging — yes, with patch_openai/patch_anthropic. For multi-step agents and quality scoring, AgentLens does more out of the box."),
            ("Can I run AgentLens alongside Helicone during migration?", "Yes. AgentLens is independent of your LLM SDK proxy. Run both, compare, pick a winner."),
            ("Does AgentLens require changing my code?", "Two-line install: agentlens.init() + agentlens.patch_openai(). Optional: wrap multi-step agents with trace_agent for the waterfall view."),
            ("Why pick AgentLens over Helicone?", "If you need multi-step agent traces, automatic quality scoring, GDPR-native compliance, or air-gap mode — AgentLens is the answer. For pure proxy logging, Helicone is simpler."),
        ],
    },
    "arize-phoenix": {
        "kind": "vs",
        "name": "Arize Phoenix",
        "name_lower": "arize-phoenix",
        "tagline_hero": "Production-grade observability without the notebook lock-in.",
        "blurb": "Phoenix is a great notebook-first ML observability tool from Arize. AgentLens is built for production-tier teams who need compliance, SLA, and a self-hosted deployment that runs as a real service — not a notebook.",
        "their_pricing_url": "https://phoenix.arize.com/",
        "their_starting_price": "Free OSS / Arize AX paid",
        "their_self_host": "Yes (notebook + Docker)",
        "their_dpa": "Arize AX paid contract",
        "rows": [
            ("Production deployment (not notebook)", True, "Docker + cron + persistent SQLite", "Notebook-first design"),
            ("Self-hosted (free OSS)", True, "open-core, BSL 1.1", True),
            ("Multi-step agent waterfalls", True, "trace_agent + spans", "Via OpenInference traces"),
            ("Automatic quality + hallucination flags", True, "zero config", "Eval framework, manual setup"),
            ("Air-gap mode (single env var)", True, "tcpdump-verified", "Manual config"),
            ("EU-hosted managed cloud", True, "Frankfurt", "Arize cloud is US"),
            ("DPA + audit log + retention", True, "Scale plan built-in", "Arize AX paid contract"),
            ("Plan-tier feature gating (server-side)", True, "Free / Starter / Team / Scale / Enterprise", "Arize AX is enterprise-tier only"),
            ("Framework-agnostic SDK", True, "any Python", "OpenInference standard"),
        ],
        "choose_them": [
            "Your team works primarily in notebooks (data science workflow)",
            "You're already on the Arize AX platform for ML observability",
            "You need OpenInference / OpenTelemetry-native instrumentation",
            "You want broader ML coverage (CV + tabular + LLM)",
        ],
        "choose_us": [
            "You're shipping LLM features in a production service (not notebooks)",
            "You need compliance workflows out of the box (DPA, audit, retention)",
            "Your buyer wants air-gap mode that's verifiable",
            "You want a clear paid tier ladder (€299–5,000/mo) instead of enterprise-sales-only",
        ],
        "migration_before": [
            ('# Before (Phoenix in notebook)', 'comment'),
            ('import phoenix as px', 'plain'),
            ('session = px.launch_app()', 'env'),
        ],
        "faqs": [
            ("Is AgentLens compatible with OpenInference/OpenTelemetry?", "Native compatibility is on the roadmap. For now, AgentLens uses its own SDK; OpenInference adapter is planned for Q3 2026."),
            ("Why pick AgentLens over Phoenix?", "Production deployment posture (Docker + persistent SQLite + cron-driven evals + alerts) plus compliance workflows + plan-tier ladder. Phoenix is notebook-first; AgentLens is service-first."),
            ("Can I use AgentLens for ML models beyond LLMs?", "Currently focused on LLMs and agents. CV/tabular monitoring is not on the immediate roadmap."),
        ],
    },
    "portkey": {
        "kind": "vs",
        "name": "Portkey",
        "name_lower": "portkey",
        "tagline_hero": "Observability + governance without proxying every call.",
        "blurb": "Portkey is a strong AI gateway — routing, fallbacks, caching. AgentLens focuses on what happens AFTER the call: deep traces, quality scoring, agent debugging, and compliance. The two coexist nicely.",
        "their_pricing_url": "https://portkey.ai/pricing",
        "their_starting_price": "Free / $49/mo Pro",
        "their_self_host": "Enterprise contract",
        "their_dpa": "Pro plan and above",
        "rows": [
            ("LLM gateway / routing / fallbacks", False, "out of scope", True),
            ("Semantic caching at edge", False, "out of scope", True),
            ("Self-hosted (free path)", True, "open-core, BSL 1.1", "Enterprise contract"),
            ("Multi-step agent waterfalls", True, "trace_agent + spans", "Limited"),
            ("Automatic quality + hallucination scoring", True, "heuristic, zero config", "Manual eval"),
            ("Air-gap mode (single env var)", True, "tcpdump-verified", "Limited"),
            ("EU-hosted managed cloud", True, "Frankfurt", "Multi-region"),
            ("Agent debugger UI", True, "waterfall view", "Limited"),
            ("Compliance workflows (DPA, audit, retention)", True, "Scale plan", "Pro+"),
        ],
        "choose_them": [
            "You need an LLM gateway with smart routing + fallbacks",
            "Edge-side semantic caching is core to your use case",
            "You don't need deep agent waterfall debugging",
            "Multi-region request routing is a key requirement",
        ],
        "choose_us": [
            "You need deep agent debugging + multi-step trace waterfalls",
            "Quality + hallucination scoring matter for your workflow",
            "Compliance posture (DPA, audit, retention) is non-negotiable",
            "Air-gap mode is a hard requirement",
        ],
        "migration_before": [
            ('# Both can coexist:', 'comment'),
            ('# Portkey handles routing/caching at the gateway', 'comment'),
            ('# AgentLens handles tracing/eval/compliance', 'comment'),
            ('agentlens.init(api_url="http://localhost:8000/ingest")', 'env'),
            ('agentlens.patch_openai()  # works alongside Portkey gateway', 'env'),
        ],
        "faqs": [
            ("Are Portkey and AgentLens competitors or complements?", "Mostly complements. Portkey is a gateway; AgentLens is observability. Many teams run both."),
            ("Can I use Portkey for routing + AgentLens for tracing?", "Yes. They operate at different layers — Portkey at the request gateway, AgentLens at the application SDK level. Both see the same call."),
            ("Why pick AgentLens for observability?", "Heuristic quality scoring out of the box + agent waterfalls + EU compliance + verifiable air-gap. Portkey's tracing is functional but lighter-weight."),
        ],
    },
    "lunary": {
        "kind": "vs",
        "name": "Lunary",
        "name_lower": "lunary",
        "tagline_hero": "Production observability with EU compliance baked in.",
        "blurb": "Lunary is a clean LLM analytics tool with a focus on cost. AgentLens covers cost too — and adds quality scoring, hallucination detection, agent waterfalls, GDPR workflows, and verifiable air-gap mode.",
        "their_pricing_url": "https://lunary.ai/pricing",
        "their_starting_price": "$20/mo Team",
        "their_self_host": "Yes (Apache-2.0)",
        "their_dpa": "Pro plan and above",
        "rows": [
            ("Cost analytics + per-model breakdown", True, "", True),
            ("Self-hosted deployment", True, "open-core, BSL 1.1", "Apache-2.0"),
            ("Multi-step agent waterfalls", True, "trace_agent + spans", "Limited"),
            ("Automatic quality + hallucination flags", True, "heuristic, zero config", "Manual eval"),
            ("Air-gap mode (single env var)", True, "tcpdump-verified", "Manual"),
            ("EU-hosted managed cloud (default)", True, "Frankfurt", "Multi-region"),
            ("Audit log + retention + right-to-erasure", True, "Scale plan", "Limited"),
            ("Production support SLA", True, "Scale+", "Enterprise add-on"),
            ("Framework-agnostic SDK", True, "", True),
        ],
        "choose_them": [
            "You want a fully Apache-2.0 stack with no commercial restrictions",
            "Cost analytics is your primary use case",
            "You're on a tight budget ($20/mo Team)",
            "You don't need deep multi-step agent traces or compliance docs",
        ],
        "choose_us": [
            "You need agent waterfall debugging + quality scoring",
            "Compliance posture (DPA, audit, retention) is a buyer requirement",
            "EU residency / air-gap matter",
            "You want production SLA on a managed plan",
        ],
        "migration_before": [
            ('# Before (Lunary)', 'comment'),
            ('import lunary', 'plain'),
            ('lunary.config(app_id="...", verbose=True)', 'env'),
        ],
        "faqs": [
            ("How does AgentLens differ from Lunary?", "Both cover cost + basic tracing. AgentLens adds quality scoring, hallucination detection, agent waterfalls, and GDPR workflows. Lunary is leaner; AgentLens is more comprehensive."),
            ("Can I migrate from Lunary?", "Yes — same span/trace mental model. ~30 min mechanical migration."),
            ("Why pick AgentLens over Lunary?", "Compliance posture, agent debugging depth, verifiable air-gap, EU-first managed cloud."),
        ],
    },
    "datadog-llm": {
        "kind": "alternatives",
        "name": "Datadog LLM Observability",
        "name_lower": "datadog-llm",
        "tagline_hero": "LLM observability without enterprise contracts.",
        "blurb": "Datadog's LLM observability is powerful — and locked behind enterprise contracts that start at multi-thousand monthly minimums. AgentLens delivers the core observability layer at a fraction of the cost, with EU residency and air-gap by default.",
        "their_pricing_url": "https://www.datadoghq.com/pricing/",
        "their_starting_price": "Custom enterprise (often $5k+/mo)",
        "their_self_host": "Limited",
        "their_dpa": "Standard enterprise",
        "rows": [
            ("Self-hosted (free path)", True, "open-core, BSL 1.1", "Limited / managed cloud only"),
            ("Starting price", True, "€299/mo flat", "Custom enterprise (often $5k+/mo)"),
            ("Multi-step agent waterfalls", True, "trace_agent + spans", True),
            ("Automatic quality + hallucination flags", True, "heuristic, zero config", "Eval framework, manual"),
            ("Air-gap mode (single env var)", True, "tcpdump-verified", "Limited (Datadog requires data flow to their cloud)"),
            ("EU-hosted (default for managed)", True, "Frankfurt", "EU region available"),
            ("Plan-tier feature gating", True, "Free / Starter / Team / Scale / Enterprise", "Enterprise tiers"),
            ("Compliance workflows (DPA, audit, retention)", True, "Scale plan", True),
            ("Vendor lock-in surface", "Low", "Pure SDK, no agent in your runtime", "Higher (Datadog agent + APM)"),
        ],
        "choose_them": [
            "You're already a Datadog customer for APM + infrastructure",
            "You have enterprise-tier budget approved",
            "Cross-stack correlation (logs + APM + LLM) is valuable",
            "You want a single vendor for full observability",
        ],
        "choose_us": [
            "Your budget is mid-market, not enterprise (€299–2,999/mo)",
            "You want LLM-specific observability without an APM agent in your runtime",
            "EU residency / air-gap matter",
            "You want to start free (self-hosted) and grow into a paid plan when ready",
        ],
        "migration_before": [
            ('# Before (Datadog LLM)', 'comment'),
            ('from datadog import initialize, statsd', 'plain'),
            ('initialize(api_key="...", app_key="...")', 'env'),
        ],
        "faqs": [
            ("Why pick AgentLens over Datadog LLM observability?", "Cost (10x cheaper at the entry point), no agent footprint in your runtime, EU residency by default, and a free self-hosted path so you can evaluate without procurement."),
            ("Can I run AgentLens alongside Datadog?", "Yes — they're complementary. Datadog handles infrastructure + APM; AgentLens handles LLM-specific traces and evaluations."),
            ("Does AgentLens have anything Datadog doesn't?", "Built-in heuristic quality scoring, hallucination flags, verifiable air-gap mode, and a clear self-hostable path with no enterprise contract gate."),
        ],
    },
}

# These competitors get a SECOND page at /alternatives/{name} (different search intent
# from /vs/{name} — "X alternative" search vs "X vs Y" search).
ALTERNATIVES_PAGES = ["langsmith", "langfuse", "helicone"]


# ── Template ──────────────────────────────────────────────────────────────────

def render_check(value, suffix=""):
    """Return HTML for a True / False / string value in a comparison row cell."""
    if value is True:
        return f'<span class="check">✓</span>{(" " + suffix) if suffix else ""}'
    if value is False:
        return '<span class="cross">✗</span>'
    if isinstance(value, str):
        return f'<span style="color:var(--muted);font-size:.85rem">{value}</span>'
    return str(value)


def build_rows(rows):
    out = []
    for capability, ours_val, ours_suffix, theirs_val in rows:
        out.append(
            f'<tr><td>{capability}</td>'
            f'<td class="ours">{render_check(ours_val, ours_suffix)}</td>'
            f'<td>{render_check(theirs_val)}</td></tr>'
        )
    return "\n      ".join(out)


def build_choose_list(items):
    return "\n        ".join(f'<li>{item}</li>' for item in items)


def build_migration_lines(lines):
    out = []
    for text, kind in lines:
        if kind == "comment":
            out.append(f'<div><span class="code-comment">{text}</span></div>')
        elif kind == "env":
            out.append(f'<div>{text}</div>')
        else:
            out.append(f'<div>{text}</div>')
    return "\n    ".join(out)


def build_faqs(faqs):
    return "\n    ".join(
        f'<details><summary>{q}</summary><p>{a}</p></details>'
        for q, a in faqs
    )


def build_jsonld_faq(faqs):
    import json
    main_entity = [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
        for q, a in faqs
    ]
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": main_entity,
    }, ensure_ascii=False)


def render_page(slug: str, kind: str, data: dict) -> str:
    """Render a /vs/{slug} or /alternatives/{slug} page."""
    name = data["name"]
    name_lower = data["name_lower"]
    canonical_path = f"/{kind}/{slug}"
    canonical_url = f"https://www.agentlens.one{canonical_path}"

    if kind == "vs":
        title = f"{name} Alternative — Self-hosted LLM Observability | AgentLens"
        h1 = f"AgentLens vs {name}"
        page_label = f"{name} Alternative · Self-hosted · Open Core"
    else:
        title = f"Best {name} Alternatives — Self-hosted LLM Observability | AgentLens"
        h1 = f"Looking for a {name} alternative?"
        page_label = f"{name} Alternative · EU · Self-hosted · Open Core"

    description = f"Looking for a self-hosted {name} alternative? AgentLens offers quality scoring, hallucination detection, agent debugging, and GDPR compliance — without sending your prompts to {name}'s cloud."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="icon" href="/logo.svg" type="image/svg+xml" />
  <meta property="og:title" content="{name} vs AgentLens — Self-hosted LLM Observability" />
  <meta property="og:description" content="{name}-alternative with open-core deployment, GDPR-native controls, and managed plans from €299/mo." />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:type" content="website" />
  <meta name="twitter:card" content="summary" />
  <script type="application/ld+json">
  {build_jsonld_faq(data["faqs"])}
  </script>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#0f1117;--surface:#1e2130;--border:#2d3148;--purple:#818cf8;--green:#4ade80;--red:#f87171;--text:#e2e8f0;--muted:#64748b}}
    body{{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}}
    a{{color:var(--purple);text-decoration:none}}
    a:hover{{text-decoration:underline}}
    nav{{display:flex;justify-content:space-between;align-items:center;padding:1.25rem 2rem;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:10}}
    .nav-logo{{font-weight:800;font-size:1.1rem;color:var(--text)}}
    .nav-logo span{{color:var(--purple)}}
    .nav-links{{display:flex;gap:1.5rem;align-items:center;font-size:.875rem}}
    .btn{{display:inline-block;padding:.5rem 1.25rem;border-radius:8px;font-weight:600;font-size:.875rem;cursor:pointer;transition:opacity .15s}}
    .btn:hover{{opacity:.85;text-decoration:none}}
    .btn-primary{{background:var(--purple);color:#0f1117}}
    .btn-outline{{border:1px solid var(--border);color:var(--text);background:none}}
    .hero{{max-width:820px;margin:0 auto;text-align:center;padding:4rem 2rem 2rem}}
    .badge{{display:inline-block;background:#1e2130;border:1px solid var(--border);border-radius:99px;padding:.3rem .9rem;font-size:.75rem;color:var(--purple);margin-bottom:1.5rem}}
    .hero h1{{font-size:clamp(2rem,5vw,3rem);font-weight:800;line-height:1.15;margin-bottom:1.25rem}}
    .hero h1 span{{color:var(--purple)}}
    .hero p{{font-size:1.05rem;color:var(--muted);max-width:620px;margin:0 auto 2rem}}
    .hero-ctas{{display:flex;gap:.75rem;justify-content:center;flex-wrap:wrap}}
    .section{{padding:3rem 2rem;max-width:1000px;margin:0 auto}}
    .section-label{{font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;color:var(--purple);margin-bottom:.75rem}}
    .section h2{{font-size:clamp(1.5rem,3vw,2rem);font-weight:700;margin-bottom:1rem}}
    .section > p{{color:var(--muted);max-width:620px;margin-bottom:1rem}}
    .compare-table{{width:100%;border-collapse:collapse;margin-top:1.5rem;font-size:.9rem}}
    .compare-table th{{padding:.75rem 1rem;text-align:left;border-bottom:1px solid var(--border);color:var(--muted);font-weight:600}}
    .compare-table th:not(:first-child){{text-align:center}}
    .compare-table td{{padding:.75rem 1rem;border-bottom:1px solid #1a1d2e;vertical-align:top}}
    .compare-table td:not(:first-child){{text-align:center}}
    .check{{color:var(--green);font-size:1rem}}
    .cross{{color:var(--red);font-size:1rem}}
    .ours{{background:rgba(129,140,248,.06)}}
    .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:1.5rem}}
    .two-col > div{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.5rem}}
    .two-col h3{{font-size:1rem;font-weight:700;margin-bottom:.75rem;color:var(--text)}}
    .two-col ul{{list-style:none;display:flex;flex-direction:column;gap:.5rem}}
    .two-col li{{font-size:.85rem;color:var(--muted);display:flex;gap:.5rem;align-items:flex-start}}
    .two-col li::before{{content:"→";color:var(--purple);flex-shrink:0}}
    .faq{{margin-top:1.5rem;display:flex;flex-direction:column;gap:.75rem}}
    .faq details{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem 1.25rem}}
    .faq summary{{cursor:pointer;font-weight:600;font-size:.95rem;color:var(--text)}}
    .faq p{{margin-top:.75rem;color:var(--muted);font-size:.88rem}}
    .code-block{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.25rem;font-family:'Menlo','Consolas',monospace;font-size:.82rem;line-height:1.7;margin-top:1rem;overflow-x:auto}}
    .code-comment{{color:var(--muted)}}
    .code-key{{color:#a5b4fc}}
    .code-str{{color:#86efac}}
    .code-fn{{color:#f9a8d4}}
    .cta-box{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:2rem;text-align:center;margin-top:2rem}}
    .cta-box h3{{font-size:1.15rem;font-weight:700;margin-bottom:.5rem}}
    .cta-box p{{color:var(--muted);font-size:.9rem;margin-bottom:1.25rem}}
    footer{{border-top:1px solid var(--border);padding:2rem;text-align:center;color:var(--muted);font-size:.8rem;margin-top:3rem}}
    @media(max-width:700px){{.two-col{{grid-template-columns:1fr}}nav{{padding:1rem}}.nav-links a:not(.btn){{display:none}}}}
  </style>
</head>
<body>

<nav>
  <a href="/" class="nav-logo"><span style="color:var(--text)">Agent<span style="color:var(--purple)">Lens</span></span></a>
  <div class="nav-links">
    <a href="/#features">Features</a>
    <a href="/#pricing">Pricing</a>
    <a href="https://github.com/Soufianeazz/agentlens" target="_blank">Core Repo</a>
    <a href="/dashboard?demo=1&api_key=al_demo_agentlens" class="btn btn-outline">Live Demo</a>
    <a href="/book-demo?source=comparison" class="btn btn-primary">Book a Demo</a>
  </div>
</nav>

<section class="hero">
  <div class="badge">{page_label}</div>
  <h1>{h1}<br/><span>{data["tagline_hero"]}</span></h1>
  <p>{data["blurb"]}</p>
  <div class="hero-ctas">
    <a href="/book-demo?source=migration-{name_lower}" class="btn btn-primary">Book a Migration Call</a>
    <a href="/dashboard?demo=1&api_key=al_demo_agentlens" class="btn btn-outline">See Live Demo →</a>
  </div>
</section>

<section class="section">
  <div class="section-label">Quick Comparison</div>
  <h2>Feature-by-feature</h2>
  <table class="compare-table">
    <thead>
      <tr>
        <th>Capability</th>
        <th class="ours" style="color:var(--purple)">AgentLens</th>
        <th>{name}</th>
      </tr>
    </thead>
    <tbody>
      {build_rows(data["rows"])}
    </tbody>
  </table>
  <p style="margin-top:1rem;font-size:.75rem;color:var(--muted)">Based on public {name} pricing as of May 2026. Verify at <a href="{data["their_pricing_url"]}" target="_blank" rel="noopener">{data["their_pricing_url"]}</a>.</p>
</section>

<section class="section">
  <div class="section-label">When to choose what</div>
  <h2>Honest recommendation</h2>
  <div class="two-col">
    <div>
      <h3>Choose {name} if…</h3>
      <ul>
        {build_choose_list(data["choose_them"])}
      </ul>
    </div>
    <div>
      <h3>Choose AgentLens if…</h3>
      <ul>
        {build_choose_list(data["choose_us"])}
      </ul>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-label">Migration</div>
  <h2>Switching from {name} takes ~30 minutes</h2>
  <p>Both tools share a similar mental model. The SDK surface is different but migration is mechanical.</p>
  <div class="code-block">
    {build_migration_lines(data["migration_before"])}
    <div>&nbsp;</div>
    <div><span class="code-comment"># After (AgentLens)</span></div>
    <div><span class="code-key">import</span> agentlens</div>
    <div>agentlens.<span class="code-fn">init</span>(<span class="code-str">"http://localhost:8000/ingest"</span>)</div>
    <div>agentlens.<span class="code-fn">patch_openai</span>()  <span class="code-comment"># or patch_anthropic()</span></div>
  </div>
</section>

<section class="section">
  <div class="section-label">FAQ</div>
  <h2>Common questions</h2>
  <div class="faq">
    {build_faqs(data["faqs"])}
  </div>
</section>

<section class="section">
  <div class="cta-box">
    <h3>Ready to own your LLM data?</h3>
    <p>15-minute migration call. We'll map your {name} setup to AgentLens and get you running.</p>
    <div class="hero-ctas">
      <a href="/book-demo?source=migration-{name_lower}" class="btn btn-primary">Book a Migration Call</a>
      <a href="https://github.com/Soufianeazz/agentlens" target="_blank" class="btn btn-outline">View Core Repo on GitHub</a>
    </div>
  </div>
</section>

<footer>
  <p>AgentLens · Open Core · <a href="https://github.com/Soufianeazz/agentlens">Core Repo</a> · <a href="https://pypi.org/project/agentlens-monitor">PyPI</a> · <a href="mailto:contact@agentlens.one">contact@agentlens.one</a></p>
  <p style="margin-top:.5rem"><a href="/impressum.html">Impressum</a> · <a href="/datenschutz.html">Datenschutz</a> · <a href="/nutzungsbedingungen.html">Nutzungsbedingungen</a></p>
</footer>

</body>
</html>
"""


# ── Generation ────────────────────────────────────────────────────────────────

def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    (DASHBOARD / "vs").mkdir(parents=True, exist_ok=True)
    (DASHBOARD / "alternatives").mkdir(parents=True, exist_ok=True)

    written = []
    for slug, data in COMPETITORS.items():
        # Generate /vs/{slug} for all (it's the primary path)
        primary_kind = "vs" if data["kind"] == "vs" else data["kind"]
        primary_path = DASHBOARD / primary_kind / f"{slug}.html"
        primary_path.write_text(render_page(slug, primary_kind, data), encoding="utf-8", newline="\n")
        written.append(str(primary_path.relative_to(DASHBOARD)))

        # Also generate /alternatives/{slug} for those with explicit second-intent SEO value
        if slug in ALTERNATIVES_PAGES and data["kind"] == "vs":
            alt_path = DASHBOARD / "alternatives" / f"{slug}.html"
            alt_path.write_text(render_page(slug, "alternatives", data), encoding="utf-8", newline="\n")
            written.append(str(alt_path.relative_to(DASHBOARD)))

    print(f"Generated {len(written)} SEO pages:")
    for w in written:
        print(f"  + {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Outreach Templates — AgentLens

Target: Developers / CTOs / Founding Engineers bei Startups die OpenAI/Anthropic in Production nutzen.

---

## 1. LinkedIn DM (kurz, direkt)

**Für: Dev oder CTO der öffentlich über LLM/AI postet**

> Hey [Name] — ich hab gesehen du baust mit [OpenAI/Claude/LLMs].
>
> Ich hab ein Tool gebaut das ich gerade launche: AgentLens. 2 Zeilen Code, und du siehst welche Responses schlechte Qualität haben, wo Halluzinationen auftreten, was du pro Call bezahlst — und bei Multi-Step Agents welcher Step crasht oder zu teuer ist.
>
> Self-hosted, MIT License, läuft auf Railway. Live Demo: AgentLens-production.up.railway.app
>
> Wärst du offen für 15 Min Feedback? Oder falls du es ausprobieren willst — Early Adopter Preis ist €199/Monat statt €299 (die ersten 10 Kunden, forever).

---

## 2. Cold Email

**Betreff:** Siehst du welche LLM-Responses bei [Firmenname] versagen?

> Hi [Name],
>
> Ich schreibe dir weil [Firmenname] aktiv mit LLMs baut — [LinkedIn/Blog/GitHub Referenz].
>
> Das Problem das ich bei fast jedem LLM-Team sehe: Man weiß nicht welche Responses schlecht sind, bis ein User sich beschwert. Kein Monitoring, kein Quality Scoring, kein Visibility in Agent Runs.
>
> Ich hab AgentLens gebaut — eine self-hosted Alternative zu LangSmith, in 2 Zeilen integriert:
>
> ```python
> agentlens.init("https://dein-server.com")
> agentlens.patch_openai()
> ```
>
> Was du bekommst:
> - Automatisches Quality Scoring für jeden Call
> - Hallucination Detection
> - Cost Tracking mit Budget Alerts
> - Agent Debugger mit Waterfall Timeline
> - GDPR-konform (deine Daten, dein Server)
>
> Live Demo (kein Login): AgentLens-production.up.railway.app
>
> Ich gebe den ersten 10 Kunden 33% Rabatt forever — €199/Monat statt €299.
>
> Hättest du 15 Minuten für einen kurzen Call diese Woche?
>
> Grüße,
> [Dein Name]

---

## 3. Reddit Post — r/LocalLLaMA / r/SideProject

**Titel:** I built a self-hosted LLM observability tool (open source) — know exactly where your app breaks

> Hey,
>
> I've been building LLM apps for a while and kept running into the same problem: no visibility into what's actually happening in production. Which responses are bad? Which prompts hallucinate? Which agent step is eating all the cost?
>
> So I built **AgentLens** — a self-hosted, open source alternative to LangSmith/Helicone.
>
> **2-line integration:**
> ```python
> agentlens.init("https://your-server.com")
> agentlens.patch_openai()  # that's it
> ```
>
> **What it does:**
> - Auto quality scoring (0-1) for every LLM response
> - Hallucination detection + flagging
> - Cost tracking per call + budget alerts (webhook/email)
> - **Agent Debugger** — waterfall timeline showing every span, duration, cost, errors
> - GDPR: export, retention policies, audit log
> - Regression detection (quality dropped since last hour?)
>
> **Tech:** FastAPI + SQLite + plain HTML dashboard (no frontend build step). Deploys to Railway in 1 click.
>
> **Live demo** (no login): https://AgentLens-production.up.railway.app
>
> **GitHub:** https://github.com/Soufianeazz/AgentLens
>
> **PyPI:** `pip install AgentLens`
>
> Happy to answer questions or take feedback. What features would make you actually use this?

---

## 4. Hacker News — "Show HN"

**Titel:** Show HN: AgentLens – self-hosted LLM observability with agent waterfall debugging

> I built this after getting frustrated with not knowing what was happening in my LLM apps in production.
>
> The core insight: most LLM monitoring tools just log requests. They don't tell you *quality*. AgentLens automatically scores every response (0–1), flags hallucinations, tracks cost, and shows regression alerts when quality drops.
>
> The newest feature (v0.2.0): Agent Debugger. If you run multi-step agents, you get a waterfall timeline showing every span — LLM calls, tool calls, retrieval steps — with timing, token counts, and errors. Click any span to expand input/output.
>
> **Technical:**
> - FastAPI + SQLite + aiosqlite (async)
> - SDK: `pip install AgentLens` — patches OpenAI/Anthropic clients with 2 lines
> - Dashboard: plain HTML + Chart.js, no build step
> - Deploys to Railway via git push
>
> **Self-hosted** = GDPR-friendly, your data stays on your server.
>
> Live demo: https://AgentLens-production.up.railway.app
> GitHub: https://github.com/Soufianeazz/AgentLens
>
> Would love feedback on what's missing or what would make you switch from LangSmith.

---

## 5. Twitter/X Thread

**Tweet 1:**
> I got tired of running LLM apps blind in production.
>
> So I built AgentLens — self-hosted observability in 2 lines:
>
> ```python
> agentlens.patch_openai()
> ```
>
> Quality scoring, hallucination detection, cost tracking. All automatic. Thread 👇

**Tweet 2:**
> The problem with most LLM monitoring: it just logs.
>
> It doesn't tell you *which* responses are bad.
> It doesn't tell you *which* prompts hallucinate.
> It doesn't tell you *which* agent step is burning money.
>
> AgentLens does all three.

**Tweet 3:**
> New in v0.2.0: Agent Debugger
>
> Waterfall timeline for every agent run.
> Click any span: see input, output, tokens, cost, errors.
>
> Finally know exactly where your 5-step agent breaks — and why.
>
> [screenshot link]

**Tweet 4:**
> Self-hosted means GDPR-friendly.
> Your prompts and outputs never leave your server.
>
> MIT License. Deploys to Railway in 1 click.
>
> Live demo (no login): AgentLens-production.up.railway.app
> GitHub: github.com/Soufianeazz/AgentLens

---

## Zielgruppen zum Ansprechen

### LinkedIn suche nach:
- "LLM engineer" OR "AI engineer" → Startups 1-50 Mitarbeiter
- Posts mit "OpenAI", "Claude API", "LangChain" in letzten 30 Tagen
- CTOs/Founding Engineers die über AI-Produkte posten

### Communities:
- r/LocalLLaMA (sehr aktiv, tech-savvy)
- r/SideProject (Builder-Community)
- Hacker News "Show HN" (Di-Do morgens 9-11 Uhr EST posten)
- LangChain Discord
- Latent Space Discord
- Twitter/X: Hashtags #LLMOps #AIEngineering

### Direkter Pitch bei:
- Startups die auf YC Founder Directory gelistet sind mit AI-Produkt
- Companies die auf job boards "AI Engineer" ausschreiben
- Open Source Repos die OpenAI/Anthropic als Dependency haben (GitHub Search)

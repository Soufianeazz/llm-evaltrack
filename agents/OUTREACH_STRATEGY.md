# AgentLens — Outreach Strategy & 30-Day Calendar

Generated: 2026-04-17  
Already contacted: Comet ML, OpenLIT, Arize AI, Traceloop, Pydantic, TensorZero, BerriAI, Serverless Devs, initMAX, Vstorm, Aegra

---

## 1. GitHub Search Queries (15 Queries für lead_finder.py)

Diese Queries sind bereits in `lead_finder.py` v2 eingebaut.
Logik: Wir suchen Repo-Owner die LLM-Frameworks *nutzen* (nicht bauen), weil die unser Tool brauchen.

| # | Query | Ziel-Persona |
|---|-------|-------------|
| 1 | `langchain openai tracing language:python stars:>5` | LangChain-Nutzer, bauen Agents |
| 2 | `anthropic claude monitoring language:python stars:>5` | Claude API-Nutzer |
| 3 | `llm observability python stars:>5` | suchen aktiv nach Observability |
| 4 | `openai cost tracking python stars:>5` | Cost-aware Builders |
| 5 | `langsmith alternative python stars:>5` | unzufrieden mit LangSmith |
| 6 | `llm agent framework python stars:>10` | Agent-Framework-Entwickler |
| 7 | `crewai autogen langgraph python stars:>5` | Multi-Agent-Nutzer |
| 8 | `rag pipeline retrieval augmented generation python stars:>5` | RAG-Builder |
| 9 | `vector database embeddings openai python stars:>5` | Embedding-Pipeline-Entwickler |
| 10 | `litellm proxy openai anthropic language:python stars:>5` | LiteLLM-Nutzer (multi-provider) |
| 11 | `dspy prompt optimization python stars:>5` | DSPy-Nutzer |
| 12 | `llamaindex openai evaluation language:python stars:>5` | LlamaIndex-Nutzer |
| 13 | `llm production deployment fastapi python stars:>5` | Prod-LLM-Backends |
| 14 | `ai chatbot backend python gdpr stars:>3` | EU/GDPR-bewusste Teams |
| 15 | `openai wrapper api cost monitoring stars:>3 language:python` | Eigenbau-Monitoring |

**Tipp:** Queries 6, 7, 12 liefern die heißesten Leads — Entwickler die Agents mit mehreren Steps bauen,  
brauchen exakt den AgentLens Waterfall Debugger.

---

## 2. LinkedIn Sales Navigator Filter-Kombinationen

### Filter-Set A: Early-Stage AI Startups (EU-Fokus)
```
Jobtitel:       "ML Engineer" OR "AI Engineer" OR "LLM Engineer" OR "AI Architect"
Seniority:      Senior, Lead, Director
Unternehmen:    1-50 Mitarbeiter (Startup)
Standort:       Deutschland, Österreich, Schweiz, Niederlande, Frankreich
Branche:        Technology, Computer Software, AI
Keywords:       "LangChain" OR "OpenAI" OR "Claude" OR "LLM" OR "RAG"
```

### Filter-Set B: Scale-up Teams (50-500 MA)
```
Jobtitel:       "Head of AI" OR "VP of Engineering" OR "CTO"
Unternehmen:    51-200 Mitarbeiter
Standort:       Europa (alle)
Branche:        FinTech, LegalTech, HealthTech, SaaS
Keywords:       "AI" OR "LLM" OR "Machine Learning"
```

### Filter-Set C: Open-Source Maintainer
```
Jobtitel:       "Software Engineer" OR "Developer" OR "Open Source"
Keywords:       "LangChain" OR "LlamaIndex" OR "CrewAI" OR "AutoGen"
Aktivität:      Post in letzten 30 Tagen über LLM/AI
```

### Filter-Set D: AI-Native B2B SaaS (höchste Kaufbereitschaft)
```
Jobtitel:       "CTO" OR "Co-Founder" OR "Technical Co-Founder"
Unternehmen:    1-20 Mitarbeiter, gegründet 2022-2025
Branche:        Computer Software
Keywords:       "GPT" OR "Claude" OR "AI-powered" OR "LLM"
Standort:       DACH + Benelux + Nordics
```

---

## 3. Top 50 Target Companies (AI Startups & LLM Builders)

Sortiert nach Fit-Score (1-5): Je höher, desto mehr von AgentLens profitieren sie.

### Tier 1 — Höchster Fit (Fit: 5/5) — nutzen LLMs in Produktion
| # | Company | Warum | HQ | Ansprache-Winkel |
|---|---------|-------|-----|-----------------|
| 1 | **Dust.tt** | AI agent platform, viele LLM-Calls | Paris | Agent debugger, cost control |
| 2 | **Fixie.ai** | LLM-powered apps, RAG | San Francisco | Hallucination detection |
| 3 | **Cognosys** | AI agent workflows | Vancouver | Waterfall debugger |
| 4 | **Respell** | No-code AI automation | SF | Cost tracking per workflow |
| 5 | **Langdock** | LangChain-basierte KI-Platform | Berlin | GDPR + self-hosted pitch |
| 6 | **Aleph Alpha** | EU LLM Provider | Heidelberg | GDPR-native, EU-compliance |
| 7 | **Luminance** | AI für Legal-Docs | London | GDPR, hallucination detection |
| 8 | **Harvey AI** | LegalTech + LLM | SF | Case study: legal team 90% faster |
| 9 | **Leya** | AI für Anwälte | Stockholm | GDPR pitch direkt |
| 10 | **Lemon AI** | AI-native Sales Automation | Berlin | Agent debugging |
| 11 | **Parloa** | Conversational AI | Berlin | LLM Monitoring, EU-Daten |
| 12 | **Nora** | AI Recruiting | München | Cost per hire via LLM |
| 13 | **Kern AI** | NLP Data Platform | Berlin | Observability, quality scoring |
| 14 | **DeepJudge** | Legal AI Search | Zürich | GDPR + hallucination |
| 15 | **AX Semantics** | NLG Platform | Stuttgart | LLM Cost Monitoring |

### Tier 2 — Hoher Fit (Fit: 4/5)
| # | Company | Warum | HQ |
|---|---------|-------|-----|
| 16 | **Eleven Labs** | Voice AI, multi-model | London |
| 17 | **Mistral AI** | LLM Provider, open-source | Paris |
| 18 | **Cohere** | Enterprise LLM | Toronto |
| 19 | **Weights & Biases** | MLOps (Konkurrenz/Partner) | SF |
| 20 | **Scale AI** | Data + LLM Evaluation | SF |
| 21 | **Hugging Face** | Open-source Hub | Paris/NY |
| 22 | **Replit** | AI-assisted coding, LLM-powered | SF |
| 23 | **Cursor** | AI Code Editor | SF |
| 24 | **Continue.dev** | Open-source AI coding | Remote |
| 25 | **Phind** | AI Search for devs | SF |
| 26 | **Perplexity AI** | AI Search | SF |
| 27 | **You.com** | AI Search | SF |
| 28 | **Kapa.ai** | AI für Developer Docs | Berlin |
| 29 | **Mendable** | AI Search für Docs | SF |
| 30 | **Docugami** | Document AI | Kirkland, WA |

### Tier 3 — Mittlerer Fit (Fit: 3/5)
| # | Company | Warum | HQ |
|---|---------|-------|-----|
| 31 | **Zapier** | AI Automation, LLM integrations | SF |
| 32 | **Make (Integromat)** | Automation + AI | Prag |
| 33 | **Relevance AI** | AI Agent Builder | Sydney |
| 34 | **Flowise** | Open-source LangChain UI | Remote |
| 35 | **Dify.ai** | LLM App Builder | Remote |
| 36 | **Botpress** | Chatbot + LLM | Montreal |
| 37 | **Voiceflow** | Conversation AI builder | Toronto |
| 38 | **Typebot** | Open-source chatbot | Remote |
| 39 | **Stack AI** | AI App Builder | SF |
| 40 | **Lindy AI** | AI Employee | SF |
| 41 | **Bland AI** | Phone AI Agents | SF |
| 42 | **Retell AI** | Voice AI Agents | SF |
| 43 | **Vapi** | Voice AI API | SF |
| 44 | **ElevenLabs** | Voice AI | London |
| 45 | **Deepgram** | Speech AI | SF |
| 46 | **AssemblyAI** | Audio AI | SF |
| 47 | **Qdrant** | Vector DB | Berlin |
| 48 | **Weaviate** | Vector DB | Amsterdam |
| 49 | **LanceDB** | Vector DB, embedded | SF |
| 50 | **ChromaDB** | Open-source Vector DB | Remote |

**Priorität:** Erst Tier 1 (EU/DACH-Companies), dann Tier 2.  
GDPR-Angle bei allen EU-Unternehmen immer als erstes Argument nennen.

---

## 4. Top 20 Open Source Repos — Potenzielle Kunden-Committer

Diese Repos haben Contributors die LLMs in Produktion nutzen und  
aktiv nach Monitoring-Lösungen suchen (GitHub Issues als Kanal).

| # | Repo | Stars | Warum Potenzial | GitHub Issue Angle |
|---|------|-------|-----------------|-------------------|
| 1 | **langchain-ai/langchain** | 90k+ | Jeder LangChain-Nutzer braucht Observability | Issue: "Built-in cost tracking?" |
| 2 | **microsoft/autogen** | 35k+ | Multi-Agent, Debugging ist Schmerz | Issue: "Agent waterfall visualization?" |
| 3 | **joaomdmoura/crewai** | 22k+ | CrewAI-Nutzer zahlen für Agent-Debugging | Comment in Debug-Issues |
| 4 | **run-llama/llama_index** | 35k+ | RAG-Entwickler brauchen Eval | Issue: "Evaluation + tracing?" |
| 5 | **BerriAI/litellm** | 14k+ | Multi-Provider-Nutzer = Cost-aware | Comment zu Cost-Issues |
| 6 | **langgenius/dify** | 45k+ | LLM-App-Builder | Issue: "Self-hosted monitoring?" |
| 7 | **logspace-ai/langflow** | 30k+ | Visueller LLM-Builder | Issue: "Trace each node?" |
| 8 | **stanford-crfm/dspy** | 18k+ | DSPy-Nutzer evaluieren Prompts | Issue: "Evaluation tracking?" |
| 9 | **guidance-ai/guidance** | 18k+ | Structured LLM Output | Issue: "Output quality monitoring?" |
| 10 | **microsoft/semantic-kernel** | 22k+ | Enterprise LLM SDK | Issue: "Observability plugin?" |
| 11 | **hwchase17/langchainjs** | 12k+ | JS-LangChain | Comment: "Python SDK, JS coming" |
| 12 | **nomic-ai/gpt4all** | 67k+ | Local LLM Runner | Issue: "API call monitoring?" |
| 13 | **lm-sys/FastChat** | 37k+ | LLM Serving | Issue: "Request tracing?" |
| 14 | **vllm-project/vllm** | 28k+ | LLM Inference | Issue: "Cost per request?" |
| 15 | **PromtEngineer/localGPT** | 20k+ | Local RAG | Issue: "Eval framework?" |
| 16 | **imartinez/privateGPT** | 53k+ | Private LLM | GDPR-Angle perfekt |
| 17 | **n8n-io/n8n** | 47k+ | Automation + AI Nodes | Issue: "LLM call monitoring?" |
| 18 | **onlook-dev/onlook** | 10k+ | AI UI Builder | Issue: "AI cost tracking?" |
| 19 | **AgentOps-AI/agentops** | 2.5k | Direkter Konkurrent/Nutzer | Differentiation: self-hosted |
| 20 | **whyhow-ai/whyhow** | 1k+ | Knowledge Graph + LLM | Issue: "Quality scoring?" |

**Taktik für GitHub Issues:**
1. Finde Issues mit Label "feature request", "monitoring", "observability", "debugging"
2. Kommentiere hilfreich: "We built X for this exact problem — check out AgentLens (self-hosted)"
3. Niemals spammen — max. 2-3 Issues pro Repo, immer mit echtem Mehrwert-Kommentar

---

## 5. Bug-Analyse & Fixes in lead_finder.py

### Bug 1: Überschreiben statt Anhängen (KRITISCH)
**Problem:** Jeder Run überschreibt `leads.csv` komplett mit `open(..., "w")`.  
Alle manuell gesetzten `outreach_status`-Felder (sent, draft) gehen verloren.  
Leads die bereits kontaktiert wurden, werden als "new" neu eingetragen.

**Fix implementiert in v2:**
```python
# Bestehende Leads laden + seen-Set bauen
existing_leads, existing_seen = _load_existing_leads()

# Nur neue suchen (existing_seen verhindert Duplikate)
new_leads = await _find_leads_impl(existing_seen)

# Kombiniert speichern
all_leads = existing_leads + new_leads
_save_leads(all_leads)
```

---

### Bug 2: Rate Limiting unvollständig (HOCH)
**Problem:** Nur `status_code == 403` wird behandelt — aber GitHub hat zwei Rate Limits:
- Primary: 5000 req/h (mit Token) — erkennbar an `X-RateLimit-Remaining: 0`
- Secondary: verhindert Bursts — gibt `403` mit `Retry-After` Header zurück

Der alte Code wartet bei 403 pauschal 60s, ignoriert aber:
- `Retry-After` Header (kann 10-120s sein, nicht immer 60s)
- Proaktives Warten wenn `X-RateLimit-Remaining` nahe 0

**Fix implementiert in v2:**
```python
async def _check_rate_limit(response: httpx.Response) -> None:
    remaining = response.headers.get("X-RateLimit-Remaining")
    reset_at   = response.headers.get("X-RateLimit-Reset")

    if response.status_code == 403:
        retry_after = int(response.headers.get("Retry-After", 60))
        await asyncio.sleep(retry_after)
        return

    if remaining is not None and int(remaining) < 5:
        wait = max(0, int(reset_at) - int(time.time())) + 2
        await asyncio.sleep(wait)
```

Außerdem: `asyncio.sleep(0.3)` → `asyncio.sleep(0.5)` und `sleep(1.5)` → `sleep(2.0)`  
GitHub empfiehlt min. 1 Request/Sekunde für unauthentifizierte Calls.

---

### Bug 3: Queries zu unspezifisch / kein Qualitäts-Filter (MITTEL)
**Problem:** 
- Nur 5 Queries → zu wenige Leads
- Kein Filter auf Repo-Stars nach dem API-Call (der `stars:>3` Query-Parameter reicht nicht —  
  GitHub API filtert nicht immer exakt)
- Keine Filterung nach User-Qualität (Bot-Accounts, Orgs mit 0 echten Kontakten)

**Fix implementiert in v2:**
```python
# 15 Queries statt 5
# Stars-Filter nach API-Response
items = r.json().get("items", [])
return [repo for repo in items if repo.get("stargazers_count", 0) >= min_stars]

# Org/Follower-Filter
if SKIP_ORGS and user.get("type") == "Organization":
    continue
if user.get("followers", 0) < MIN_FOLLOWERS:
    continue
```

---

## 6. 30-Tage Outreach Calendar

**Tägliche Baseline-Ziele:**
- Emails: 5-10/Tag (SendGrid Free: 100/Tag limit)
- LinkedIn DMs: 10-15/Tag (Sales Navigator Limit: ~100/Woche)
- GitHub Comments: 2-3/Tag (qualitative, kein Spam)
- Twitter/X Engagement: 5/Tag (Reply zu LLM-Builder Tweets)

---

### Woche 1 (17.04 — 23.04): Foundation + Quick Wins

**Fokus:** EU/DACH-Tier-1-Companies + GitHub Lead-Finder neu befüllen

| Tag | Kanal | Targets | Aktion |
|-----|-------|---------|--------|
| Mo 17.04 | GitHub | Run lead_finder.py mit neuen 15 Queries | 50-80 neue Leads generieren |
| Mo 17.04 | Email | Langdock, Kapa.ai, Parloa, Kern AI | GDPR-Pitch: "Ihr baut für EU-Kunden" |
| Di 18.04 | LinkedIn | DACH AI Engineers (Filter-Set A) | 15 Connection Requests + Kurz-DM |
| Di 18.04 | Email | Dust.tt, Lemon AI, Nora | Agent Debugger Pitch |
| Mi 19.04 | GitHub | LangChain-Repo Issues kommentieren | 3 hilfreiche Comments mit AgentLens-Link |
| Mi 19.04 | Email | 8 neue Leads aus lead_finder (mit Email) | Personalisierter Outreach via run_campaign.py |
| Do 20.04 | LinkedIn | Filter-Set B (Heads of AI, 50-200 MA) | 15 DMs: "Wie debuggt ihr eure LLM-Agents?" |
| Do 20.04 | Email | DeepJudge, Luminance, Harvey AI | Legal AI: Hallucination Detection Pitch |
| Fr 21.04 | GitHub | CrewAI, AutoGen Issues | 3 Comments zu Debug-Feature-Requests |
| Fr 21.04 | Email | Follow-Up Welle 1 (Montag-Emails +48h) | "Habt ihr Zeit für 20 Min?" |
| Sa 22.04 | Content | LinkedIn Post schreiben | "Wie wir LLM-Kosten um 60% gesenkt haben" |
| So 23.04 | Analyse | Replies prüfen, Calendar Woche 2 anpassen | — |

**Woche 1 Ziele:**
- 35 Emails gesendet
- 45 LinkedIn DMs
- 9 GitHub Comments
- Ziel: 2-3 Demo-Calls gebucht

---

### Woche 2 (24.04 — 30.04): Scaling + Follow-Ups

**Fokus:** Open Source Repo-Contributors + LinkedIn Scale-up

| Tag | Kanal | Targets | Aktion |
|-----|-------|---------|--------|
| Mo 24.04 | Email | Follow-Up alle nicht-respondierten Woche-1-Leads | Template: "Quick follow-up — 2 Minuten?" |
| Mo 24.04 | GitHub | Dify, Langflow Issues | Comments zu Monitoring-Feature-Requests |
| Di 25.04 | LinkedIn | Filter-Set C (Open-Source Maintainer) | 15 DMs: "Ich sehe du nutzt CrewAI —..." |
| Di 25.04 | Email | 10 neue GitHub-Leads (run_campaign.py) | Batch 2 |
| Mi 26.04 | Twitter/X | Reply zu LLM-Builder Threads | "We open-sourced our observability stack" |
| Mi 26.04 | Email | Relevance AI, Flowise, Stack AI | No-code Builder Pitch |
| Do 27.04 | LinkedIn | Filter-Set D (CTOs, Co-Founders, 1-20 MA) | 15 DMs: direkter Demo-Invite |
| Do 27.04 | Email | Tier-2 Companies: Dust, Cognosys, Respell | Agent-Debugging Pitch |
| Fr 28.04 | GitHub | privateGPT, localGPT Contributors | GDPR/Selbst-Hosting Pitch in Issues |
| Fr 28.04 | Email | Follow-Up Welle 2 | Letzte Chance vor Archivierung |
| Sa 29.04 | Content | Case Study Twitter Thread | Legal-Tech Case Study 90% faster |
| So 30.04 | Analyse | Response Rate messen, A/B Varianten testen | — |

**Woche 2 Ziele:**
- 50 Emails gesendet
- 45 LinkedIn DMs
- 9 GitHub Comments
- 15 Twitter Engagements
- Ziel: 4-6 Demo-Calls gebucht, 1 bezahlender Kunde

---

### Woche 3 (01.05 — 07.05): Community + Content-Led

**Fokus:** Inbound durch Content + Community-Präsenz aufbauen

| Tag | Kanal | Targets | Aktion |
|-----|-------|---------|--------|
| Mo 01.05 | GitHub | AgentLens Repo: README verbessern | "Show HN"-vorbereitung |
| Di 02.05 | Reddit | r/MachineLearning, r/LocalLLaMA | Show AgentLens: "We built a self-hosted..." |
| Di 02.05 | Email | 10 neue Leads Batch 3 | Fokus: RAG-Builder (Query 8,9) |
| Mi 03.05 | LinkedIn | Post: "5 LLM Cost Mistakes" | Organischer Inbound |
| Mi 03.05 | Discord | LangChain Discord, CrewAI Discord | Hilfreich in #help Channels |
| Do 04.05 | Email | Tier-1 Companies die nicht geantwortet | 3. Touch: anderer Winkel (Cost statt GDPR) |
| Do 04.05 | GitHub | n8n Issues, Zapier Community | Automation + LLM Monitoring |
| Fr 05.05 | HackerNews | "Show HN: AgentLens — self-hosted LLM observability" | Ziel: 50+ Upvotes, Top-5 |
| Sa 06.05 | Email | HN-Interessenten (Comments) | Direkte Follow-Up-Emails |
| So 07.05 | Analyse | Metriken Woche 3, Top-Performing Templates identifizieren | — |

**Woche 3 Ziele:**
- 40 Emails gesendet
- 30 LinkedIn DMs
- 15 Community Comments (Discord, Reddit)
- 1x HackerNews Show HN
- Ziel: 5-10 Demo-Calls, 2-3 bezahlende Kunden

---

### Woche 4 (08.05 — 14.05): Demo-to-Close + Referrals

**Fokus:** Demos konvertieren, erste Kunden um Referrals bitten

| Tag | Kanal | Targets | Aktion |
|-----|-------|---------|--------|
| Mo 08.05 | Email | Alle Demo-Interessenten | Kalender-Link + Prep-Fragen senden |
| Di 09.05 | LinkedIn | Post: "After 100 cold emails, here's what worked" | Thought Leadership |
| Mi 10.05 | Email | Neuer Batch 4: Tier-2/3 Companies | Skalierung |
| Do 11.05 | Email | Demo-Follow-Ups (48h nach Demo) | Angebot + Pricing senden |
| Fr 12.05 | GitHub | Erfolgreiche Kunden bitten, AgentLens zu starten | Social Proof |
| Sa 13.05 | Email | Referral-Bitte an erste Kunden | "Kennt ihr jemanden der..." |
| So 14.05 | Analyse | Monat 1 Review — was hat konvertiert? | Pivot-Entscheidung |

**Woche 4 Ziele:**
- 30 Emails gesendet
- 20 LinkedIn DMs
- 3-5 Demo-Calls durchgeführt
- Ziel: 3-5 bezahlende Kunden, MRR > €500

---

## 7. Tägliche Checkliste (Template)

```
MORGEN (30 Min):
[ ] lead_finder.py run (Mo + Do)
[ ] 5-10 Emails via run_campaign.py --dry-run prüfen, dann senden
[ ] LinkedIn: 5 DMs aus gespeicherter Liste

MITTAG (20 Min):
[ ] GitHub: 1-2 hilfreiche Comments
[ ] Twitter: 3-5 Replies zu LLM-Tweets

ABEND (15 Min):
[ ] AgentLens Dashboard checken: Replies/Öffnungsraten
[ ] Responds beantworten
[ ] leads.csv: Status auf "replied" setzen
```

---

## 8. Email-Templates: A/B Test Varianten

### Variante A — Cost Angle (für Repo mit >10 Stars)
```
Subject: {repo_name} → hidden LLM costs?

Hi {name},

Saw {repo_name} — nice work on {repo_description_snippet}.

Quick question: do you track what each LLM call actually costs you?  
Most teams find out they've wasted $300-500/month on hallucinated outputs  
only after they get the bill.

We built AgentLens for this — 2-line setup, self-hosted, no data leaves your infra.  
Case study: German legal team cut wasted API costs by €1,200/month:  
[case study link]

Worth a 20-min call?

— Soufian
```

### Variante B — Debugging Angle (für Agent/Multi-Step Repos)
```
Subject: debug {repo_name} agent steps visually?

Hi {name},

{repo_name} looks like it has multiple LLM steps — when one fails,  
how do you figure out which step broke and why?

We built a waterfall debugger for exactly this. Self-hosted, 2-line setup.  
[case study link]

20 minutes?

— Soufian
```

### Variante C — GDPR Angle (für EU-Companies)
```
Subject: {repo_name} + GDPR compliance?

Hi {name},

Building {repo_name} for EU customers means your LLM call data  
shouldn't leave your infrastructure.

AgentLens is self-hosted, GDPR-native — logs never touch our servers.  
2-line integration: patch_openai() or patch_anthropic().  
[case study link]

20-min demo?

— Soufian
```

---

## 9. Erfolgsmessung (KPIs)

| Metrik | Woche 1 Ziel | Monat 1 Ziel |
|--------|-------------|--------------|
| Emails gesendet | 35 | 155 |
| Email Open Rate | >40% | >40% |
| Reply Rate | >8% | >10% |
| Demo-Calls | 2-3 | 10-15 |
| Demo → Trial Rate | — | >30% |
| Trial → Paid Rate | — | >20% |
| Bezahlende Kunden | 0 | 3-5 |
| MRR | €0 | €500-1500 |

**Nächste Schritte:**
1. `python agents/lead_finder.py` — neuen Run mit v2 starten (15 Queries)
2. `python agents/run_campaign.py --dry-run` — Emails prüfen
3. LinkedIn Sales Navigator Filter-Set A einrichten
4. GitHub Issues der Top-5 Repos nach "monitoring" und "observability" durchsuchen

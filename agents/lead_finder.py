"""
Agent 1 — Lead Finder
Durchsucht GitHub nach Entwicklern, die aktiv LLM-Frameworks nutzen.
Speichert Leads als CSV in agents/leads.csv.

Verwendung:
    python agents/lead_finder.py
"""
import httpx
import csv
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import agentlens
    from agentlens import trace_agent
    TRACING = True
except ImportError:
    TRACING = False

# ── Konfiguration ──────────────────────────────────────────────
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN", "")          # Optional — erhöht Rate Limit auf 5000/h
AGENTLENS_URL   = os.getenv("AGENTLENS_URL", "https://llm-evaltrack-production.up.railway.app")
OUTPUT_FILE     = Path(__file__).parent / "leads.csv"

# Was suchen wir? Repos die LLM-Frameworks nutzen
SEARCH_QUERIES = [
    "langchain openai tracing language:python stars:>3",
    "anthropic claude monitoring language:python stars:>3",
    "llm observability python stars:>3",
    "openai cost tracking python stars:>3",
    "langsmith alternative python stars:>3",
]

LEADS_PER_QUERY = 8   # GitHub-Ergebnisse pro Query
# ───────────────────────────────────────────────────────────────


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


async def _search_repos(client: httpx.AsyncClient, query: str) -> list:
    try:
        r = await client.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "updated", "per_page": LEADS_PER_QUERY},
            headers=_gh_headers(),
            timeout=30,
        )
        if r.status_code == 403:
            print("  [GitHub Rate Limit erreicht — warte 60s]")
            await asyncio.sleep(60)
            return []
        if r.status_code != 200:
            print(f"  [GitHub Fehler {r.status_code}]")
            return []
        return r.json().get("items", [])
    except Exception as e:
        print(f"  [Netzwerkfehler: {e}]")
        return []


async def _get_user(client: httpx.AsyncClient, username: str) -> dict:
    try:
        r = await client.get(
            f"https://api.github.com/users/{username}",
            headers=_gh_headers(),
            timeout=20,
        )
        if r.status_code != 200:
            return {}
        d = r.json()
        return {
            "email":    d.get("email") or "",
            "name":     d.get("name") or username,
            "blog":     d.get("blog") or "",
            "company":  (d.get("company") or "").strip("@"),
            "bio":      d.get("bio") or "",
            "location": d.get("location") or "",
            "twitter":  d.get("twitter_username") or "",
            "followers": d.get("followers", 0),
        }
    except Exception:
        return {}


async def _find_leads_impl(span_ctx=None) -> list:
    seen = set()
    leads = []

    async with httpx.AsyncClient() as client:
        for i, query in enumerate(SEARCH_QUERIES, 1):
            print(f"\n[{i}/{len(SEARCH_QUERIES)}] Suche: {query}")

            repos = await _search_repos(client, query)
            print(f"  → {len(repos)} Repos gefunden")

            for repo in repos:
                owner = repo["owner"]["login"]
                if owner in seen:
                    continue
                seen.add(owner)

                user = await _get_user(client, owner)
                await asyncio.sleep(0.3)   # Rate Limit freundlich

                lead = {
                    "github_user":      owner,
                    "name":             user.get("name", owner),
                    "email":            user.get("email", ""),
                    "twitter":          user.get("twitter", ""),
                    "company":          user.get("company", ""),
                    "location":         user.get("location", ""),
                    "bio":              user.get("bio", "")[:120],
                    "blog":             user.get("blog", ""),
                    "followers":        user.get("followers", 0),
                    "repo_name":        repo["name"],
                    "repo_url":         repo["html_url"],
                    "repo_description": (repo.get("description") or "")[:150],
                    "repo_stars":       repo.get("stargazers_count", 0),
                    "language":         repo.get("language") or "",
                    "outreach_status":  "new",
                    "email_subject":    "",
                    "email_body":       "",
                }
                leads.append(lead)
                email_tag = "✓ email" if lead["email"] else "— no email"
                print(f"  + {owner:<25} | {repo['name']:<30} | {email_tag}")

            await asyncio.sleep(1.5)  # zwischen Queries

    return leads


async def find_leads() -> list:
    if TRACING:
        agentlens.init(api_url=f"{AGENTLENS_URL}/ingest")

    print("=" * 55)
    print("  AgentLens — Lead Finder Agent")
    print("=" * 55)

    if TRACING:
        with trace_agent("lead_finder", input=f"{len(SEARCH_QUERIES)} queries") as trace:
            with trace.span("github_search", span_type="tool") as s:
                leads = await _find_leads_impl()
                s.set_output(f"{len(leads)} leads gefunden")
            trace.set_output(f"{len(leads)} leads, {sum(1 for l in leads if l['email'])} mit Email")
    else:
        leads = await _find_leads_impl()

    # CSV speichern
    if leads:
        OUTPUT_FILE.parent.mkdir(exist_ok=True)
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=leads[0].keys())
            writer.writeheader()
            writer.writerows(leads)

    with_email = sum(1 for l in leads if l["email"])
    print(f"\n{'=' * 55}")
    print(f"  Gesamt:      {len(leads)} Leads")
    print(f"  Mit E-Mail:  {with_email} Leads")
    print(f"  Gespeichert: {OUTPUT_FILE}")
    print(f"{'=' * 55}\n")
    return leads


if __name__ == "__main__":
    asyncio.run(find_leads())

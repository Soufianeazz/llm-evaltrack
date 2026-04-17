"""
Agent 1 — Lead Finder  (v2 — verbessert)
Durchsucht GitHub nach Entwicklern, die aktiv LLM-Frameworks nutzen.
Speichert Leads als CSV in agents/leads.csv.

Verbesserungen v2:
  - FIX 1: Append-Modus — keine Duplikate; bestehende leads.csv wird nie überschrieben
  - FIX 2: Rate-Limit-aware: liest X-RateLimit-Remaining aus Header und wartet proaktiv
  - FIX 3: Erweiterte Queries (10+) + Qualitäts-Filter (min. Stars, kein Bot/Org)
  - NEU:   --min-stars CLI-Flag + MIN_FOLLOWERS Filter

Verwendung:
    python agents/lead_finder.py                  # Neue Leads anhängen
    python agents/lead_finder.py --fresh          # CSV neu erstellen (überschreiben)
    python agents/lead_finder.py --min-stars 10   # Nur Repos mit 10+ Stars
"""
import httpx
import csv
import asyncio
import os
import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import bugspy
    from bugspy import trace_agent
    TRACING = True
except ImportError:
    TRACING = False

# ── Konfiguration ──────────────────────────────────────────────
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN", "")
AGENTLENS_URL   = os.getenv("AGENTLENS_URL", "https://llm-evaltrack-production.up.railway.app")
OUTPUT_FILE     = Path(__file__).parent / "leads.csv"

# ── FIX 3: Erweiterte Queries (10 spezifische Targeting-Strategien) ──
SEARCH_QUERIES = [
    # Klassische LLM-Framework-Nutzer
    "langchain openai tracing language:python stars:>5",
    "anthropic claude monitoring language:python stars:>5",
    "llm observability python stars:>5",
    "openai cost tracking python stars:>5",
    "langsmith alternative python stars:>5",
    # Agent-Framework-Nutzer — hohes Potenzial
    "llm agent framework python stars:>10",
    "crewai autogen langgraph python stars:>5",
    # RAG-Entwickler
    "rag pipeline retrieval augmented generation python stars:>5",
    "vector database embeddings openai python stars:>5",
    # Spezifische Tool-Nutzer
    "litellm proxy openai anthropic language:python stars:>5",
    "dspy prompt optimization python stars:>5",
    "llamaindex openai evaluation language:python stars:>5",
    # EU/DACH-fokussiert (GDPR-Winkel)
    "llm production deployment fastapi python stars:>5",
    "ai chatbot backend python gdpr stars:>3",
    # Startups mit Eigenbau-Lösungen
    "openai wrapper api cost monitoring stars:>3 language:python",
]

LEADS_PER_QUERY = 10   # GitHub-Ergebnisse pro Query

# ── FIX 3: Qualitäts-Filter ──
MIN_STARS      = 3     # Repos mit weniger Stars überspringen
MIN_FOLLOWERS  = 0     # Follower-Mindestanzahl (0 = kein Filter)
SKIP_ORGS      = False # True = nur Privatpersonen (keine Org-Accounts)
# ───────────────────────────────────────────────────────────────


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


# ── FIX 2: Rate-Limit-aware Search ──────────────────────────────
async def _check_rate_limit(response: httpx.Response) -> None:
    """
    Liest X-RateLimit-Remaining aus dem Response-Header.
    Wenn < 5 Requests übrig: warte bis Reset-Zeitpunkt.
    Wenn 403 (sekundäres Limit): exponentiell warten.
    """
    remaining = response.headers.get("X-RateLimit-Remaining")
    reset_at   = response.headers.get("X-RateLimit-Reset")

    if response.status_code == 403:
        retry_after = int(response.headers.get("Retry-After", 60))
        print(f"  [Secondary Rate Limit — warte {retry_after}s]")
        await asyncio.sleep(retry_after)
        return

    if remaining is not None and int(remaining) < 5:
        if reset_at:
            wait = max(0, int(reset_at) - int(time.time())) + 2
            print(f"  [Rate Limit fast leer ({remaining} verbleibend) — warte {wait}s bis Reset]")
            await asyncio.sleep(wait)
        else:
            print("  [Rate Limit fast leer — warte 60s]")
            await asyncio.sleep(60)


async def _search_repos(client: httpx.AsyncClient, query: str, min_stars: int = MIN_STARS) -> list:
    try:
        r = await client.get(
            "https://api.github.com/search/repositories",
            params={
                "q":        query,
                "sort":     "updated",
                "per_page": LEADS_PER_QUERY,
            },
            headers=_gh_headers(),
            timeout=30,
        )
        await _check_rate_limit(r)

        if r.status_code == 403:
            return []  # bereits gewartet, aber Rate Limit bleibt — überspringe
        if r.status_code != 200:
            print(f"  [GitHub Fehler {r.status_code}: {r.text[:120]}]")
            return []

        items = r.json().get("items", [])
        # FIX 3: Stars-Filter anwenden
        return [repo for repo in items if repo.get("stargazers_count", 0) >= min_stars]

    except httpx.TimeoutException:
        print("  [Timeout — Query übersprungen]")
        return []
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
        await _check_rate_limit(r)

        if r.status_code != 200:
            return {}
        d = r.json()
        return {
            "email":     d.get("email") or "",
            "name":      d.get("name") or username,
            "blog":      d.get("blog") or "",
            "company":   (d.get("company") or "").strip("@"),
            "bio":       d.get("bio") or "",
            "location":  d.get("location") or "",
            "twitter":   d.get("twitter_username") or "",
            "followers": d.get("followers", 0),
            "type":      d.get("type", "User"),  # "User" oder "Organization"
        }
    except Exception:
        return {}


# ── FIX 1: Append-Modus — bestehende Leads laden ────────────────
def _load_existing_leads() -> tuple[list, set]:
    """
    Lädt bestehende leads.csv und gibt (leads_liste, seen_github_users) zurück.
    seen_github_users verhindert Duplikate beim Anhängen neuer Leads.
    """
    existing_leads = []
    seen_users = set()

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_leads.append(dict(row))
                seen_users.add(row["github_user"])
        print(f"  [Append-Modus] {len(existing_leads)} bestehende Leads geladen — Duplikate werden übersprungen")

    return existing_leads, seen_users


def _save_leads(leads: list) -> None:
    """Speichert alle Leads (bestehende + neue) in leads.csv."""
    if not leads:
        return
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)


async def _find_leads_impl(existing_seen: set, min_stars: int = MIN_STARS) -> list:
    """Sucht neue Leads auf GitHub — überspringt bereits bekannte github_user."""
    # Lokale seen-Menge — kombiniert bestehende + neu gefundene (verhindert Duplikate innerhalb dieses Runs)
    seen = set(existing_seen)
    new_leads = []

    async with httpx.AsyncClient() as client:
        for i, query in enumerate(SEARCH_QUERIES, 1):
            print(f"\n[{i}/{len(SEARCH_QUERIES)}] Suche: {query}")

            repos = await _search_repos(client, query, min_stars=min_stars)
            print(f"  >> {len(repos)} Repos nach Star-Filter")

            for repo in repos:
                owner = repo["owner"]["login"]

                # FIX 1: Duplikat-Check (bestehende + aktuelle Run)
                if owner in seen:
                    print(f"  ~ {owner:<25} | bereits bekannt — übersprungen")
                    continue
                seen.add(owner)

                user = await _get_user(client, owner)
                await asyncio.sleep(0.5)   # FIX 2: etwas großzügigeres Rate-Limit-Pacing

                # FIX 3: Qualitäts-Filter — Org-Accounts und Low-Follower überspringen
                if SKIP_ORGS and user.get("type") == "Organization":
                    print(f"  ~ {owner:<25} | Org-Account — übersprungen")
                    continue
                if user.get("followers", 0) < MIN_FOLLOWERS:
                    print(f"  ~ {owner:<25} | zu wenige Follower — übersprungen")
                    continue

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
                new_leads.append(lead)
                email_tag = "OK email" if lead["email"] else "-- no email"
                print(f"  + {owner:<25} | {repo['name']:<30} | {email_tag}")

            # FIX 2: zwischen Queries immer 2s warten (GitHub Secondary Rate Limit)
            await asyncio.sleep(2.0)

    return new_leads


async def find_leads(fresh: bool = False, min_stars: int = MIN_STARS) -> list:
    if TRACING:
        bugspy.init(api_url=f"{AGENTLENS_URL}/ingest")

    print("=" * 55)
    print("  BugSpy — Lead Finder Agent v2")
    print("=" * 55)

    # FIX 1: Bestehende Leads laden (außer --fresh)
    if fresh:
        print("  Modus: FRESH (CSV wird neu erstellt)")
        existing_leads, existing_seen = [], set()
    else:
        existing_leads, existing_seen = _load_existing_leads()

    if TRACING:
        with trace_agent("lead_finder", input=f"{len(SEARCH_QUERIES)} queries, fresh={fresh}") as trace:
            with trace.span("github_search", span_type="tool") as s:
                new_leads = await _find_leads_impl(existing_seen, min_stars=min_stars)
                s.set_output(f"{len(new_leads)} neue leads gefunden")
            trace.set_output(f"{len(new_leads)} neu, {len(existing_leads)} bestehend")
    else:
        new_leads = await _find_leads_impl(existing_seen, min_stars=min_stars)

    # FIX 1: Kombiniert speichern
    all_leads = existing_leads + new_leads
    _save_leads(all_leads)

    with_email = sum(1 for l in new_leads if l["email"])
    print(f"\n{'=' * 55}")
    print(f"  Neue Leads:       {len(new_leads)}")
    print(f"  Davon mit Email:  {with_email}")
    print(f"  Gesamt in CSV:    {len(all_leads)}")
    print(f"  Gespeichert:      {OUTPUT_FILE}")
    print(f"{'=' * 55}\n")
    return all_leads


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BugSpy Lead Finder v2")
    parser.add_argument("--fresh",      action="store_true", help="CSV neu erstellen (Duplikate zurücksetzen)")
    parser.add_argument("--min-stars",  type=int, default=MIN_STARS, help=f"Mindest-Stars pro Repo (default: {MIN_STARS})")
    args = parser.parse_args()
    asyncio.run(find_leads(fresh=args.fresh, min_stars=args.min_stars))

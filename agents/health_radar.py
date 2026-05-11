"""
Health Radar — 3x/day full-spectrum scan of AgentLens infrastructure.

PURPOSE
-------
Detect functional, security, and quality regressions BEFORE Bibin (or any pilot
customer) hits them. Classify findings by severity and route them:
  CRITICAL  → GitHub Issue (labelled `radar:critical`) + SendGrid email
  HIGH      → GitHub Issue (`radar:high`)
  MEDIUM    → GitHub Issue (`radar:medium`), deduped against open issues
  NOTED     → printed only

DESIGN PRINCIPLE: DETECT, DO NOT AUTO-FIX. Every finding includes a clear
remediation suggestion in prose; humans decide whether and how to apply it.
The reasoning: pilot customer uptime is more valuable than the time saved
by autonomous code modifications, and the failure modes of unsupervised
auto-fix are catastrophic (silent regressions, wrong-direction fixes).

CHECKS (six categories)
-----------------------
1. Live HTTP probes — 12 production endpoints expected 2xx
2. /install and /uninstall hygiene — clean LF, bash shebang, no stale URLs
3. GitHub Actions workflow status — any workflow that failed in the last 24h
4. GHCR pilot image freshness — pilot-latest tag age
5. Static repo audit — CRLF in scripts, missing critical COPY directives,
   unguarded HTTP-client call sites
6. License + repo hygiene — LICENSE files present, README license section intact,
   pilot_state.json coherence

ENV
---
  AGENTLENS_URL          default https://www.agentlens.one
  AGENTLENS_DEMO_KEY     default al_demo_agentlens
  GITHUB_REPOSITORY      e.g. Soufianeazz/agentlens  (GH-Actions injects)
  GITHUB_TOKEN           needs issues: write           (GH-Actions injects)
  SENDGRID_API_KEY       for CRITICAL alerts
  SENDER_EMAIL           SendGrid verified sender
  OPS_EMAIL              alert recipient (Soufian)
  RADAR_DRY_RUN          if "1" → no issues created, no emails sent
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("radar")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
URL = os.environ.get("AGENTLENS_URL", "https://www.agentlens.one").rstrip("/")
DEMO_KEY = os.environ.get("AGENTLENS_DEMO_KEY", "al_demo_agentlens")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DRY_RUN = os.environ.get("RADAR_DRY_RUN", "") == "1"

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "NOTED")


@dataclass
class Finding:
    severity: str           # CRITICAL / HIGH / MEDIUM / NOTED
    category: str           # short tag for grouping (e.g. "endpoint", "ci", "static")
    title: str              # one-line summary
    detail: str             # multi-line context
    fix: str                # human-readable remediation suggestion
    signature: str = ""     # stable hash for dedup; auto-computed if empty

    def __post_init__(self):
        if not self.signature:
            raw = f"{self.category}|{self.title}".encode("utf-8")
            self.signature = hashlib.sha256(raw).hexdigest()[:16]


@dataclass
class RadarReport:
    findings: list[Finding] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)

    def add(self, severity: str, category: str, title: str, detail: str, fix: str) -> None:
        if severity not in SEVERITIES:
            raise ValueError(f"unknown severity: {severity}")
        self.findings.append(Finding(severity, category, title, detail, fix))

    def by_severity(self, sev: str) -> list[Finding]:
        return [f for f in self.findings if f.severity == sev]

    def counts(self) -> dict[str, int]:
        return {s: len(self.by_severity(s)) for s in SEVERITIES}


# ── Section 1: live HTTP probes ───────────────────────────────────────────────

LIVE_PROBES = [
    # (path, requires_demo_key, expected_codes, description)
    ("/healthz",                False, {200},      "liveness"),
    ("/",                       False, {200},      "landing page"),
    ("/dashboard",              False, {200, 302}, "dashboard html"),
    ("/traces.html",            False, {200},      "traces UI"),
    ("/debug.html",             False, {200},      "debug UI"),
    ("/compliance.html",        False, {200},      "compliance UI"),
    ("/requests/stats",         True,  {200},      "stats API"),
    ("/requests/trend",         True,  {200},      "trend API"),
    ("/requests/worst",         True,  {200},      "worst-quality API"),
    ("/traces?limit=5",         True,  {200},      "traces list API"),
    ("/debug/requests?limit=5", True,  {200},      "debug list API"),
    ("/install",                False, {200},      "self-host installer"),
    ("/uninstall",              False, {200},      "self-host uninstaller"),
]


def http_get(path: str, with_key: bool) -> tuple[int | str, bytes]:
    """Return (status-or-error-string, body-bytes)."""
    headers = {"User-Agent": "agentlens-radar/1.0"}
    if with_key:
        headers["X-API-Key"] = DEMO_KEY
    req = urllib.request.Request(f"{URL}{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read(8192)
    except urllib.error.HTTPError as e:
        return e.code, e.read(400)
    except Exception as e:
        return f"ERR:{type(e).__name__}", str(e).encode()[:400]


def check_live_endpoints(report: RadarReport) -> None:
    failures = []
    for path, with_key, expected, desc in LIVE_PROBES:
        status, body = http_get(path, with_key)
        if not (isinstance(status, int) and status in expected):
            failures.append((path, status, body[:200].decode("utf-8", errors="replace"), desc))
    if not failures:
        return
    # If multiple endpoints fail simultaneously, that's CRITICAL (likely outage)
    if len(failures) >= 3:
        detail = "\n".join(f"  {p}: {s} — {b}" for p, s, b, _ in failures)
        report.add(
            "CRITICAL", "outage",
            f"{len(failures)}/{len(LIVE_PROBES)} endpoints failing simultaneously",
            f"Endpoints failing:\n{detail}\n\nThis usually means Railway is down, the build "
            f"failed, or DNS is broken. Check Railway logs and the most recent deploy.",
            "1) Visit https://railway.com/project/joyful-perception → check deployment status. "
            "2) `railway logs` to see runtime crashes. 3) If recent commit broke build, revert.",
        )
        return
    # Otherwise per-endpoint HIGH
    for path, status, body, desc in failures:
        sev = "CRITICAL" if path in ("/healthz", "/install") else "HIGH"
        report.add(
            sev, "endpoint",
            f"{path} returned {status} ({desc})",
            f"Status: {status}\nBody (first 200 chars): {body}",
            f"Check the route handler for {path} in api/. Verify upstream services "
            "(DB, worker) are healthy. Reproduce locally with: "
            f"curl -sS{' -H \"X-API-Key: ...\"' if path.startswith(('/requests','/traces','/debug')) else ''} {URL}{path}",
        )


# ── Section 2: install/uninstall script hygiene ───────────────────────────────

def check_install_script_hygiene(report: RadarReport) -> None:
    for path in ("/install", "/uninstall"):
        status, body = http_get(path, False)
        if not (isinstance(status, int) and status == 200):
            continue  # already reported in Section 1
        # CRLF check
        if b"\r\n" in body or (b"\r" in body and b"\r\n" not in body):
            report.add(
                "CRITICAL", "install-script",
                f"{path} body contains CR characters",
                f"`curl ... | bash` will fail on Linux with $'\\r' errors. "
                f"This breaks every pilot install.",
                "Re-deploy after verifying scripts/*.sh are LF-only on the source. "
                "Add .gitattributes if not present. The /install handler should also "
                "call body.replace(b'\\r\\n', b'\\n').replace(b'\\r', b'\\n') defensively.",
            )
        # Bash shebang check
        if not body.startswith((b"#!/usr/bin/env bash", b"#!/bin/bash", b"#!/usr/bin/env sh")):
            report.add(
                "HIGH", "install-script",
                f"{path} does not start with a bash shebang",
                f"First 80 bytes: {body[:80]!r}",
                "Verify the source file is intact and the route handler returns the "
                "right file. Re-run release-pilot-image workflow if Dockerfile-side issue.",
            )
        # Stale-URL check
        if b"get.agentlens.one" in body:
            report.add(
                "HIGH", "install-script",
                f"{path} body still references unregistered get.agentlens.one",
                "Users following on-screen instructions will hit DNS NXDOMAIN.",
                "Replace with www.agentlens.one/install or /uninstall in the source script.",
            )


# ── Section 3: GitHub Actions workflow status ─────────────────────────────────

def gh_api(path: str) -> dict | list | None:
    """Unauthenticated GitHub API call (works for public repos)."""
    if not REPO:
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}{path}",
        headers={"User-Agent": "agentlens-radar/1.0", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.warning("gh_api %s failed: %s", path, e)
        return None


def check_workflow_status(report: RadarReport) -> None:
    data = gh_api("/actions/runs?per_page=50") or {}
    runs = data.get("workflow_runs", []) or []
    if not runs:
        return
    # Group by workflow name, take most recent
    latest_by_name: dict[str, dict] = {}
    for r in runs:
        n = r.get("name", "?")
        if n not in latest_by_name:
            latest_by_name[n] = r
    failed = [r for r in latest_by_name.values() if r.get("conclusion") == "failure"]
    if not failed:
        return
    for r in failed:
        name = r.get("name", "?")
        url = r.get("html_url", "")
        sha = (r.get("head_sha") or "")[:7]
        # Workflows that gate Bibin's image build are HIGH; ops alerts are MEDIUM
        critical_workflows = {"Release Pilot Image"}
        sev = "HIGH" if name in critical_workflows else "MEDIUM"
        report.add(
            sev, "ci",
            f"Workflow '{name}' last run FAILED (sha {sha})",
            f"URL: {url}",
            f"Open the run, read the failed step's log, and either fix the issue or "
            f"manually re-trigger the workflow if it was a flake.",
        )


# ── Section 4: GHCR pilot image freshness ─────────────────────────────────────

def check_ghcr_image_freshness(report: RadarReport) -> None:
    """Verify pilot-latest tag is recent (built within last 30 days)."""
    try:
        token_url = "https://ghcr.io/token?scope=repository:soufianeazz/agentlens:pull&service=ghcr.io"
        with urllib.request.urlopen(token_url, timeout=10) as resp:
            token = json.loads(resp.read())["token"]
        req = urllib.request.Request(
            "https://ghcr.io/v2/soufianeazz/agentlens/tags/list",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "agentlens-radar/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tags = json.loads(resp.read()).get("tags", []) or []
    except Exception as e:
        report.add(
            "MEDIUM", "ghcr",
            "Could not list GHCR tags",
            f"Error: {e}",
            "Verify ghcr.io/soufianeazz/agentlens is still public and the token endpoint works. "
            "If the registry is unreachable, customer install.sh will fail at `docker pull`.",
        )
        return
    if "pilot-latest" not in tags:
        report.add(
            "CRITICAL", "ghcr",
            "pilot-latest tag missing from GHCR",
            f"Tags present: {tags}",
            "install.sh pulls pilot-latest by default. Without it, every new pilot install fails. "
            "Trigger workflow_dispatch on release-pilot-image.yml to rebuild.",
        )
        return
    # Check date-stamped tags for the most recent one
    date_tags = sorted([t for t in tags if t.startswith("pilot-") and t != "pilot-latest"])
    if not date_tags:
        return
    most_recent = date_tags[-1]
    m = re.match(r"pilot-(\d{4})\.(\d{2})\.(\d{2})", most_recent)
    if not m:
        return
    import datetime as _dt
    tag_date = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    age_days = (_dt.date.today() - tag_date).days
    if age_days > 30:
        report.add(
            "MEDIUM", "ghcr",
            f"Most recent pilot tag is {age_days} days old ({most_recent})",
            f"All tags: {date_tags[-5:]}",
            "Stale pilot images may carry known bugs. Push a fresh commit or trigger "
            "release-pilot-image.yml manually with pilot_tag=pilot-YYYY.MM.DD",
        )


# ── Section 5: static repo audit ──────────────────────────────────────────────

def check_static_repo(report: RadarReport) -> None:
    # 5a: CRLF in shell scripts
    for sh in (REPO_ROOT / "scripts").glob("*.sh"):
        data = sh.read_bytes()
        if b"\r\n" in data:
            report.add(
                "CRITICAL", "static",
                f"{sh.relative_to(REPO_ROOT)} has CRLF line endings",
                "On-disk file contains \\r\\n. Even if Git LFS or autocrlf hides it, "
                "the file shipped to Linux containers via FileResponse will break bash.",
                "Run: python -c \"open(p,'wb').write(open(p,'rb').read().replace(b'\\\\r\\\\n',b'\\\\n'))\" "
                "for each affected file. Verify .gitattributes pins *.sh to LF.",
            )
    # 5b: Dockerfile must COPY scripts/
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8", errors="replace") if (REPO_ROOT / "Dockerfile").exists() else ""
    if dockerfile and "scripts" not in dockerfile:
        report.add(
            "CRITICAL", "static",
            "Dockerfile no longer COPYs scripts/ — /install will return 500",
            "The /install and /uninstall routes serve files from scripts/. If the "
            "Dockerfile lacks `COPY scripts ./scripts`, those routes return File-Not-Found.",
            "Add `COPY scripts ./scripts` between the other COPY directives in Dockerfile.",
        )
    # 5c: .gitattributes presence
    if not (REPO_ROOT / ".gitattributes").exists():
        report.add(
            "MEDIUM", "static",
            ".gitattributes missing",
            "Without .gitattributes, Windows checkouts can reintroduce CRLF into "
            "scripts/*.sh and break customer installs.",
            "Add .gitattributes with `*.sh text eol=lf` and `Dockerfile text eol=lf`.",
        )
    # 5d: LICENSE files presence
    for path in ("LICENSE", "agentlens/LICENSE", "LICENSING.md"):
        if not (REPO_ROOT / path).exists():
            report.add(
                "HIGH", "static",
                f"License artifact missing: {path}",
                "Required for the dual-license model (BSL server + MIT SDK).",
                f"Restore {path} from the last good commit or re-run the license-switch setup.",
            )


# ── Section 6: pilot state coherence ──────────────────────────────────────────

def check_pilot_state(report: RadarReport) -> None:
    pf = REPO_ROOT / "agents" / "pilot_state.json"
    if not pf.exists():
        report.add("MEDIUM", "pilot", "pilot_state.json missing", "", "")
        return
    try:
        state = json.loads(pf.read_text(encoding="utf-8"))
    except Exception as e:
        report.add("HIGH", "pilot", "pilot_state.json is invalid JSON", str(e),
                   "Restore from previous commit or recreate from agents/pilot_state.json template.")
        return
    contact = state.get("contact_email", "")
    if not contact or "REPLACE" in contact or "@" not in contact:
        report.add(
            "MEDIUM", "pilot",
            "pilot contact_email not set",
            f"Current value: {contact!r}",
            "After Bibin signs up, edit agents/pilot_state.json contact_email so "
            "customer-reminder emails can fire on Day 10/13/14/18.",
        )
    kickoff = state.get("kickoff_date_utc", "")
    if kickoff and "REPLACE" in kickoff:
        report.add(
            "NOTED", "pilot",
            "kickoff_date_utc not set yet (expected before pilot starts)",
            f"Current value: {kickoff!r}",
            "After kickoff call, set kickoff_date_utc to the call's end timestamp (ISO 8601).",
        )


# ── Reporting: GitHub Issue + Email ───────────────────────────────────────────

def post_github_issue(title: str, body: str, labels: list[str], signature: str) -> None:
    """Create a GitHub Issue with dedup. Skips if an open issue with the same
    signature already exists."""
    if DRY_RUN or not (REPO and GH_TOKEN):
        logger.info("[DRY-RUN] would post issue: %s", title)
        return
    # Dedup: search by signature marker in body
    marker = f"<!-- radar-signature: {signature} -->"
    search_url = (
        f"https://api.github.com/repos/{REPO}/issues?state=open&labels=radar:auto&per_page=100"
    )
    try:
        req = urllib.request.Request(
            search_url,
            headers={
                "Authorization": f"Bearer {GH_TOKEN}",
                "User-Agent": "agentlens-radar/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing = json.loads(resp.read())
        for iss in existing:
            if marker in (iss.get("body") or ""):
                logger.info("Dedup: open issue #%s already covers signature %s", iss["number"], signature)
                return
    except Exception as e:
        logger.warning("dedup search failed (%s) — proceeding to create", e)
    # Create
    payload = {
        "title": title,
        "body": body + "\n\n" + marker,
        "labels": labels + ["radar:auto"],
    }
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues",
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "User-Agent": "agentlens-radar/1.0",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            logger.info("Created issue #%s: %s", data["number"], title)
    except Exception:
        logger.exception("issue creation failed for: %s", title)


def send_email(subject: str, body: str) -> None:
    api_key = os.environ.get("SENDGRID_API_KEY")
    sender = os.environ.get("SENDER_EMAIL")
    recipient = os.environ.get("OPS_EMAIL")
    if DRY_RUN or not (api_key and sender and recipient):
        logger.info("[DRY-RUN/no-creds] would email: %s", subject)
        return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        msg = Mail(from_email=sender, to_emails=recipient, subject=subject, plain_text_content=body)
        SendGridAPIClient(api_key).send(msg)
        logger.info("Email sent: %s", subject)
    except Exception:
        logger.exception("SendGrid send failed: %s", subject)


def format_finding(f: Finding) -> str:
    return (
        f"### [{f.severity}] {f.title}\n"
        f"**Category:** `{f.category}`\n\n"
        f"**Detail:**\n```\n{f.detail}\n```\n\n"
        f"**Suggested fix:**\n{f.fix}\n"
    )


def dispatch_findings(report: RadarReport) -> None:
    crit = report.by_severity("CRITICAL")
    high = report.by_severity("HIGH")
    medium = report.by_severity("MEDIUM")

    # Email summary if any CRITICAL
    if crit:
        body_lines = [
            f"AgentLens Health Radar — {len(crit)} CRITICAL, {len(high)} HIGH, {len(medium)} MEDIUM",
            "",
        ]
        for f in crit + high:
            body_lines.append(f"[{f.severity}] {f.title}")
            body_lines.append(f"  → {f.fix}")
            body_lines.append("")
        send_email(
            f"[Radar] {len(crit)} CRITICAL finding(s) — AgentLens scan",
            "\n".join(body_lines),
        )

    # Create issues for CRITICAL + HIGH + MEDIUM (deduped)
    for f in crit + high + medium:
        labels = [f"radar:{f.severity.lower()}"]
        post_github_issue(
            title=f"[Radar] [{f.severity}] {f.title}",
            body=format_finding(f),
            labels=labels,
            signature=f.signature,
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logger.info("Radar scan starting against %s (dry_run=%s)", URL, DRY_RUN)
    report = RadarReport()

    check_live_endpoints(report)
    check_install_script_hygiene(report)
    check_workflow_status(report)
    check_ghcr_image_freshness(report)
    check_static_repo(report)
    check_pilot_state(report)

    counts = report.counts()
    logger.info("Scan complete: %s", counts)

    # Write structured report to disk (gitignored)
    radar_dir = REPO_ROOT / ".audit" / "radar"
    radar_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    report_path = radar_dir / f"radar-{ts}.md"
    lines = [
        f"# Health Radar — {ts} UTC",
        f"Target: {URL}",
        f"Counts: {counts}",
        "",
    ]
    for sev in SEVERITIES:
        sev_findings = report.by_severity(sev)
        if not sev_findings:
            continue
        lines.append(f"## {sev} ({len(sev_findings)})")
        lines.append("")
        for f in sev_findings:
            lines.append(format_finding(f))
            lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", report_path)

    dispatch_findings(report)

    # Exit code: non-zero only if there are CRITICAL findings, so cron stays
    # mostly green and we don't get alert fatigue from yellow runs.
    return 1 if report.by_severity("CRITICAL") else 0


if __name__ == "__main__":
    raise SystemExit(main())

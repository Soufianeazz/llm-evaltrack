# AgentLens Licensing — Plain-Language Guide

AgentLens uses a **dual-license** model that mirrors how Sentry, MongoDB, and
Sourcegraph license their server software.

## TL;DR

| Component | License | What it means |
|---|---|---|
| **Python SDK** (`agentlens/` directory, `pip install agentlens-monitor`) | **MIT** | Use it anywhere, in any product, commercial or not. No restrictions. |
| **Server** (everything else: `api/`, `pipeline/`, `storage/`, `evaluation/`, `dashboard/`) | **Business Source License 1.1** | Free for almost everything except offering AgentLens-as-a-Service to third parties. |

The server license **converts to Apache 2.0 on 2030-05-11** (4 years from
publication — standard BSL clause).

---

## What can I do with the AgentLens server (BSL)?

### YES — these are always free under BSL

- ✅ **Self-host AgentLens to monitor your own LLM applications** (the most
  common use case — internal observability for your team's products)
- ✅ **Modify the source** to fit your needs
- ✅ **Run it in air-gapped or on-premise environments** for your company
- ✅ **Use it for as many internal LLM apps as you want, no per-seat counting**
- ✅ **Distribute modified versions** internally or to evaluation partners
- ✅ **Use it in client work / consulting** to instrument LLM apps you build for
  customers (as long as you're not packaging AgentLens itself as the deliverable)

### NO — these require a commercial license from us

- ❌ **Offer AgentLens (or a fork of it) as a hosted SaaS service** to third
  parties — i.e. sign up customers, charge them, and run AgentLens on their
  behalf. That competes directly with our hosted offering.
- ❌ **White-label AgentLens and resell it** as your own observability product.
- ❌ **Bundle AgentLens with another product you sell** as a value-add
  observability layer (OEM use).

If any of these "NO" cases describe what you want to do, contact
**soufian.azzaoui48@gmail.com** for a commercial license. There is one — the
BSL is designed exactly to make this conversation easy.

---

## What about the Python SDK?

**Pure MIT, no restrictions.** If you import `agentlens` in your application
code (`pip install agentlens-monitor`), you can do anything with it — including
shipping it inside your own commercial product. The SDK is the open distribution
layer; no part of the BSL applies to your application code.

---

## Why this split?

We want **maximum adoption** of the SDK so AgentLens can be the easy default
choice for LLM observability in any Python codebase. We also want a
**sustainable business** so AgentLens can keep being maintained, supported,
and improved — which means we cannot let well-funded competitors (think
hyperscalers or other SaaS vendors) take our open-source server code, package
it as their own hosted product, and undercut the company that built it.

This is exactly the trade-off that **MongoDB (SSPL)**, **Sentry (BSL)**,
**Cockroach (BSL)**, **Elastic (Elastic License)**, and **Sourcegraph (FSL)**
made — and it's why those companies still exist as healthy independent
businesses funding their own development.

---

## What about the BSL "production use" question?

The BSL standard text restricts production use unless the Licensor grants an
"Additional Use Grant". **Our Additional Use Grant explicitly permits
production use** for any purpose EXCEPT offering the Licensed Work as a
competing commercial service.

Plain English: **if you're using AgentLens to watch your own LLM apps in
production, you're fine.** The restriction only kicks in if you're trying to
become an AgentLens-hosting business.

---

## Plan-tier features (separate from the license)

The license governs what you can do with the **source code**. The
**plan-tier features** (Free / Starter / Team / Scale / Enterprise) are
separate — they're enforced server-side per API key:

| Plan | Price | What you get |
|---|---:|---|
| Free | €0 | Ingest API + Basic Stats (24h) |
| Starter | €299/mo | + Prompt Debugger |
| Team | €999/mo | + Agent Debugger + Advanced Analytics |
| Scale | €2,999/mo | + Compliance / GDPR workflows + Audit log |
| Enterprise | €5,000+/mo | + Private Deploy + SLA + Security Package |

**You can run a self-hosted AgentLens for free under the BSL** — but the paid
features (Prompt Debugger, Agent Debugger, etc.) are gated by your AgentLens
plan tier, not by the license. To unlock them in a self-hosted deployment, you
register your instance against an active paid plan.

---

## Pilot programs

Qualified teams can request a **14-day full-feature pilot** (every paid
feature unlocked) at no cost before committing to a paid tier. After the
pilot ends with a 7-day grace period, the API key reverts to free-tier
features unless converted to a paid plan. Contact us at
**soufian.azzaoui48@gmail.com** to request a pilot.

---

## Questions

- License questions, alternative licensing arrangements, OEM:
  **soufian.azzaoui48@gmail.com**
- General inquiries: https://www.agentlens.one
- Issues / bug reports: https://github.com/Soufianeazz/agentlens/issues

---

*This document is informational. The legally binding terms are in `LICENSE`
(BSL 1.1 for the server) and `agentlens/LICENSE` (MIT for the SDK). When in
doubt, those files govern.*

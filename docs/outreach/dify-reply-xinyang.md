# Dify Reply — Xinyang Zhang (DevRel)
# To: support@dify.ai
# Subject: Re: AgentLens x Dify — native observability integration

Hi Xinyang,

Thanks for getting back to me — I'll be direct.

I'm proposing a native integration: a lightweight AgentLens callback for Dify workflow nodes, so Dify users get full LLM observability (traces, costs, hallucination flags, GDPR export) without leaving their self-hosted setup.

Concretely, what I'd ship:

1. A Python hook that wraps Dify workflow nodes with `agentlens.trace()` — one import, zero config change
2. A joint blog post: "Root-cause a Dify workflow failure in under 5 minutes"
3. A listing in Dify's integrations/observability section

Why this makes sense for Dify users specifically: AgentLens is self-hosted by default and has a built-in air-gap mode (no outbound traffic from their data). That's a natural fit for the Dify community — teams that chose Dify precisely because they want to run everything on their own infrastructure.

No money asked. I do the work on my side (~1 week), you get a relevant integration for your self-host users.

Happy to jump on a 20-min call, or I can just ship a POC first and show you — whatever's faster for you.

— Soufiane
AgentLens · https://www.agentlens.one

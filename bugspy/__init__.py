"""
AgentLens — LLM observability, quality scoring, and agent debugging.

Quick start:
    import bugspy
    agentlens.init(api_url="http://localhost:8000")
    agentlens.patch_openai()    # auto-track all openai calls
    agentlens.patch_anthropic() # auto-track all anthropic calls
"""
from bugspy.tracker import init, track_llm_call
from bugspy.integrations.openai import patch as patch_openai
from bugspy.integrations.anthropic import patch as patch_anthropic
from bugspy.tracing import trace_agent, span

__all__ = [
    "init",
    "track_llm_call",
    "patch_openai",
    "patch_anthropic",
    "trace_agent",
    "span",
]
__version__ = "0.2.0"

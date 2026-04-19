"""
llm-observe — Drop-in observability for LLM applications.

Quick start:
    import llm_observe
    llm_observe.init(api_url="http://localhost:8000")
    llm_observe.patch_openai()    # auto-track all openai calls
    llm_observe.patch_anthropic() # auto-track all anthropic calls

LangChain:
    from llm_observe.integrations.langchain import AgentLensCallbackHandler
    handler = AgentLensCallbackHandler()
    chain.invoke({"input": "..."}, config={"callbacks": [handler]})
"""
from llm_observe.tracker import init, track_llm_call
from llm_observe.integrations.openai import patch as patch_openai
from llm_observe.integrations.anthropic import patch as patch_anthropic
from llm_observe.tracing import trace_agent, span

__all__ = [
    "init",
    "track_llm_call",
    "patch_openai",
    "patch_anthropic",
    "trace_agent",
    "span",
]
__version__ = "0.4.0"

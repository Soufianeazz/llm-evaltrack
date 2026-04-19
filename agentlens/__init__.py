"""
AgentLens — LLM observability, quality scoring, and agent debugging.

Quick start:
    import agentlens
    agentlens.init(api_url="http://localhost:8000")
    agentlens.patch_openai()    # auto-track all openai calls
    agentlens.patch_anthropic() # auto-track all anthropic calls

LangChain:
    from agentlens.integrations.langchain import AgentLensCallbackHandler
    handler = AgentLensCallbackHandler()
    chain.invoke({"input": "..."}, config={"callbacks": [handler]})

LlamaIndex:
    from agentlens.integrations.llama_index import AgentLensLlamaIndexHandler
    from llama_index.core import Settings
    from llama_index.core.callbacks import CallbackManager
    Settings.callback_manager = CallbackManager([AgentLensLlamaIndexHandler()])
"""
from agentlens.tracker import init, track_llm_call
from agentlens.integrations.openai import patch as patch_openai
from agentlens.integrations.anthropic import patch as patch_anthropic
from agentlens.tracing import trace_agent, span

__all__ = [
    "init",
    "track_llm_call",
    "patch_openai",
    "patch_anthropic",
    "trace_agent",
    "span",
]
__version__ = "0.4.1"

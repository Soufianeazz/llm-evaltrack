"""
llm-observe — Drop-in observability for LLM applications.

Quick start:
    import llm_observe
    llm_observe.init(api_url="http://localhost:8000")
    llm_observe.patch_openai()    # auto-track all openai calls
    llm_observe.patch_anthropic() # auto-track all anthropic calls
"""
from llm_observe.tracker import init, track_llm_call
from llm_observe.integrations.openai import patch as patch_openai
from llm_observe.integrations.anthropic import patch as patch_anthropic

__all__ = [
    "init",
    "track_llm_call",
    "patch_openai",
    "patch_anthropic",
]
__version__ = "0.1.0"

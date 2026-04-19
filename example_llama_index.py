"""
AgentLens ↔ LlamaIndex integration example.

Install:
    pip install agentlens-monitor llama-index-core llama-index-llms-openai

Run:
    export OPENAI_API_KEY=sk-...
    python example_llama_index.py
"""
from __future__ import annotations

import os

import llm_observe
from llm_observe.integrations.llama_index import AgentLensLlamaIndexHandler


def main() -> None:
    llm_observe.init(
        api_url=os.getenv("AGENTLENS_URL", "http://localhost:8000/ingest"),
    )

    from llama_index.core import Settings, Document, VectorStoreIndex
    from llama_index.core.callbacks import CallbackManager

    Settings.callback_manager = CallbackManager([AgentLensLlamaIndexHandler(trace_name="example_rag")])

    docs = [Document(text="LLM observability tools capture inputs, outputs, latency, and cost.")]
    index = VectorStoreIndex.from_documents(docs)
    query_engine = index.as_query_engine()
    answer = query_engine.query("What do LLM observability tools capture?")
    print("Answer:", answer)


if __name__ == "__main__":
    main()

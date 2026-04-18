"""
AgentLens ↔ LangChain integration example.

Runs a tiny LangChain agent with the AgentLens callback handler.
Every LLM call, tool call, and chain step is streamed to your
AgentLens dashboard as a span in a single trace.

Install:
    pip install agentlens-monitor langchain langchain-openai

Run:
    export OPENAI_API_KEY=sk-...
    python example_langchain.py

Open the trace at: https://your-agentlens/traces.html
"""
from __future__ import annotations

import os

import llm_observe
from llm_observe.integrations.langchain import AgentLensCallbackHandler


def main() -> None:
    # 1. Configure AgentLens (point this at your deployment)
    llm_observe.init(
        api_url=os.getenv("AGENTLENS_URL", "http://localhost:8000/ingest"),
    )

    # 2. Build any LangChain pipeline — a simple chain here
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a concise technical assistant."),
        ("user", "{question}"),
    ])
    chain = prompt | llm | StrOutputParser()

    # 3. Attach the AgentLens callback — one line
    handler = AgentLensCallbackHandler(trace_name="example_qa_chain")

    # 4. Run the chain — every step shows up in the AgentLens trace view
    answer = chain.invoke(
        {"question": "What is LLM observability in one sentence?"},
        config={"callbacks": [handler]},
    )
    print("Answer:", answer)


if __name__ == "__main__":
    main()

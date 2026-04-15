from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class BudgetAlert(Base):
    __tablename__ = "budget_alerts"

    id = Column(String, primary_key=True, default="default")
    daily_budget_usd = Column(Float, nullable=False)
    webhook_url = Column(String, nullable=True)
    email = Column(String, nullable=True)
    triggered_today = Column(Boolean, default=False)
    last_triggered = Column(Float, nullable=True)  # unix epoch


class Request(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    timestamp = Column(Float, nullable=False, index=True)

    evaluation = relationship("Evaluation", back_populates="request", uselist=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True)
    action = Column(String, nullable=False)  # export, delete, retention_run, policy_change
    detail = Column(Text, nullable=True)
    timestamp = Column(Float, nullable=False, index=True)


class RetentionPolicy(Base):
    __tablename__ = "retention_policy"

    id = Column(String, primary_key=True, default="default")
    retention_days = Column(Float, nullable=False)  # delete data older than X days
    enabled = Column(Boolean, default=True)
    last_run = Column(Float, nullable=True)


class Trace(Base):
    """One agent run — contains multiple spans (steps)."""
    __tablename__ = "traces"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)  # e.g. "research_agent", "booking_flow"
    status = Column(String, nullable=False, default="running")  # running, completed, failed
    input = Column(Text, nullable=True)  # initial user input
    output = Column(Text, nullable=True)  # final agent output
    total_tokens = Column(Float, default=0)
    total_cost_usd = Column(Float, default=0)
    total_duration_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    started_at = Column(Float, nullable=False, index=True)
    ended_at = Column(Float, nullable=True)

    spans = relationship("Span", back_populates="trace", order_by="Span.started_at")


class Span(Base):
    """One step in an agent run — LLM call, tool call, decision, etc."""
    __tablename__ = "spans"

    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    parent_span_id = Column(String, nullable=True)  # for nested spans
    name = Column(String, nullable=False)  # e.g. "llm_call", "tool:search", "decision"
    span_type = Column(String, nullable=False)  # llm, tool, retrieval, decision, custom
    status = Column(String, nullable=False, default="running")  # running, completed, failed
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    model = Column(String, nullable=True)  # only for LLM spans
    tokens = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)
    duration_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    started_at = Column(Float, nullable=False)
    ended_at = Column(Float, nullable=True)

    trace = relationship("Trace", back_populates="spans")


class Evaluation(Base):
    __tablename__ = "evaluations"

    request_id = Column(String, ForeignKey("requests.id"), primary_key=True)
    quality_score = Column(Float, nullable=False, index=True)
    hallucination_score = Column(Float, nullable=False)
    flags = Column(JSON, default=list)
    score_explanation = Column(Text)

    request = relationship("Request", back_populates="evaluation")

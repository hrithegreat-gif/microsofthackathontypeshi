# models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


# ─── Sub-schemas used inside TaskLedger ───────────────────────────────────────

class GuardrailEntry(BaseModel):
    """Recorded every time the Director warns the user about a risky choice."""
    risk_type: str                  # e.g. "no_auth", "plaintext_creds"
    recommendation: str             # What the Director suggested instead
    user_decision: str              # "override" | "accepted_recommendation"
    timestamp: str                  # ISO 8601 datetime string


class NonFunctionalRequirements(BaseModel):
    """Performance, reliability, and cost expectations."""
    performance_sla: Optional[str] = None    # e.g. "< 200ms response time"
    availability: Optional[str] = None       # e.g. "99.9% uptime"
    budget_usd_per_month: Optional[float] = None
    max_concurrent_users: Optional[int] = None


class TechConstraints(BaseModel):
    """What the user wants or doesn't want in the stack."""
    preferred_language: Optional[str] = None    # e.g. "Python", "TypeScript"
    preferred_framework: Optional[str] = None   # e.g. "FastAPI", "Next.js"
    preferred_database: Optional[str] = None    # e.g. "PostgreSQL", "MongoDB"
    forbidden_services: list[str] = []          # e.g. ["AWS", "Firebase"]
    cloud_provider: str = "Azure"


class RevisionEntry(BaseModel):
    """One entry every time the Task Ledger is changed after creation."""
    changed_by: str                 # User ID or "director"
    change_type: str                # "COSMETIC" | "STRUCTURAL" | "CORRECTION"
    field_changed: str              # Which field was updated
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ─── Main Task Ledger ──────────────────────────────────────────────────────────

class TaskLedger(BaseModel):
    """
    The single source of truth for an entire project build.
    Created during Stage 1 (Director clarification).
    Read by every agent throughout the pipeline.
    """

    # Identity
    project_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    owner_id: str = "default_user"      # Azure AD identity in production

    # Core requirements — filled by Director during clarification loop
    user_intent: str                    # Raw plain-language description from user
    functional_requirements: list[str] = []
    # e.g. ["User can register and log in",
    #        "User can create, edit, delete tasks",
    #        "Tasks have title, description, due date, priority"]

    non_functional_requirements: NonFunctionalRequirements = Field(
        default_factory=NonFunctionalRequirements
    )

    tech_constraints: TechConstraints = Field(
        default_factory=TechConstraints
    )

    integration_targets: list[str] = []
    # e.g. ["SendGrid for email", "Stripe for payments", "GitHub OAuth"]

    # Safety and audit fields
    guardrail_overrides: list[GuardrailEntry] = []
    # Populated whenever user overrides a Director warning

    revision_history: list[RevisionEntry] = []
    # Full log of every change made after initial creation

    # Lifecycle status
    status: str = "DRAFT"
    # DRAFT           — Director is still asking clarifying questions
    # VALIDATED       — Validator Agent has checked it, no blockers found
    # AEG_APPROVED    — User approved the execution graph, build can start
    # BUILDING        — Agents are currently executing
    # COMPLETE        — Build finished successfully
    # FAILED          — Build failed, see revision_history for details

    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ─── AEG schemas (needed by Dev 2 scheduler) ──────────────────────────────────

class AgentNode(BaseModel):
    """One agent in the execution graph."""
    agent_id: str                           # Unique ID e.g. "backend_engineer_1"
    role: str                               # e.g. "Backend Engineer"
    inputs: list[str] = []                  # What it needs from upstream agents
    outputs: list[str] = []                 # What it produces for downstream agents
    token_budget: int = 30000
    model_preference: str = "gpt-4o-mini"
    status: str = "PENDING"
    # PENDING | RUNNING | COMPLETED | FAILED | SLEEPING | RATE_LIMITED
    pending_since: Optional[str] = None     # ISO timestamp — used for starvation check
    priority: str = "NORMAL"               # NORMAL | ELEVATED


class AEGEdge(BaseModel):
    """A dependency between two agents."""
    from_agent: str     # Agent that produces the output
    to_agent: str       # Agent that needs that output
    # Note: field is "from_agent" not "from" — "from" is a reserved Python keyword


class AEG(BaseModel):
    """The full execution plan — a directed acyclic graph of agents."""
    aeg_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    nodes: list[AgentNode]
    edges: list[AEGEdge]
    status: str = "PENDING_APPROVAL"
    # PENDING_APPROVAL | APPROVED | EXECUTING | COMPLETED | FAILED
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
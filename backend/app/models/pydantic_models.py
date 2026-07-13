"""API request/response schemas."""
from typing import Any, Optional

from pydantic import BaseModel


# ---- Copilot ----
class CopilotQuery(BaseModel):
    query: str
    equipment_filter: list[str] = []
    language: str = "en"
    include_knowledge_capsules: bool = True
    confidence_threshold: str = "MEDIUM"


class Citation(BaseModel):
    doc_id: str
    page: int = 1
    excerpt: str = ""


class CopilotAnswer(BaseModel):
    answer: str
    confidence: str
    citations: list[Citation] = []
    related_entities: list[str] = []
    knowledge_capsules: list[dict] = []
    graph_nodes_highlighted: list[str] = []
    response_time_ms: int


class FeedbackIn(BaseModel):
    query_log_id: int
    feedback: int  # 1 or -1


# ---- Compliance ----
class ComplianceCheckRequest(BaseModel):
    procedure_id: str            # indexed doc file_id or Neo4j proc_id
    regulation_ids: list[str] = []   # empty = auto-suggest


class ComplianceGap(BaseModel):
    severity: str                # CRITICAL / MODERATE / MINOR
    status: str                  # NON_COMPLIANT / PARTIAL
    regulation_clause: str
    regulation_ref: str
    procedure_text: str
    risk: str
    recommended_action: str


class ComplianceReport(BaseModel):
    check_id: str
    procedure_id: str
    regulations_checked: list[str]
    summary: dict
    gaps: list[ComplianceGap]
    report_text: str


# ---- Preservation ----
class SessionStart(BaseModel):
    expert_name: str
    equipment_focus: str = ""


class InsightDecision(BaseModel):
    insight_index: int
    action: str                  # approve / edit / reject
    edited_text: Optional[str] = None
    category: Optional[str] = None
    linked_equipment: Optional[str] = None
    notes: str = ""


class ApproveRequest(BaseModel):
    decisions: list[InsightDecision]
    verified_by: str


# ---- Graph ----
class GraphQueryRequest(BaseModel):
    cypher: str
    params: dict[str, Any] = {}

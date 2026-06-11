"""
document_agent.py — LangGraph-based Document Analysis Agent.

Graph: classify → conditional → extract → reason → plan → draft → END

Conditional after classify:
  • confidence < 60 AND retry_count < 2  →  increment retry_count, loop
    back to classify (no separate retry node)
  • otherwise  →  proceed to extract

Public API:
    analyze_document(text: str) -> list[StepResult]
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.base import StepResult, invoke_llm, parse_kv
from app.agents.prompts.document import (
    CLASSIFY_PROMPT,
    DRAFT_PROMPT,
    EXTRACT_PROMPT,
    PLAN_PROMPT,
    REASON_PROMPT,
)


# ── Agent State ────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    document_text: str
    doc_type: str
    legal_domain: str
    confidence: int
    retry_count: int
    extracted_facts: str
    reasoning: str
    action_plan: str
    response_letter: str
    steps_log: list


# ── Classify Node ──────────────────────────────────────────────────────────

_CLASSIFY_KEYS: list[str] = ["DOC_TYPE", "LEGAL_DOMAIN", "CONFIDENCE", "REASONING"]
_CLASSIFY_DEFAULTS: dict = {
    "DOC_TYPE": "Unknown",
    "LEGAL_DOMAIN": "Other",
    "CONFIDENCE": "50",
    "REASONING": "",
}


def _safe_int(value: str, fallback: int = 0) -> int:
    """Extract an integer from *value*, returning *fallback* on failure."""
    try:
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else fallback
    except Exception:
        return fallback


def classify_node(state: AgentState) -> AgentState:
    """
    Classify the document.  On a retry pass (retry_count > 0) the node
    automatically uses more document context.
    """
    # Use broader context on retries
    char_limit = 2000 if state["retry_count"] == 0 else 4000
    text = state["document_text"][:char_limit]

    raw = invoke_llm(
        system=CLASSIFY_PROMPT,
        user=f"Classify this document:\n{text}",
    )

    data = parse_kv(raw, _CLASSIFY_KEYS, _CLASSIFY_DEFAULTS)
    confidence = _safe_int(data["CONFIDENCE"], fallback=50)

    state["doc_type"] = data["DOC_TYPE"]
    state["legal_domain"] = data["LEGAL_DOMAIN"]
    state["confidence"] = confidence

    step_label = "1_classify" if state["retry_count"] == 0 else f"1_classify_retry_{state['retry_count']}"
    state["steps_log"].append(
        StepResult(
            step=step_label,
            title="Document Classification",
            content=(
                f"**Type:** {state['doc_type']}\n"
                f"**Legal Domain:** {state['legal_domain']}\n"
                f"**Confidence:** {confidence}%\n"
                f"**Reasoning:** {data['REASONING']}"
            ),
            confidence=confidence,
        )
    )
    return state


# ── Conditional Router ─────────────────────────────────────────────────────

def _classify_router(state: AgentState) -> Literal["classify", "extract"]:
    """
    If confidence is below threshold and retries remain, bump
    retry_count and route back to classify.  Otherwise proceed.
    """
    if state["confidence"] < 60 and state["retry_count"] < 2:
        state["retry_count"] += 1
        state["steps_log"].append(
            StepResult(
                step="retry_notice",
                title="Agent Decision: Low Confidence — Retrying",
                content=(
                    f"Confidence was {state['confidence']}%. "
                    "Re-analysing with broader context."
                ),
                confidence=state["confidence"],
            )
        )
        return "classify"
    return "extract"


# ── Extract Node ───────────────────────────────────────────────────────────

def extract_node(state: AgentState) -> AgentState:
    """Extract key legal facts from the document."""
    domain_hints: dict[str, str] = {
        "RTI": "Focus on: applicant, public authority, information requested, deadlines.",
        "Tenant_Rights": "Focus on: landlord, tenant, rent amount, notice period, violations.",
        "Income_Certificate": "Focus on: certificate holder, income amount, issuing authority, validity.",
        "Land_Records": "Focus on: plot number, owner, area, disputes, encumbrances.",
        "Court_Notice": "Focus on: case number, court, parties, hearing date, charges.",
        "Employment": "Focus on: employer, employee, role, terms, violations.",
        "Other": "Focus on: all parties, dates, key claims, obligations.",
    }
    hint = domain_hints.get(state["legal_domain"], domain_hints["Other"])

    result = invoke_llm(
        system=f"{EXTRACT_PROMPT}\n{hint}",
        user=f"Document type: {state['doc_type']}\nDocument text:\n{state['document_text'][:3000]}",
    )

    state["extracted_facts"] = result
    state["steps_log"].append(
        StepResult(
            step="2_extract",
            title="Key Facts Extracted",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


# ── Reason Node ────────────────────────────────────────────────────────────

def reason_node(state: AgentState) -> AgentState:
    """Perform deep legal reasoning based on domain."""
    domain_laws: dict[str, str] = {
        "RTI": "RTI Act 2005 — § 7 (30-day response), § 8 (exemptions), § 19 (appeals)",
        "Tenant_Rights": "Transfer of Property Act 1882, Rent Control Acts, state tenancy laws",
        "Income_Certificate": "IT Act 2000 (digital signatures), Maharashtra Regulation Act 2000",
        "Land_Records": "Registration Act 1908, Land Acquisition Act, state revenue codes",
        "Court_Notice": "CPC 1908, CrPC, relevant IPC sections",
        "Employment": "Industrial Disputes Act, Labour Laws, Contract Act 1872",
        "Other": "Indian Constitution, relevant IPC sections, state-specific laws",
    }
    laws = domain_laws.get(state["legal_domain"], domain_laws["Other"])

    result = invoke_llm(
        system=f"{REASON_PROMPT}\nRelevant laws: {laws}",
        user=(
            f"Document type: {state['doc_type']}\n"
            f"Legal domain: {state['legal_domain']}\n"
            f"Extracted facts:\n{state['extracted_facts']}"
        ),
    )

    state["reasoning"] = result
    state["steps_log"].append(
        StepResult(
            step="3_reason",
            title="Legal Reasoning & Rights Analysis",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


# ── Plan Node ──────────────────────────────────────────────────────────────

def plan_node(state: AgentState) -> AgentState:
    """Generate a domain-specific action plan."""
    result = invoke_llm(
        system=PLAN_PROMPT,
        user=(
            f"Legal domain: {state['legal_domain']}\n"
            f"Legal analysis:\n{state['reasoning']}\n\n"
            "Create the action plan:"
        ),
    )

    state["action_plan"] = result
    state["steps_log"].append(
        StepResult(
            step="4_plan",
            title="Action Plan",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


# ── Draft Node ─────────────────────────────────────────────────────────────

def draft_node(state: AgentState) -> AgentState:
    """Draft a formal legal response letter."""
    result = invoke_llm(
        system=DRAFT_PROMPT,
        user=(
            f"Document type: {state['doc_type']}\n"
            f"Action plan context:\n{state['action_plan']}\n\n"
            "Draft the letter:"
        ),
    )

    state["response_letter"] = result
    state["steps_log"].append(
        StepResult(
            step="5_draft",
            title="Draft Response Letter",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


# ── Build & Compile Graph ─────────────────────────────────────────────────

def _build_document_graph() -> object:
    """
    classify → conditional → extract → reason → plan → draft → END

    No separate retry node — classify itself adapts on re-entry via
    retry_count.
    """
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("reason", reason_node)
    graph.add_node("plan", plan_node)
    graph.add_node("draft", draft_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        _classify_router,
        {
            "classify": "classify",  # retry loop
            "extract": "extract",
        },
    )

    graph.add_edge("extract", "reason")
    graph.add_edge("reason", "plan")
    graph.add_edge("plan", "draft")
    graph.add_edge("draft", END)

    return graph.compile()


_agent = _build_document_graph()


# ── Public API ─────────────────────────────────────────────────────────────

def analyze_document(text: str) -> list[StepResult]:
    """
    Run the full document-analysis pipeline and return the steps log.

    Parameters
    ----------
    text : str
        The raw document text to analyse.

    Returns
    -------
    list[StepResult]
        Ordered list of step results produced by the agent.
    """
    initial_state: AgentState = {
        "document_text": text,
        "doc_type": "",
        "legal_domain": "",
        "confidence": 0,
        "retry_count": 0,
        "extracted_facts": "",
        "reasoning": "",
        "action_plan": "",
        "response_letter": "",
        "steps_log": [],
    }

    final_state = _agent.invoke(initial_state)
    return final_state["steps_log"]

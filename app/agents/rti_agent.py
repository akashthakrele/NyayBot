"""
rti_agent.py — LangGraph-based RTI (Right to Information) Agent.

Graph: assess → conditional → two paths:
  Path A (rti_applicable=True AND confidence ≥ 60):
      legal_basis → draft → filing → END
  Path B (rti_applicable=False OR confidence < 60):
      alternate → END

Public API:
    analyze_rti(problem: str) -> list[StepResult]
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.base import StepResult, invoke_llm, parse_kv
from app.agents.prompts.rti import (
    ALTERNATE_PROMPT,
    ASSESS_PROMPT,
    DRAFT_RTI_PROMPT,
    FILING_PROMPT,
    LEGAL_BASIS_PROMPT,
)


# ── Agent State ────────────────────────────────────────────────────────────
class RTIState(TypedDict):
    problem: str
    rti_applicable: bool
    confidence: int
    department: str
    information_needed: str
    legal_basis: str
    application_draft: str
    filing_instructions: str
    steps_log: list


# ── Helpers ────────────────────────────────────────────────────────────────

_ASSESS_KEYS: list[str] = [
    "RTI_APPLICABLE",
    "CONFIDENCE",
    "DEPARTMENT",
    "INFORMATION_NEEDED",
    "REASONING",
]
_ASSESS_DEFAULTS: dict = {
    "RTI_APPLICABLE": "NO",
    "CONFIDENCE": "50",
    "DEPARTMENT": "Unknown",
    "INFORMATION_NEEDED": "",
    "REASONING": "",
}


def _safe_int(value: str, fallback: int = 0) -> int:
    """Extract an integer from *value*, returning *fallback* on failure."""
    try:
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else fallback
    except Exception:
        return fallback


# ── Assess Node ────────────────────────────────────────────────────────────

def assess_node(state: RTIState) -> RTIState:
    """Evaluate whether the problem is suitable for an RTI application."""
    raw = invoke_llm(
        system=ASSESS_PROMPT,
        user=f"Citizen's problem:\n{state['problem']}",
    )

    data = parse_kv(raw, _ASSESS_KEYS, _ASSESS_DEFAULTS)

    applicable = data["RTI_APPLICABLE"].strip().upper() == "YES"
    confidence = _safe_int(data["CONFIDENCE"], fallback=50)

    state["rti_applicable"] = applicable
    state["confidence"] = confidence
    state["department"] = data["DEPARTMENT"]
    state["information_needed"] = data["INFORMATION_NEEDED"]

    state["steps_log"].append(
        StepResult(
            step="1_assess",
            title="RTI Applicability Assessment",
            content=(
                f"**RTI Applicable:** {'Yes' if applicable else 'No'}\n"
                f"**Confidence:** {confidence}%\n"
                f"**Department:** {data['DEPARTMENT']}\n"
                f"**Information Needed:** {data['INFORMATION_NEEDED']}\n"
                f"**Reasoning:** {data['REASONING']}"
            ),
            confidence=confidence,
        )
    )
    return state


# ── Conditional Router ─────────────────────────────────────────────────────

def _assess_router(state: RTIState) -> Literal["legal_basis", "alternate"]:
    """
    Path A: rti_applicable is True AND confidence >= 60  →  legal_basis
    Path B: rti_applicable is False OR confidence <  60  →  alternate
    """
    if state["rti_applicable"] and state["confidence"] >= 60:
        return "legal_basis"
    return "alternate"


# ── Path A Nodes ───────────────────────────────────────────────────────────

def legal_basis_node(state: RTIState) -> RTIState:
    """Establish the legal foundation for the RTI application."""
    result = invoke_llm(
        system=LEGAL_BASIS_PROMPT,
        user=(
            f"Problem: {state['problem']}\n"
            f"Department: {state['department']}\n"
            f"Information needed: {state['information_needed']}"
        ),
    )

    state["legal_basis"] = result
    state["steps_log"].append(
        StepResult(
            step="2_legal_basis",
            title="Legal Basis for RTI",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


def draft_node(state: RTIState) -> RTIState:
    """Draft the formal RTI application."""
    result = invoke_llm(
        system=DRAFT_RTI_PROMPT,
        user=(
            f"Department: {state['department']}\n"
            f"Information needed: {state['information_needed']}\n"
            f"Legal basis:\n{state['legal_basis']}"
        ),
    )

    state["application_draft"] = result
    state["steps_log"].append(
        StepResult(
            step="3_draft",
            title="RTI Application Draft",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


def filing_node(state: RTIState) -> RTIState:
    """Provide step-by-step filing instructions."""
    result = invoke_llm(
        system=FILING_PROMPT,
        user=(
            f"Department: {state['department']}\n"
            f"RTI application:\n{state['application_draft']}"
        ),
    )

    state["filing_instructions"] = result
    state["steps_log"].append(
        StepResult(
            step="4_filing",
            title="Filing Instructions",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


# ── Path B Node ────────────────────────────────────────────────────────────

def alternate_node(state: RTIState) -> RTIState:
    """Suggest alternate legal remedies when RTI is not applicable."""
    result = invoke_llm(
        system=ALTERNATE_PROMPT,
        user=f"Citizen's problem:\n{state['problem']}",
    )

    state["steps_log"].append(
        StepResult(
            step="2_alternate",
            title="Alternate Legal Remedies",
            content=result,
            confidence=state["confidence"],
        )
    )
    return state


# ── Build & Compile Graph ─────────────────────────────────────────────────

def _build_rti_graph() -> object:
    """
    assess → conditional →
        Path A: legal_basis → draft → filing → END
        Path B: alternate → END
    """
    graph = StateGraph(RTIState)

    graph.add_node("assess", assess_node)
    graph.add_node("legal_basis", legal_basis_node)
    graph.add_node("draft", draft_node)
    graph.add_node("filing", filing_node)
    graph.add_node("alternate", alternate_node)

    graph.set_entry_point("assess")

    graph.add_conditional_edges(
        "assess",
        _assess_router,
        {
            "legal_basis": "legal_basis",
            "alternate": "alternate",
        },
    )

    # Path A chain
    graph.add_edge("legal_basis", "draft")
    graph.add_edge("draft", "filing")
    graph.add_edge("filing", END)

    # Path B terminal
    graph.add_edge("alternate", END)

    return graph.compile()


_agent = _build_rti_graph()


# ── Public API ─────────────────────────────────────────────────────────────

def analyze_rti(problem: str) -> list[StepResult]:
    """
    Run the full RTI analysis pipeline and return the steps log.

    Parameters
    ----------
    problem : str
        Description of the citizen's problem or grievance.

    Returns
    -------
    list[StepResult]
        Ordered list of step results produced by the agent.
    """
    initial_state: RTIState = {
        "problem": problem,
        "rti_applicable": False,
        "confidence": 0,
        "department": "",
        "information_needed": "",
        "legal_basis": "",
        "application_draft": "",
        "filing_instructions": "",
        "steps_log": [],
    }

    final_state = _agent.invoke(initial_state)
    return final_state["steps_log"]

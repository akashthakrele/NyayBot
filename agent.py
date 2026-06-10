import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from openai import OpenAI
from langgraph.graph import StateGraph, END

load_dotenv()

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
)

def llm(system: str, user: str) -> str:
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return r.choices[0].message.content

# ── State ──────────────────────────────────────────────────────────────────
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

# ── Nodes ──────────────────────────────────────────────────────────────────

def classify_node(state: AgentState) -> AgentState:
    """Agent decides doc type AND confidence. If low confidence, it will retry."""
    text = state["document_text"][:2000]
    
    result = llm(
        system="""You are a legal document classifier for Indian government documents.
Classify the document and return EXACTLY in this format:
DOC_TYPE: [type]
LEGAL_DOMAIN: [one of: RTI, Tenant_Rights, Income_Certificate, Land_Records, Court_Notice, Employment, Other]
CONFIDENCE: [0-100]
REASONING: [one sentence why]""",
        user=f"Classify this document:\n{text}"
    )
    
    lines = result.strip().split('\n')
    data = {}
    for line in lines:
        if ':' in line:
            k, v = line.split(':', 1)
            data[k.strip()] = v.strip()
    
    confidence = int(''.join(filter(str.isdigit, data.get('CONFIDENCE', '50'))) or '50')
    
    state["doc_type"] = data.get('DOC_TYPE', 'Unknown')
    state["legal_domain"] = data.get('LEGAL_DOMAIN', 'Other')
    state["confidence"] = confidence
    state["steps_log"].append({
        "step": "1_classify",
        "title": "Document Classification",
        "content": f"**Type:** {state['doc_type']}\n**Legal Domain:** {state['legal_domain']}\n**Confidence:** {confidence}%\n**Reasoning:** {data.get('REASONING', '')}",
        "confidence": confidence
    })
    return state


def should_retry_classification(state: AgentState) -> Literal["retry", "extract"]:
    """Real decision node — agent decides whether to retry or proceed."""
    if state["confidence"] < 60 and state["retry_count"] < 2:
        state["retry_count"] += 1
        state["steps_log"].append({
            "step": "retry_notice",
            "title": "Agent Decision: Low Confidence — Retrying",
            "content": f"Confidence was {state['confidence']}%. Agent is re-analyzing with broader context.",
            "confidence": state["confidence"]
        })
        return "retry"
    return "extract"


def retry_classify_node(state: AgentState) -> AgentState:
    """Retry with more document text."""
    text = state["document_text"][:4000]  # broader context
    
    result = llm(
        system="""You are a legal document classifier. Previous classification had low confidence.
Try again with broader analysis. Return EXACTLY:
DOC_TYPE: [type]
LEGAL_DOMAIN: [one of: RTI, Tenant_Rights, Income_Certificate, Land_Records, Court_Notice, Employment, Other]
CONFIDENCE: [0-100]
REASONING: [one sentence why]""",
        user=f"Re-classify with full context:\n{text}"
    )
    
    lines = result.strip().split('\n')
    data = {}
    for line in lines:
        if ':' in line:
            k, v = line.split(':', 1)
            data[k.strip()] = v.strip()
    
    confidence = int(''.join(filter(str.isdigit, data.get('CONFIDENCE', '60'))) or '60')
    state["doc_type"] = data.get('DOC_TYPE', state["doc_type"])
    state["legal_domain"] = data.get('LEGAL_DOMAIN', state["legal_domain"])
    state["confidence"] = confidence
    state["steps_log"].append({
        "step": "1_classify_retry",
        "title": "Re-Classification Result",
        "content": f"**Type:** {state['doc_type']}\n**Legal Domain:** {state['legal_domain']}\n**Confidence after retry:** {confidence}%",
        "confidence": confidence
    })
    return state


def extract_node(state: AgentState) -> AgentState:
    """Extract facts tailored to the detected legal domain."""
    domain_hints = {
        "RTI": "Focus on: applicant, public authority, information requested, deadlines",
        "Tenant_Rights": "Focus on: landlord, tenant, rent amount, notice period, violations",
        "Income_Certificate": "Focus on: certificate holder, income amount, issuing authority, validity",
        "Land_Records": "Focus on: plot number, owner, area, disputes, encumbrances",
        "Court_Notice": "Focus on: case number, court, parties, hearing date, charges",
        "Employment": "Focus on: employer, employee, role, terms, violations",
        "Other": "Focus on: all parties, dates, key claims, obligations"
    }
    
    hint = domain_hints.get(state["legal_domain"], domain_hints["Other"])
    
    result = llm(
        system=f"""Extract key legal facts from this {state['doc_type']} document.
{hint}
Format as clear bullet points. Be specific with names, dates, amounts.""",
        user=f"Document text:\n{state['document_text'][:3000]}"
    )
    
    state["extracted_facts"] = result
    state["steps_log"].append({
        "step": "2_extract",
        "title": "Key Facts Extracted",
        "content": result,
        "confidence": state["confidence"]
    })
    return state


def reason_node(state: AgentState) -> AgentState:
    """Deep legal reasoning based on domain."""
    domain_laws = {
        "RTI": "RTI Act 2005 — Section 7 (30-day response), Section 8 (exemptions), Section 19 (appeals)",
        "Tenant_Rights": "Transfer of Property Act 1882, Rent Control Acts, specific state tenancy laws",
        "Income_Certificate": "IT Act 2000 (digital signatures), Maharashtra Regulation Act 2000",
        "Land_Records": "Registration Act 1908, Land Acquisition Act, state revenue codes",
        "Court_Notice": "CPC 1908, CrPC, relevant IPC sections",
        "Employment": "Industrial Disputes Act, Labour Laws, Contract Act 1872",
        "Other": "Indian Constitution, relevant IPC sections, state-specific laws"
    }
    
    laws = domain_laws.get(state["legal_domain"], domain_laws["Other"])
    
    result = llm(
        system=f"""You are an expert Indian legal analyst specializing in {state['legal_domain']}.
Relevant laws: {laws}
Analyze: legal validity, rights involved, potential violations, risk level (Low/Medium/High).
Be specific to Indian law. Cite actual sections.""",
        user=f"Document type: {state['doc_type']}\nFacts:\n{state['extracted_facts']}"
    )
    
    state["reasoning"] = result
    state["steps_log"].append({
        "step": "3_reason",
        "title": "Legal Reasoning & Rights Analysis",
        "content": result,
        "confidence": state["confidence"]
    })
    return state


def plan_node(state: AgentState) -> AgentState:
    """Generate domain-specific action plan."""
    result = llm(
        system=f"""You are a legal advisor helping Indian citizens with {state['legal_domain']} cases.
Create a numbered action plan. For each step include:
- Exact action to take
- Deadline (specific days)
- Who to contact (with actual govt portals/numbers if known)
Be practical. Assume citizen has limited legal knowledge.""",
        user=f"Legal analysis:\n{state['reasoning']}\n\nCreate action plan:"
    )
    
    state["action_plan"] = result
    state["steps_log"].append({
        "step": "4_plan",
        "title": "Action Plan",
        "content": result,
        "confidence": state["confidence"]
    })
    return state


def draft_node(state: AgentState) -> AgentState:
    """Draft formal response letter."""
    result = llm(
        system=f"""Draft a formal legal letter for an Indian citizen regarding a {state['doc_type']}.
Keep under 250 words. Professional tone. Include:
- Subject line
- Reference to specific laws
- Clear ask/response
- Leave blanks for [Name], [Address], [Date]""",
        user=f"Action plan context:\n{state['action_plan']}\n\nDraft the letter:"
    )
    
    state["response_letter"] = result
    state["steps_log"].append({
        "step": "5_draft",
        "title": "Draft Response Letter",
        "content": result,
        "confidence": state["confidence"]
    })
    return state


# ── Build Graph ────────────────────────────────────────────────────────────

def build_agent():
    graph = StateGraph(AgentState)
    
    graph.add_node("classify", classify_node)
    graph.add_node("retry_classify", retry_classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("reason", reason_node)
    graph.add_node("plan", plan_node)
    graph.add_node("draft", draft_node)
    
    graph.set_entry_point("classify")
    
    # Real decision edge — agent decides to retry or proceed
    graph.add_conditional_edges(
        "classify",
        should_retry_classification,
        {
            "retry": "retry_classify",
            "extract": "extract"
        }
    )
    
    graph.add_edge("retry_classify", "extract")
    graph.add_edge("extract", "reason")
    graph.add_edge("reason", "plan")
    graph.add_edge("plan", "draft")
    graph.add_edge("draft", END)
    
    return graph.compile()

agent = build_agent()

def analyze_document(text: str) -> list:
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
        "steps_log": []
    }
    
    final_state = agent.invoke(initial_state)
    return final_state["steps_log"]
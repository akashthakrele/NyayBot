"""
app/services/rti_service.py — Orchestrates problem → RTI agent pipeline.
"""

from app.agents.rti_agent import analyze_rti


def process_rti(problem: str) -> list:
    """
    Full RTI analysis pipeline.

    1. Run the LangGraph RTI agent on the problem statement.
    2. Return the steps log.

    Parameters
    ----------
    problem : str
        The citizen's problem or grievance description.

    Returns
    -------
    list
        Ordered list of StepResult dicts from the agent.
    """
    steps = analyze_rti(problem)
    return steps

"""
app/services/document_service.py — Orchestrates PDF → agent pipeline.
"""

from app.agents.document_agent import analyze_document
from app.utils.pdf_extractor import extract_text


def process_pdf(file_bytes: bytes) -> list:
    """
    Full document-analysis pipeline.

    1. Extract text from PDF bytes via PyMuPDF.
    2. Run the LangGraph document agent.
    3. Return the steps log.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the uploaded PDF.

    Returns
    -------
    list
        Ordered list of StepResult dicts from the agent.

    Raises
    ------
    ValueError
        Propagated from extract_text if the PDF yields no text.
    """
    text = extract_text(file_bytes)
    steps = analyze_document(text)
    return steps

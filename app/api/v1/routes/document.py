"""
app/api/v1/routes/document.py — POST /api/v1/analyze route.
"""

from fastapi import APIRouter, File, UploadFile

from app.schemas.document import AnalyzeResponse
from app.services.document_service import process_pdf

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document_route(file: UploadFile = File(...)) -> AnalyzeResponse:
    """
    Upload a PDF and receive a multi-step legal analysis.

    - Accepts a single PDF via multipart form upload.
    - Returns ordered analysis steps from the document agent.
    """
    contents = await file.read()
    steps = process_pdf(contents)
    return AnalyzeResponse(steps=steps)

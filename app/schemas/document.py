"""
app/schemas/document.py — Request / response models for document analysis.
"""

from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    """Response schema for POST /api/v1/analyze."""

    steps: list[dict]

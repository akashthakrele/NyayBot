"""
app/schemas/rti.py — Request / response models for RTI analysis.
"""

from pydantic import BaseModel


class RTIRequest(BaseModel):
    """Request body for POST /api/v1/rti."""

    problem: str


class RTIResponse(BaseModel):
    """Response schema for POST /api/v1/rti."""

    steps: list[dict]

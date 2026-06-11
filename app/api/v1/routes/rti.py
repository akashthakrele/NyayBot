"""
app/api/v1/routes/rti.py — POST /api/v1/rti route.
"""

from fastapi import APIRouter

from app.schemas.rti import RTIRequest, RTIResponse
from app.services.rti_service import process_rti

router = APIRouter()


@router.post("/rti", response_model=RTIResponse)
async def analyze_rti_route(body: RTIRequest) -> RTIResponse:
    """
    Submit a problem description and receive RTI applicability analysis.

    - Accepts a JSON body with a `problem` field.
    - Returns ordered analysis steps from the RTI agent.
    """
    steps = process_rti(body.problem)
    return RTIResponse(steps=steps)

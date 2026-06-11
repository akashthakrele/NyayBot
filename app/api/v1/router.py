"""
app/api/v1/router.py — Registers all v1 API routes.
"""

from fastapi import APIRouter

from app.api.v1.routes.document import router as document_router
from app.api.v1.routes.rti import router as rti_router

router = APIRouter(prefix="/api/v1")

router.include_router(document_router, tags=["Document Analysis"])
router.include_router(rti_router, tags=["RTI Analysis"])

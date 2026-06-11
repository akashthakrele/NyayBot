"""
app/main.py — FastAPI application initialisation.

- Mounts the v1 API router
- Serves frontend/index.html at GET /
- Registers CORS middleware and exception handlers
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.middleware import register_cors
from app.exceptions.handlers import register_exception_handlers

# ── Application factory ───────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered Indian legal document analyser and RTI assistant.",
    version="1.0.0",
)

# ── Middleware ─────────────────────────────────────────────────────────────
register_cors(app)

# ── Exception handlers ────────────────────────────────────────────────────
register_exception_handlers(app)

# ── API routes ─────────────────────────────────────────────────────────────
app.include_router(v1_router)

# ── Frontend ───────────────────────────────────────────────────────────────
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend() -> HTMLResponse:
    """Serve the single-page frontend."""
    index_path = _FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            content="<h1>Frontend not found</h1><p>Place index.html in frontend/</p>",
            status_code=404,
        )
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

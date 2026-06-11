"""
app/core/middleware.py — CORS middleware registration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_cors(app: FastAPI) -> None:
    """
    Register CORS middleware allowing all origins.
    Wide-open for hackathon; tighten before production.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

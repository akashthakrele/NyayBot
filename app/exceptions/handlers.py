"""
app/exceptions/handlers.py — Structured exception handlers for FastAPI.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NyayBotException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class PDFExtractionError(NyayBotException):
    """Raised when PDF text extraction fails."""

    def __init__(self, message: str = "Could not extract text from PDF") -> None:
        super().__init__(message=message, status_code=422)


class AgentProcessingError(NyayBotException):
    """Raised when an agent pipeline fails."""

    def __init__(self, message: str = "Agent processing failed") -> None:
        super().__init__(message=message, status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach structured error handlers to the FastAPI application."""

    @app.exception_handler(NyayBotException)
    async def nyaybot_exception_handler(
        request: Request, exc: NyayBotException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {type(exc).__name__}"},
        )

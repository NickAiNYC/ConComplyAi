"""FastAPI application factory for the ConComplyAI platform."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from concomplyai import __version__
from concomplyai.api.middleware import (
    ErrorHandlerMiddleware,
    RateLimitMiddleware,
    TokenAuthMiddleware,
)
from concomplyai.api.routes import router
from concomplyai.config.settings import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Applies CORS, authentication (when a token is configured), rate
    limiting, and error-handling middleware in the correct order.
    """
    settings = get_settings()

    app = FastAPI(
        title="ConComplyAI Platform",
        version=__version__,
        description="Construction Compliance Intelligence Platform API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Starlette processes middleware in reverse registration order, so the
    # outermost (first to run) middleware should be added last.
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RateLimitMiddleware)

    if settings.auth_token.get_secret_value():
        app.add_middleware(TokenAuthMiddleware)

    app.include_router(router)

    return app


def main() -> None:
    """Run the application with uvicorn using configured host and port."""
    settings = get_settings()
    app = create_app()
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
    )


if __name__ == "__main__":
    main()

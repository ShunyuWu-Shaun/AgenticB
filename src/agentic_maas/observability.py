from __future__ import annotations

from fastapi import FastAPI


def instrument_fastapi(app: FastAPI) -> None:
    """Best-effort OTel instrumentation without hard dependency at runtime."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        # Keep runtime lightweight for local development if OTel packages are not installed.
        return

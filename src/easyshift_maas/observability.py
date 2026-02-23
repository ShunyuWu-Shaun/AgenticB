from __future__ import annotations

from fastapi import FastAPI


def instrument_fastapi(app: FastAPI) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        return

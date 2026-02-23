from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed


class OpenAICompatibleProvider:
    """Generic provider for vLLM/Qwen/DeepSeek OpenAI-compatible endpoints."""

    def __init__(self, name: str, base_url: str, model: str, api_key: str | None = None) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.2), reraise=True)
    def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None,
        temperature: float,
        timeout_s: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = list(tools)

        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.2), reraise=True)
    def embeddings(self, inputs: Sequence[str]) -> list[list[float]]:
        payload = {
            "model": self.model,
            "input": list(inputs),
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        data = body.get("data", [])
        return [item["embedding"] for item in data]

    def health(self) -> dict[str, Any]:
        status: str
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(f"{self.base_url}/models", headers=self._headers())
                response.raise_for_status()
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            return {"provider": self.name, "status": "degraded", "error": str(exc)}
        return {"provider": self.name, "status": status, "model": self.model}

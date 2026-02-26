from __future__ import annotations

import json
from typing import Any

import httpx


class OpenAICompatibleError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_s: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def chat_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        request_payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_payload,
                )
                response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise OpenAICompatibleError(f"LLM request failed: {exc}") from exc

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
            if not isinstance(content, str):
                raise TypeError(f"unexpected content type: {type(content).__name__}")
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            raise OpenAICompatibleError(f"failed to decode LLM JSON payload: {exc}") from exc

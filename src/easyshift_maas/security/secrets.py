from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlparse

import yaml


class SecretResolverProtocol(Protocol):
    def resolve(self, conn_ref: str) -> dict[str, Any]: ...


class EnvSecretResolver:
    """Resolve conn_ref from environment variables.

    Supported forms:
    - env:MY_CONN
    - MY_CONN
    """

    def resolve(self, conn_ref: str) -> dict[str, Any]:
        key = conn_ref.split(":", 1)[1] if conn_ref.startswith("env:") else conn_ref
        raw = os.getenv(key)
        if raw is None:
            raise KeyError(f"environment variable not found: {key}")
        return self._parse_payload(raw)

    def _parse_payload(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if not text:
            return {}

        if text.startswith("{"):
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("env secret JSON must be an object")
            return payload

        if "://" in text:
            return self._parse_dsn(text)

        if "=" in text:
            result: dict[str, Any] = {}
            for pair in text.split(";"):
                if "=" not in pair:
                    continue
                key, value = pair.split("=", 1)
                result[key.strip()] = value.strip()
            if result:
                return result

        raise ValueError("unable to parse env connection secret; expected JSON, DSN, or k=v pairs")

    def _parse_dsn(self, dsn: str) -> dict[str, Any]:
        parsed = urlparse(dsn)
        payload: dict[str, Any] = {
            "scheme": parsed.scheme,
            "host": parsed.hostname,
            "port": parsed.port,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/") if parsed.path else "",
        }
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            payload[key] = value
        return {key: value for key, value in payload.items() if value is not None}


class FileSecretResolver:
    """Resolve conn_ref from file secrets.

    Supported forms:
    - file:/absolute/path.json
    - file:/absolute/path.yaml
    """

    def resolve(self, conn_ref: str) -> dict[str, Any]:
        if not conn_ref.startswith("file:"):
            raise KeyError("not a file secret reference")
        path = Path(conn_ref.split(":", 1)[1])
        if not path.exists():
            raise FileNotFoundError(path)

        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            payload = yaml.safe_load(raw)
        else:
            payload = json.loads(raw)

        if not isinstance(payload, dict):
            raise ValueError("file secret must contain a mapping object")
        return payload


class ChainedSecretResolver:
    def __init__(self, resolvers: list[SecretResolverProtocol] | None = None) -> None:
        self._resolvers = resolvers or [EnvSecretResolver(), FileSecretResolver()]

    def resolve(self, conn_ref: str) -> dict[str, Any]:
        errors: list[str] = []
        for resolver in self._resolvers:
            try:
                return resolver.resolve(conn_ref)
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue
        joined = "; ".join(errors) if errors else "no resolver configured"
        raise KeyError(f"unable to resolve conn_ref '{conn_ref}': {joined}")

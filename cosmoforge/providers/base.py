"""Provider interface: one chat turn against any model backend.

A provider is deliberately small: it turns a list of :class:`ChatMessage` into
an :class:`LLMResponse`. Concrete providers only translate transport details;
routing, fallback and prompt-building live one layer up.
"""
from __future__ import annotations

import abc
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a request."""


@dataclass
class ChatMessage:
    role: str          # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    text: str
    provider: str = ""
    model: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


def first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


class Provider(abc.ABC):
    """Base class for every backend.

    Subclasses set the class-level defaults (``name``, ``default_model``,
    ``default_base_url`` and the ``*_env`` tuples) and implement ``_complete``.
    """

    name = "provider"
    label = "Provider"
    default_model = ""
    default_base_url = ""
    api_key_env: Tuple[str, ...] = ()
    base_url_env: Tuple[str, ...] = ()
    model_env: Tuple[str, ...] = ()
    requires_key = True
    supports_system = True

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        retries: int = 1,
        **options: Any,
    ):
        self.model = model or first_env(*self.model_env) or self.default_model
        if api_key is None:
            api_key = first_env(*self.api_key_env)
        self.api_key = api_key or ""
        self.base_url = (
            base_url or first_env(*self.base_url_env) or self.default_base_url
        ).rstrip("/")
        self.timeout = float(timeout)
        self.retries = max(0, int(retries))
        self.options = options

    # -- introspection ----------------------------------------------------
    @property
    def configured(self) -> bool:
        return bool(self.api_key) or not self.requires_key

    def describe(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "label": self.label,
            "model": self.model,
            "base_url": self.base_url,
            "configured": self.configured,
            "requires_key": self.requires_key,
        }

    # -- public API -------------------------------------------------------
    def complete(
        self,
        messages: Sequence[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.configured:
            raise ProviderError(
                f"{self.label} is not configured (set one of: "
                f"{', '.join(self.api_key_env) or 'an API key'})."
            )
        last: Optional[ProviderError] = None
        for attempt in range(self.retries + 1):
            try:
                return self._complete(list(messages), temperature, max_tokens)
            except ProviderError as exc:
                last = exc
                if attempt < self.retries:
                    time.sleep(min(2.0 ** attempt, 4.0))
        raise last or ProviderError(f"{self.label} failed")

    @abc.abstractmethod
    def _complete(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- transport helpers ------------------------------------------------
    def _post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        merged = {"Content-Type": "application/json"}
        if headers:
            merged.update(headers)
        request = urllib.request.Request(url, data=body, headers=merged, method="POST")
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise ProviderError(f"{self.label} HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"{self.label} connection error: {exc.reason}") from exc
        except OSError as exc:  # pragma: no cover - sockets/timeouts
            raise ProviderError(f"{self.label} transport error: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"{self.label} returned non-JSON: {raw[:200]!r}") from exc
        data["__latency_ms"] = (time.time() - started) * 1000.0
        return data

    @staticmethod
    def _split_system(
        messages: Sequence[ChatMessage],
    ) -> Tuple[str, List[ChatMessage]]:
        system = []
        rest: List[ChatMessage] = []
        for message in messages:
            if message.role == "system":
                system.append(message.content)
            else:
                rest.append(message)
        return "\n\n".join(system), rest


class FallbackProvider(Provider):
    """Tries a chain of providers in order; the first success wins.

    Used so a run can name several backends (e.g. a primary cloud model plus a
    local Ollama instance) and never crash when one of them is unreachable.
    """

    name = "fallback"
    label = "Fallback chain"
    requires_key = False

    def __init__(self, providers: Sequence[Provider]):
        self.providers = list(providers)
        if not self.providers:
            raise ValueError("FallbackProvider needs at least one provider")
        primary = self.providers[0]
        self.model = primary.model
        self.base_url = primary.base_url
        self.api_key = primary.api_key
        self.timeout = primary.timeout
        self.retries = primary.retries
        self.options = dict(primary.options)

    @property
    def configured(self) -> bool:
        return any(p.configured for p in self.providers)

    def describe(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "label": self.label,
            "model": self.model,
            "chain": [p.describe() for p in self.providers],
            "configured": self.configured,
        }

    def _complete(self, messages, temperature, max_tokens):
        errors: List[str] = []
        for provider in self.providers:
            if not provider.configured:
                errors.append(f"{provider.name}: not configured")
                continue
            try:
                return provider.complete(messages, temperature, max_tokens)
            except ProviderError as exc:
                errors.append(str(exc))
        raise ProviderError("all providers failed: " + " | ".join(errors))


__all__ = [
    "ProviderError",
    "ChatMessage",
    "LLMResponse",
    "Provider",
    "FallbackProvider",
    "first_env",
]

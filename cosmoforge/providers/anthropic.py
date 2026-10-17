"""Anthropic Messages API provider."""
from __future__ import annotations

from typing import List, Optional

from .base import ChatMessage, LLMResponse, Provider, ProviderError


class AnthropicProvider(Provider):
    name = "anthropic"
    label = "Anthropic Claude"
    default_base_url = "https://api.anthropic.com"
    default_model = "claude-3-5-sonnet-latest"
    api_key_env = ("ANTHROPIC_API_KEY",)
    base_url_env = ("ANTHROPIC_BASE_URL",)
    model_env = ("ANTHROPIC_MODEL", "COSMOFORGE_MODEL")
    api_version = "2023-06-01"

    def _complete(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        system, rest = self._split_system(messages)
        payload = {
            "model": self.model,
            "max_tokens": int(max_tokens or 1024),
            "temperature": min(max(temperature, 0.0), 1.0),
            "messages": [m.to_dict() for m in rest],
        }
        if system and self.supports_system:
            payload["system"] = system
        data = self._post_json(
            f"{self.base_url}/v1/messages",
            payload,
            {
                "x-api-key": self.api_key,
                "anthropic-version": self.api_version,
            },
        )
        blocks = data.get("content") or []
        text = "".join(
            block.get("text", "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not text:
            raise ProviderError(f"{self.label}: no text content in response: {data}")
        return LLMResponse(
            text=text,
            provider=self.name,
            model=data.get("model", self.model),
            usage=data.get("usage", {}) or {},
            latency_ms=float(data.get("__latency_ms", 0.0)),
        )


__all__ = ["AnthropicProvider"]

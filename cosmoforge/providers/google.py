"""Google Gemini (Generative Language API) provider."""
from __future__ import annotations

import urllib.parse
from typing import List, Optional

from .base import ChatMessage, LLMResponse, Provider, ProviderError


class GoogleProvider(Provider):
    name = "google"
    label = "Google Gemini"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta"
    default_model = "gemini-2.0-flash"
    api_key_env = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    base_url_env = ("GEMINI_BASE_URL", "GOOGLE_BASE_URL")
    model_env = ("GEMINI_MODEL", "GOOGLE_MODEL", "COSMOFORGE_MODEL")

    def _complete(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        system, rest = self._split_system(messages)
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in rest
        ]
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = int(max_tokens)
        if system and self.supports_system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        query = urllib.parse.urlencode({"key": self.api_key})
        url = f"{self.base_url}/models/{self.model}:generateContent?{query}"
        data = self._post_json(url, payload)

        try:
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.label}: unexpected response shape: {data}") from exc
        if not text:
            reason = data.get("promptFeedback", {}).get("blockReason", "empty candidate")
            raise ProviderError(f"{self.label}: no text ({reason})")
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            usage=data.get("usageMetadata", {}) or {},
            latency_ms=float(data.get("__latency_ms", 0.0)),
        )


__all__ = ["GoogleProvider"]

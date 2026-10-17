"""Ollama is a provider too: local, key-free, and the usual offline fallback."""
from __future__ import annotations

from typing import List, Optional

from .base import ChatMessage, LLMResponse, Provider, ProviderError


class OllamaProvider(Provider):
    name = "ollama"
    label = "Ollama (local)"
    default_base_url = "http://localhost:11434"
    default_model = "llama3.2"
    base_url_env = ("OLLAMA_HOST", "OLLAMA_BASE_URL")
    model_env = ("OLLAMA_MODEL", "COSMOFORGE_MODEL")
    requires_key = False

    def _complete(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        options = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": options,
        }
        data = self._post_json(f"{self.base_url}/api/chat", payload)
        try:
            text = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"{self.label}: unexpected response shape: {data}") from exc
        return LLMResponse(
            text=text or "",
            provider=self.name,
            model=data.get("model", self.model),
            usage={
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
            latency_ms=float(data.get("__latency_ms", 0.0)),
        )


__all__ = ["OllamaProvider"]

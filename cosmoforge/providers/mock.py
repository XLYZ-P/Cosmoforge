"""A local, deterministic, key-free provider.

Useful for tests and for `--narrator llm` demos without any credentials: it
returns a plausible-looking JSON object built from the prompt hash so output is
stable across runs.
"""
from __future__ import annotations

import hashlib
import json
from typing import List, Optional

from .base import ChatMessage, LLMResponse, Provider

_ADJECTIVES = (
    "silent", "burning", "hollow", "radiant", "tidal", "nested", "recursive",
    "patient", "shattered", "luminous", "drowned", "iron",
)
_NOUNS = (
    "archive", "horizon", "engine", "cradle", "lattice", "requiem", "garden",
    "witness", "threshold", "chorus", "spiral", "inheritance",
)


class MockProvider(Provider):
    name = "mock"
    label = "Mock (offline)"
    default_model = "mock-1"
    requires_key = False

    def _allowed_kinds(self, messages: List[ChatMessage]) -> List[str]:
        """Read `allowed_child_kinds` out of the expansion request, if present."""
        for message in reversed(messages):
            try:
                payload = json.loads(message.content)
            except (ValueError, TypeError):
                continue
            if isinstance(payload, dict):
                allowed = payload.get("allowed_child_kinds")
                if isinstance(allowed, list):
                    return [k for k in allowed if isinstance(k, str)]
        return []

    def _complete(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        prompt = "\n".join(m.content for m in messages)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
        adjective = _ADJECTIVES[seed % len(_ADJECTIVES)]
        noun = _NOUNS[(seed // 7) % len(_NOUNS)]
        data: dict = {
            "narrative": (
                f"A {adjective} {noun} unfolds here. [mock:{digest[:8]}]"
            )
        }
        allowed = self._allowed_kinds(messages)
        if allowed:
            children = []
            for i in range(1 + seed % 2):
                kind = allowed[(seed + i) % len(allowed)]
                children.append(
                    {
                        "label": f"{_ADJECTIVES[(seed + i * 3) % len(_ADJECTIVES)].title()} {kind.title()}",
                        "kind": kind,
                        "detail": f"Offline mock content for a {kind}. [mock]",
                        "meta": {
                            "note": "mock",
                            "severity": round(((seed + i * 11) % 100) / 100, 2),
                        },
                    }
                )
            data["children"] = children
        return LLMResponse(
            text=json.dumps(data, ensure_ascii=False),
            provider=self.name,
            model=self.model,
        )


__all__ = ["MockProvider"]

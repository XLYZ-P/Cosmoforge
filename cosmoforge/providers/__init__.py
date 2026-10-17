"""Provider registry and resolution.

Importing this package registers every built-in provider. The rest of the
framework only ever calls :func:`resolve` (one backend) or :func:`resolve_many`
(a fallback chain), so adding a vendor is a one-line registration.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Type, Union

from .base import (
    ChatMessage,
    FallbackProvider,
    LLMResponse,
    Provider,
    ProviderError,
    first_env,
)
from .anthropic import AnthropicProvider
from .google import GoogleProvider
from .mock import MockProvider
from .ollama import OllamaProvider
from .openai import (
    AzureOpenAIProvider,
    DashScopeProvider,
    DeepSeekProvider,
    FireworksProvider,
    GroqProvider,
    LMStudioProvider,
    MistralProvider,
    MoonshotProvider,
    OpenAICompatProvider,
    OpenRouterProvider,
    PerplexityProvider,
    TogetherProvider,
    VllmProvider,
    XaiProvider,
    ZhipuProvider,
)

_REGISTRY: Dict[str, Type[Provider]] = {}

#: Spec accepted anywhere a provider is requested.
ProviderSpec = Union[str, Dict[str, Any], Provider, None]


def register(provider_cls: Type[Provider]) -> Type[Provider]:
    """Register a provider under its ``name`` (idempotent)."""
    _REGISTRY[provider_cls.name] = provider_cls
    return provider_cls


for _cls in (
    OpenAICompatProvider,
    AzureOpenAIProvider,
    DeepSeekProvider,
    MoonshotProvider,
    ZhipuProvider,
    DashScopeProvider,
    MistralProvider,
    GroqProvider,
    TogetherProvider,
    OpenRouterProvider,
    XaiProvider,
    FireworksProvider,
    PerplexityProvider,
    VllmProvider,
    LMStudioProvider,
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider,
    MockProvider,
):
    register(_cls)


#: Friendly aliases -> canonical provider names.
ALIASES: Dict[str, str] = {
    "gpt": "openai",
    "openai-compatible": "openai",
    "claude": "anthropic",
    "gemini": "google",
    "qwen": "dashscope",
    "glm": "zhipu",
    "kimi": "moonshot",
    "grok": "xai",
    "local": "ollama",
    "none": "mock",
    "offline": "mock",
    "": "mock",
}


def canonical(name: str) -> str:
    key = (name or "").strip().lower()
    return ALIASES.get(key, key)


def available() -> List[Dict[str, Any]]:
    """Provider catalogue for `cosmoforge providers` and docs."""
    rows = []
    for name, cls in sorted(_REGISTRY.items()):
        rows.append(
            {
                "provider": name,
                "label": cls.label,
                "default_model": cls.default_model,
                "base_url": cls.default_base_url,
                "api_key_env": list(cls.api_key_env),
                "requires_key": cls.requires_key,
            }
        )
    return rows


def get(name: str) -> Type[Provider]:
    key = canonical(name)
    if key not in _REGISTRY:
        raise KeyError(
            f"unknown provider {name!r}; available: {', '.join(sorted(_REGISTRY))}"
        )
    return _REGISTRY[key]


def _build(spec: Dict[str, Any]) -> Provider:
    name = spec.get("provider") or spec.get("type") or spec.get("name") or ""
    override_cls = spec.get("class")
    if isinstance(override_cls, type) and issubclass(override_cls, Provider):
        cls = override_cls
    else:
        cls = get(name)
    options = dict(spec.get("options", {}))
    # pass through any extra scalar keys as provider options
    for key, value in spec.items():
        if key in {
            "provider", "type", "name", "class", "model", "api_key",
            "base_url", "timeout", "retries", "options",
        }:
            continue
        options[key] = value
    return cls(
        model=spec.get("model"),
        api_key=spec.get("api_key"),
        base_url=spec.get("base_url"),
        timeout=float(spec.get("timeout", 60.0)),
        retries=int(spec.get("retries", 1)),
        **options,
    )


def resolve(spec: ProviderSpec = None, **overrides: Any) -> Provider:
    """Turn a spec into a ready-to-use provider.

    ``spec`` may be a provider name, a config dict, an existing ``Provider``
    instance, or ``None`` (which reads ``COSMOFORGE_PROVIDER`` and falls back to
    the offline mock provider).
    """
    if isinstance(spec, Provider):
        return spec
    if spec is None:
        env_name = first_env("COSMOFORGE_PROVIDER")
        spec = {"provider": env_name or "mock"}
    if isinstance(spec, str):
        spec = {"provider": spec}
    if not isinstance(spec, dict):
        raise TypeError(f"cannot resolve provider from {spec!r}")
    merged = dict(spec)
    if overrides:
        merged.update({k: v for k, v in overrides.items() if v is not None})
    return _build(merged)


def resolve_many(specs: Sequence[ProviderSpec]) -> Provider:
    """Resolve several specs into one fallback chain (single spec passes through)."""
    providers = [resolve(spec) for spec in specs if spec is not None]
    if not providers:
        return resolve(None)
    if len(providers) == 1:
        return providers[0]
    return FallbackProvider(providers)


__all__ = [
    "ProviderError",
    "ChatMessage",
    "LLMResponse",
    "Provider",
    "FallbackProvider",
    "ProviderSpec",
    "register",
    "get",
    "available",
    "canonical",
    "resolve",
    "resolve_many",
    "ALIASES",
]

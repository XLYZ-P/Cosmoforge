"""OpenAI-compatible chat-completions providers.

One tiny base class covers the whole OpenAI dialect. Every vendor below is just
a set of defaults (base URL + API-key env var), which is why this file is the
widest source of provider coverage for the least code.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from .base import ChatMessage, LLMResponse, Provider, ProviderError


class OpenAICompatProvider(Provider):
    """POST /chat/completions with a bearer token."""

    name = "openai"
    label = "OpenAI-compatible"
    default_base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    api_key_env = ("OPENAI_API_KEY",)
    base_url_env = ("OPENAI_BASE_URL", "COSMOFORGE_BASE_URL")
    model_env = ("OPENAI_MODEL", "COSMOFORGE_MODEL")
    requires_key = True
    chat_path = "/chat/completions"

    extra_headers = {}

    def _headers(self) -> dict:
        headers = dict(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _complete(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [m.to_dict() for m in messages],
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        data = self._post_json(
            f"{self.base_url}{self.chat_path}", payload, self._headers()
        )
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.label}: unexpected response shape: {data}") from exc
        if isinstance(text, list):  # some gateways return content parts
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        return LLMResponse(
            text=text or "",
            provider=self.name,
            model=data.get("model", self.model),
            usage=data.get("usage", {}) or {},
            latency_ms=float(data.get("__latency_ms", 0.0)),
        )


class AzureOpenAIProvider(OpenAICompatProvider):
    """Azure OpenAI: deployment-scoped URL plus an api-version query param."""

    name = "azure"
    label = "Azure OpenAI"
    default_model = "gpt-4o-mini"
    default_base_url = ""
    api_key_env = ("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY")
    base_url_env = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_BASE_URL")
    model_env = ("AZURE_OPENAI_MODEL", "AZURE_OPENAI_DEPLOYMENT")
    requires_key = True

    def _complete(self, messages, temperature, max_tokens):
        api_version = self.options.get("api_version", "2024-06-01")
        path = f"/openai/deployments/{self.model}/chat/completions?api-version={api_version}"
        payload = {
            "temperature": temperature,
            "messages": [m.to_dict() for m in messages],
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        data = self._post_json(
            f"{self.base_url}{path}",
            payload,
            {"api-key": self.api_key},
        )
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.label}: unexpected response shape: {data}") from exc
        return LLMResponse(
            text=text or "",
            provider=self.name,
            model=data.get("model", self.model),
            usage=data.get("usage", {}) or {},
            latency_ms=float(data.get("__latency_ms", 0.0)),
        )


# -- vendor presets ---------------------------------------------------------
# Each subclass only changes marketing defaults; the protocol is identical.


class DeepSeekProvider(OpenAICompatProvider):
    name = "deepseek"
    label = "DeepSeek"
    default_base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"
    api_key_env = ("DEEPSEEK_API_KEY",)
    model_env = ("DEEPSEEK_MODEL", "COSMOFORGE_MODEL")


class MoonshotProvider(OpenAICompatProvider):
    name = "moonshot"
    label = "Moonshot (Kimi)"
    default_base_url = "https://api.moonshot.cn/v1"
    default_model = "moonshot-v1-8k"
    api_key_env = ("MOONSHOT_API_KEY",)


class ZhipuProvider(OpenAICompatProvider):
    name = "zhipu"
    label = "Zhipu GLM"
    default_base_url = "https://open.bigmodel.cn/api/paas/v4"
    default_model = "glm-4-flash"
    api_key_env = ("ZHIPU_API_KEY", "ZHIPUAI_API_KEY")


class DashScopeProvider(OpenAICompatProvider):
    name = "dashscope"
    label = "Alibaba DashScope (Qwen)"
    default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model = "qwen-plus"
    api_key_env = ("DASHSCOPE_API_KEY",)


class MistralProvider(OpenAICompatProvider):
    name = "mistral"
    label = "Mistral"
    default_base_url = "https://api.mistral.ai/v1"
    default_model = "mistral-large-latest"
    api_key_env = ("MISTRAL_API_KEY",)


class GroqProvider(OpenAICompatProvider):
    name = "groq"
    label = "Groq"
    default_base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"
    api_key_env = ("GROQ_API_KEY",)


class TogetherProvider(OpenAICompatProvider):
    name = "together"
    label = "Together AI"
    default_base_url = "https://api.together.xyz/v1"
    default_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    api_key_env = ("TOGETHER_API_KEY",)


class OpenRouterProvider(OpenAICompatProvider):
    name = "openrouter"
    label = "OpenRouter"
    default_base_url = "https://openrouter.ai/api/v1"
    default_model = "openai/gpt-4o-mini"
    api_key_env = ("OPENROUTER_API_KEY",)
    extra_headers = {"X-Title": "Cosmoforge"}


class XaiProvider(OpenAICompatProvider):
    name = "xai"
    label = "xAI Grok"
    default_base_url = "https://api.x.ai/v1"
    default_model = "grok-2-latest"
    api_key_env = ("XAI_API_KEY",)


class FireworksProvider(OpenAICompatProvider):
    name = "fireworks"
    label = "Fireworks AI"
    default_base_url = "https://api.fireworks.ai/inference/v1"
    default_model = "accounts/fireworks/models/llama-v3p3-70b-instruct"
    api_key_env = ("FIREWORKS_API_KEY",)


class PerplexityProvider(OpenAICompatProvider):
    name = "perplexity"
    label = "Perplexity"
    default_base_url = "https://api.perplexity.ai"
    default_model = "sonar"
    api_key_env = ("PERPLEXITY_API_KEY",)


class VllmProvider(OpenAICompatProvider):
    """Any self-hosted OpenAI-compatible server (vLLM, TGI, LM Studio, ...)."""

    name = "vllm"
    label = "Local vLLM / OpenAI-compatible server"
    default_base_url = "http://localhost:8000/v1"
    default_model = "local-model"
    api_key_env = ("VLLM_API_KEY",)
    base_url_env = ("VLLM_BASE_URL", "COSMOFORGE_BASE_URL")
    requires_key = False


class LMStudioProvider(OpenAICompatProvider):
    name = "lmstudio"
    label = "LM Studio"
    default_base_url = "http://localhost:1234/v1"
    default_model = "local-model"
    api_key_env = ()
    base_url_env = ("LMSTUDIO_BASE_URL",)
    requires_key = False


__all__ = [
    "OpenAICompatProvider",
    "AzureOpenAIProvider",
    "DeepSeekProvider",
    "MoonshotProvider",
    "ZhipuProvider",
    "DashScopeProvider",
    "MistralProvider",
    "GroqProvider",
    "TogetherProvider",
    "OpenRouterProvider",
    "XaiProvider",
    "FireworksProvider",
    "PerplexityProvider",
    "VllmProvider",
    "LMStudioProvider",
]

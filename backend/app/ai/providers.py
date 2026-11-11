"""Provider-independent LLM interface.

Resolution order: the user's own provider settings (Settings > AI) win; otherwise the
server-level environment configuration is used; otherwise `None` is returned and callers
switch to the clearly labelled offline mode.
"""
from dataclasses import dataclass
from typing import Protocol

import anthropic
import httpx

from ..config import get_settings
from ..models import UserSettings
from ..security import decrypt_secret

DEFAULT_MODELS = {"anthropic": "claude-opus-5-5", "openai_compatible": "gpt-4o-mini"}


class AIError(Exception):
    """Raised with a user-presentable message when the provider call fails."""


@dataclass
class ProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str = ""
    source: str = "server"  # server | user


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, system: str, messages: list[dict], max_tokens: int = 2000) -> str: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, cfg: ProviderConfig):
        self.model = cfg.model
        self.client = anthropic.Anthropic(api_key=cfg.api_key, timeout=120.0, max_retries=2)

    def complete(self, system: str, messages: list[dict], max_tokens: int = 2000) -> str:
        kwargs: dict = dict(model=self.model, max_tokens=max_tokens, system=system, messages=messages)
        # Server-side fallback on refusals is supported on current Opus/Sonnet/Fable models.
        if self.model.startswith(("claude-opus-5", "claude-sonnet-5-5", "claude-fable-5")):
            kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        if self.model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-haiku-5", "claude-opus-4-8")):
            kwargs["output_config"] = {"effort": "medium"}
        try:
            resp = self.client.beta.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise AIError("The Anthropic API key was rejected. Check it in Settings > AI.") from e
        except anthropic.NotFoundError as e:
            raise AIError(f"Model '{self.model}' was not found for this API key.") from e
        except anthropic.RateLimitError as e:
            raise AIError("The AI provider is rate limiting requests. Try again shortly.") from e
        except anthropic.APIStatusError as e:
            raise AIError(f"The AI provider returned an error ({e.status_code}).") from e
        except anthropic.APIConnectionError as e:
            raise AIError("Could not reach the AI provider.") from e
        if resp.stop_reason == "refusal":
            raise AIError("The model declined this request.")
        return "".join(b.text for b in resp.content if b.type == "text").strip()


class OpenAICompatibleProvider:
    """Works with OpenAI, Groq, OpenRouter, Together, Ollama, LM Studio, vLLM and similar APIs."""

    name = "openai_compatible"

    def __init__(self, cfg: ProviderConfig):
        self.model = cfg.model
        self.base_url = (cfg.base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = cfg.api_key

    def complete(self, system: str, messages: list[dict], max_tokens: int = 2000) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        body = {"model": self.model, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system}, *messages]}
        try:
            r = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=120)
        except httpx.HTTPError as e:
            raise AIError("Could not reach the AI provider.") from e
        if r.status_code == 401:
            raise AIError("The API key was rejected. Check it in Settings > AI.")
        if r.status_code >= 400:
            raise AIError(f"The AI provider returned an error ({r.status_code}).")
        try:
            return r.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise AIError("Unexpected response from the AI provider.") from e


def resolve_config(us: UserSettings | None) -> ProviderConfig | None:
    s = get_settings()
    if us and us.ai_provider and us.ai_provider != "default":
        if us.ai_provider == "none":
            return None
        key = decrypt_secret(us.ai_api_key_encrypted) if us.ai_api_key_encrypted else ""
        if not key:
            key = s.anthropic_api_key if us.ai_provider == "anthropic" else s.openai_api_key
        if not key and us.ai_provider == "anthropic":
            return None
        if not key and us.ai_provider == "openai_compatible" and not us.ai_base_url:
            return None  # local endpoints (Ollama) may not need a key, but need a base URL
        return ProviderConfig(
            provider=us.ai_provider,
            model=us.ai_model or DEFAULT_MODELS[us.ai_provider],
            api_key=key or "",
            base_url=us.ai_base_url or "",
            source="user",
        )
    if s.ai_provider == "anthropic" and s.anthropic_api_key:
        return ProviderConfig("anthropic", s.ai_model or DEFAULT_MODELS["anthropic"], s.anthropic_api_key)
    if s.ai_provider == "openai_compatible" and (s.openai_api_key or s.ai_base_url):
        return ProviderConfig("openai_compatible", s.ai_model or DEFAULT_MODELS["openai_compatible"], s.openai_api_key, s.ai_base_url)
    return None


def get_provider(us: UserSettings | None) -> LLMProvider | None:
    cfg = resolve_config(us)
    if cfg is None:
        return None
    return AnthropicProvider(cfg) if cfg.provider == "anthropic" else OpenAICompatibleProvider(cfg)

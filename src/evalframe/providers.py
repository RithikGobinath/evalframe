"""Provider adapters with a shared result format."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    request_id: str | None
    finish_reason: str | None


class Provider(Protocol):
    async def generate(self, model: str, system: str, user: str, max_output_tokens: int) -> ProviderResponse: ...
    async def close(self) -> None: ...


class OpenAIProvider:
    def __init__(self) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required for an OpenAI run")
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(timeout=90.0, max_retries=2)

    async def generate(self, model: str, system: str, user: str, max_output_tokens: int) -> ProviderResponse:
        response = await self.client.responses.create(
            model=model,
            instructions=system,
            input=user,
            max_output_tokens=max_output_tokens,
        )
        usage = response.usage
        return ProviderResponse(
            text=response.output_text or "",
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            request_id=getattr(response, "_request_id", None),
            finish_reason=response.status,
        )

    async def close(self) -> None:
        await self.client.close()


class OpenRouterProvider:
    def __init__(self) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required for an OpenRouter run")
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=90.0,
            max_retries=2,
        )

    async def generate(self, model: str, system: str, user: str, max_output_tokens: int) -> ProviderResponse:
        completion = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_output_tokens,
        )
        choice = completion.choices[0]
        usage = completion.usage
        return ProviderResponse(
            text=choice.message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            request_id=getattr(completion, "_request_id", None) or completion.id,
            finish_reason=choice.finish_reason,
        )

    async def close(self) -> None:
        await self.client.close()


class AnthropicProvider:
    def __init__(self) -> None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY is required for an Anthropic run")
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(timeout=90.0, max_retries=2)

    async def generate(self, model: str, system: str, user: str, max_output_tokens: int) -> ProviderResponse:
        message = await self.client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_output_tokens,
        )
        return ProviderResponse(
            text="".join(block.text for block in message.content if block.type == "text"),
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            request_id=getattr(message, "_request_id", None),
            finish_reason=message.stop_reason,
        )

    async def close(self) -> None:
        await self.client.close()


def create_provider(name: str) -> Provider:
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "openrouter":
        return OpenRouterProvider()
    raise ValueError(f"Unsupported provider: {name}")

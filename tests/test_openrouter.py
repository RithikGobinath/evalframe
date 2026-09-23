import asyncio
from types import SimpleNamespace

from evalframe.providers import OpenRouterProvider
from evalframe.runner import parse_model_spec


def test_openrouter_uses_chat_completions_and_preserves_usage(monkeypatch):
    import openai

    observed = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            observed["request"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="billing"), finish_reason="stop")],
                usage=SimpleNamespace(prompt_tokens=14, completion_tokens=3),
                id="router-request",
            )

    class FakeClient:
        def __init__(self, **kwargs):
            observed["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self):
            observed["closed"] = True

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret")
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeClient)
    provider = OpenRouterProvider()
    response = asyncio.run(provider.generate("anthropic/claude-haiku-4.5", "Classify", "A ticket", 64))
    asyncio.run(provider.close())

    assert observed["client"]["base_url"] == "https://openrouter.ai/api/v1"
    assert observed["request"] == {
        "model": "anthropic/claude-haiku-4.5",
        "messages": [{"role": "system", "content": "Classify"}, {"role": "user", "content": "A ticket"}],
        "max_tokens": 64,
    }
    assert (response.text, response.input_tokens, response.output_tokens, response.request_id) == (
        "billing", 14, 3, "router-request"
    )
    assert observed["closed"] is True


def test_openrouter_model_slug_can_contain_colon():
    assert parse_model_spec("openrouter:vendor/model:free") == ("openrouter", "vendor/model:free")

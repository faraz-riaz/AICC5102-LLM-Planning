from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.llm_heuristics import models


ORIGINAL_LOAD_ENVIRONMENT = models.load_environment


class FakeGeminiModels:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    def count_tokens(self, **kwargs):
        self.requests.append(("count_tokens", kwargs))
        return SimpleNamespace(total_tokens=3)

    def generate_content(self, **kwargs):
        self.requests.append(("generate_content", kwargs))
        return SimpleNamespace(text="generated", usage_metadata={"total_tokens": 4})


class FakeGeminiClient:
    def __init__(self) -> None:
        self.models = FakeGeminiModels()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeCreate:
    def __init__(self, response) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.response


class FakeOpenAIClient:
    def __init__(self) -> None:
        message = SimpleNamespace(content="generated", reasoning_content=None)
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=message)], usage={"total_tokens": 4}
        )
        response = SimpleNamespace(output_text="generated", usage={"total_tokens": 4})
        self.chat = SimpleNamespace(completions=FakeCreate(completion))
        self.responses = FakeCreate(response)
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def isolate_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LLM_PROVIDER",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "NVIDIA_API_KEY",
        *models.PROVIDER_MODEL_ENV_VARS.values(),
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(models, "load_environment", lambda: None)


def test_gemini_developer_api_uses_gemini_api_key(monkeypatch) -> None:
    calls = []
    sentinel = object()
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    monkeypatch.setattr(
        models.genai,
        "Client",
        lambda **kwargs: calls.append(kwargs) or sentinel,
    )

    assert models.create_gemini_client() is sentinel
    assert calls == [{"api_key": "gemini-secret"}]


def test_gemini_developer_api_matches_google_key_precedence(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-secret")
    monkeypatch.setattr(
        models.genai,
        "Client",
        lambda **kwargs: calls.append(kwargs) or object(),
    )

    models.create_gemini_client()
    assert calls == [{"api_key": "google-secret"}]


def test_gemini_vertex_uses_project_location_and_adc(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.setenv("GEMINI_API_KEY", "ignored-in-vertex-mode")
    monkeypatch.setattr(
        models.genai,
        "Client",
        lambda **kwargs: calls.append(kwargs) or object(),
    )

    models.create_gemini_client()

    assert calls[0]["vertexai"] is True
    assert calls[0]["project"] == "test-project"
    assert calls[0]["location"] == "global"
    assert calls[0]["http_options"].api_version == "v1"
    assert "api_key" not in calls[0]


def test_gemini_vertex_reports_missing_cloud_configuration(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")

    with pytest.raises(models.ProviderConfigurationError, match="GOOGLE_CLOUD_PROJECT"):
        models.create_gemini_client()


def test_configuration_description_never_contains_secret(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "must-not-be-reported")

    description = models.describe_provider_configuration("gemini")

    assert description["auth_mode"] == "developer_api_key"
    assert description["credential_source"] == "GEMINI_API_KEY"
    assert "must-not-be-reported" not in repr(description)


def test_dotenv_is_loaded_without_overriding_shell_values(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text(
        "LLM_PROVIDER=openai\nOPENAI_MODEL=from-dotenv\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "from-shell")
    monkeypatch.setattr(models, "load_environment", ORIGINAL_LOAD_ENVIRONMENT)

    models.load_environment()

    assert models.resolve_provider_name() == "openai"
    assert models.resolve_model_name("openai") == "from-shell"


@pytest.mark.parametrize("model_name", models.GEMINI_MODELS)
def test_all_advertised_gemini_models_build_compatible_requests(
    monkeypatch, model_name
) -> None:
    client = FakeGeminiClient()
    monkeypatch.setattr(models, "create_gemini_client", lambda: client)

    assert models.run_gemini(model_name, "prompt", 0.2, 0.7) == "generated"

    request = client.models.requests[1][1]
    assert request["model"] == models.GEMINI_MODELS[model_name]
    config = request["config"].model_dump(exclude_none=True)
    assert "temperature" not in config
    assert "top_p" not in config
    assert "thinking_config" not in config
    assert client.closed is True


@pytest.mark.parametrize("model_name", models.OPENAI_MODELS)
def test_all_advertised_openai_models_use_responses_api(monkeypatch, model_name) -> None:
    clients: list[FakeOpenAIClient] = []
    constructor_calls = []
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    def make_client(**kwargs):
        constructor_calls.append(kwargs)
        client = FakeOpenAIClient()
        clients.append(client)
        return client

    monkeypatch.setattr(models, "OpenAI", make_client)

    assert models.run_openai(model_name, "prompt", 0.2, 0.7) == "generated"
    request = clients[0].responses.requests[0]
    assert request["model"] == models.OPENAI_MODELS[model_name]
    assert request["input"] == "prompt"
    if model_name in {"gpt-4.1", "gpt-4o"}:
        assert request["temperature"] == 0.2
        assert request["top_p"] == 0.7
    else:
        assert "temperature" not in request
        assert "top_p" not in request
    assert constructor_calls == [{"api_key": "openai-secret"}]
    assert clients[0].closed is True


@pytest.mark.parametrize("provider", ["deepseek", "nvidia"])
def test_all_advertised_openai_compatible_models(monkeypatch, provider) -> None:
    key_name = models.PROVIDER_API_KEY_ENV_VARS[provider]
    monkeypatch.setenv(key_name, "provider-secret")
    clients: list[FakeOpenAIClient] = []

    def make_client(**kwargs):
        client = FakeOpenAIClient()
        clients.append(client)
        return client

    monkeypatch.setattr(models, "OpenAI", make_client)
    runner = models.RUNNERS[provider]

    for model_name, model_id in models.PROVIDER_MODELS[provider].items():
        assert runner(model_name, "prompt", 0.2, 0.7) == "generated"
        assert clients[-1].chat.completions.requests[0]["model"] == model_id
        assert clients[-1].closed is True


@pytest.mark.parametrize("provider", models.PROVIDERS)
def test_provider_specific_model_defaults(monkeypatch, provider) -> None:
    configured_model = f"exact-{provider}-model-id"
    monkeypatch.setenv(models.PROVIDER_MODEL_ENV_VARS[provider], configured_model)

    assert models.resolve_model_name(provider) == configured_model


def test_exact_unlisted_model_ids_are_supported() -> None:
    assert models.get_model_id("new-model-preview", {}) == "new-model-preview"


def test_missing_api_key_has_actionable_error() -> None:
    with pytest.raises(models.ProviderConfigurationError, match="OPENAI_API_KEY"):
        models.run_openai("gpt-4.1", "prompt", 0.2, 0.7)

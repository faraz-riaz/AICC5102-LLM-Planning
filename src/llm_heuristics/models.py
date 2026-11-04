import logging
import os
import re
from collections.abc import Callable, Mapping
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI


# These aliases are the models we exercise in lightweight tests. Exact provider
# model IDs are also accepted so a newly released model does not require a code
# change before it can be tried.
GEMINI_MODELS = {
    "gemini-3.8-flash": "gemini-3.8-flash",
    "gemini-3.7-flash": "gemini-3.7-flash",
    "gemini-3.5-flash": "gemini-3.5-flash",
    "gemini-3.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite": "gemini-3.1-flash-lite",
    "gemini-3.1-pro": "gemini-3.1-pro-preview",
    "gemini-3-flash": "gemini-3-flash-preview",
}

OPENAI_MODELS = {
    "gpt-6-astra": "gpt-6-astra",
    "gpt-6.1-sol": "gpt-6.1-sol",
    "gpt-6.1-terra": "gpt-6.1-terra",
    "gpt-6-luna": "gpt-6-luna",
    "gpt-5.2": "gpt-5.2-2025-12-11",
    "gpt-4.1": "gpt-4.1-2025-04-14",
    "gpt-4o": "gpt-4o-2024-08-06",
}

DEEPSEEK_MODELS = {
    "deepseek-r1": "deepseek-reasoner",
    "deepseek-v3": "deepseek-chat",
}

NVIDIA_MODELS = {
    "kimi-k2.5": "moonshotai/kimi-k2.5",
    "glm5": "z-ai/glm5",
    "gpt-oss20b": "openai/gpt-oss-20b",
    "gpt-oss120b": "openai/gpt-oss-120b",
    "qwen3.5-397b": "qwen/qwen3.5-397b-a17b",
}

PROVIDER_MODELS = {
    "gemini": GEMINI_MODELS,
    "deepseek": DEEPSEEK_MODELS,
    "nvidia": NVIDIA_MODELS,
    "openai": OPENAI_MODELS,
}
PROVIDERS = tuple(PROVIDER_MODELS)
PROVIDER_DEFAULT_MODELS = {
    "gemini": "gemini-3.8-flash",
    "deepseek": "deepseek-v3",
    "nvidia": "kimi-k2.5",
    "openai": "gpt-4.1",
}
PROVIDER_MODEL_ENV_VARS = {
    "gemini": "GEMINI_MODEL",
    "deepseek": "DEEPSEEK_MODEL",
    "nvidia": "NVIDIA_MODEL",
    "openai": "OPENAI_MODEL",
}
PROVIDER_API_KEY_ENV_VARS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class ProviderConfigurationError(ValueError):
    """Raised when a selected provider is missing required configuration."""


def load_environment() -> None:
    """Load a local .env without replacing variables set by the shell or CI."""
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def sanitize_llm_answer(answer: str) -> str:
    if "```" not in answer:
        return answer
    match = re.search(r"```(?:\w+\n)?(.*?)```", answer, re.DOTALL)
    return match.group(1) if match else answer


def get_model_id(model: str, available_models: Mapping[str, str]) -> str:
    """Resolve a tested alias, while allowing an exact provider model ID."""
    model = model.strip()
    if not model:
        raise ValueError("Model name cannot be empty.")
    return available_models.get(model, model)


def resolve_provider_name(provider: str | None = None) -> str:
    load_environment()
    selected = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()
    if selected not in PROVIDER_MODELS:
        supported = ", ".join(PROVIDERS)
        raise ProviderConfigurationError(
            f"Unknown LLM provider {selected!r}. Choose one of: {supported}."
        )
    return selected


def resolve_model_name(provider: str, model_name: str | None = None) -> str:
    provider = resolve_provider_name(provider)
    env_var = PROVIDER_MODEL_ENV_VARS[provider]
    selected = model_name or os.getenv(env_var) or PROVIDER_DEFAULT_MODELS[provider]
    # Resolve here to validate empty values, but retain the friendly alias for
    # logging and provider-specific capability checks.
    get_model_id(selected, PROVIDER_MODELS[provider])
    return selected


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _required_environment(name: str, provider: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise ProviderConfigurationError(
        f"{provider} requires {name}. Copy .env.example to .env and set it, "
        "or export it in the shell."
    )


def describe_provider_configuration(
    provider: str | None = None, model_name: str | None = None
) -> dict[str, str]:
    """Validate local configuration without exposing secrets or calling an API."""
    provider = resolve_provider_name(provider)
    model_name = resolve_model_name(provider, model_name)
    description = {
        "provider": provider,
        "model": model_name,
        "model_id": get_model_id(model_name, PROVIDER_MODELS[provider]),
    }
    if provider == "gemini":
        if _is_true(os.getenv("GOOGLE_GENAI_USE_VERTEXAI")):
            description.update(
                auth_mode="vertex_adc",
                project=_required_environment(
                    "GOOGLE_CLOUD_PROJECT", "Gemini on Vertex AI"
                ),
                location=_required_environment(
                    "GOOGLE_CLOUD_LOCATION", "Gemini on Vertex AI"
                ),
            )
        else:
            if os.getenv("GOOGLE_API_KEY"):
                description.update(
                    auth_mode="developer_api_key",
                    credential_source="GOOGLE_API_KEY",
                )
            elif os.getenv("GEMINI_API_KEY"):
                description.update(
                    auth_mode="developer_api_key",
                    credential_source="GEMINI_API_KEY",
                )
            else:
                raise ProviderConfigurationError(
                    "Gemini Developer API requires GEMINI_API_KEY (or "
                    "GOOGLE_API_KEY). Copy .env.example to .env and set one key."
                )
    else:
        key_name = PROVIDER_API_KEY_ENV_VARS[provider]
        _required_environment(key_name, provider)
        description.update(auth_mode="api_key", credential_source=key_name)
    return description


def create_gemini_client():
    """Create a Gemini Developer API or Vertex AI client from environment config."""
    load_environment()
    if _is_true(os.getenv("GOOGLE_GENAI_USE_VERTEXAI")):
        project = _required_environment("GOOGLE_CLOUD_PROJECT", "Gemini on Vertex AI")
        location = _required_environment("GOOGLE_CLOUD_LOCATION", "Gemini on Vertex AI")
        logging.info(
            "Using Gemini through Vertex AI with Application Default Credentials "
            "(%s/%s).",
            project,
            location,
        )
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=types.HttpOptions(api_version="v1"),
        )

    # This matches the SDK's documented precedence when both variables exist.
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ProviderConfigurationError(
            "Gemini Developer API requires GEMINI_API_KEY (or GOOGLE_API_KEY). "
            "Copy .env.example to .env and set one key."
        )
    key_source = "GOOGLE_API_KEY" if os.getenv("GOOGLE_API_KEY") else "GEMINI_API_KEY"
    logging.info("Using Gemini Developer API credentials from %s.", key_source)
    return genai.Client(api_key=api_key)


def _gemini_generation_config(
    model_id: str, temperature: float, top_p: float
) -> types.GenerateContentConfig:
    config: dict[str, object] = {"response_mime_type": "text/plain"}
    # Gemini 3+ rejects the legacy sampling and integer thinking-budget fields.
    # Omitting them lets the service use the model's supported defaults.
    if not model_id.startswith(("gemini-3", "gemini-4")):
        config.update(temperature=temperature, top_p=top_p)
    return types.GenerateContentConfig(**config)


def run_gemini(
    model_name: str | None, prompt: str, temperature: float, top_p: float
) -> str:
    model_name = resolve_model_name("gemini", model_name)
    model_id = get_model_id(model_name, GEMINI_MODELS)
    client = create_gemini_client()
    try:
        token_count = client.models.count_tokens(
            model=model_id, contents=prompt
        ).total_tokens
        logging.info("#tokens in prompt: %s", token_count)

        response = client.models.generate_content(
            model=model_id,
            config=_gemini_generation_config(model_id, temperature, top_p),
            contents=prompt,
        )
        logging.info("Gemini usage metadata:\n%s", response.usage_metadata)
        answer = response.text or ""
        print(answer)
        return answer
    finally:
        client.close()


def _openai_compatible_client(provider: str, base_url: str | None = None) -> OpenAI:
    load_environment()
    api_key = _required_environment(PROVIDER_API_KEY_ENV_VARS[provider], provider)
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def run_deepseek(
    model_name: str | None, prompt: str, temperature: float, top_p: float
) -> str:
    model_name = resolve_model_name("deepseek", model_name)
    client = _openai_compatible_client("deepseek", "https://api.deepseek.com")
    try:
        completion = client.chat.completions.create(
            model=get_model_id(model_name, DEEPSEEK_MODELS),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=top_p,
            stream=False,
        )
        logging.info("LLM usage: %s", completion.usage)
        return completion.choices[0].message.content or ""
    finally:
        client.close()


def run_nvidia(
    model_name: str | None, prompt: str, temperature: float, top_p: float
) -> str:
    model_name = resolve_model_name("nvidia", model_name)
    client = _openai_compatible_client(
        "nvidia", "https://integrate.api.nvidia.com/v1"
    )
    thinking_opt_in_models = {"glm5", "qwen3.5-397b"}
    extra_body = None
    if model_name in thinking_opt_in_models:
        extra_body = {"chat_template_kwargs": {"enable_thinking": True}}

    try:
        completion = client.chat.completions.create(
            model=get_model_id(model_name, NVIDIA_MODELS),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=top_p,
            stream=False,
            extra_body=extra_body,
        )
        logging.info("LLM usage: %s", completion.usage)
        message = completion.choices[0].message
        reasoning = getattr(message, "reasoning_content", None)
        if reasoning:
            logging.info("Thinking summary:\n%s", reasoning)
        return message.content or ""
    finally:
        client.close()


def run_openai(
    model_name: str | None, prompt: str, temperature: float, top_p: float
) -> str:
    model_name = resolve_model_name("openai", model_name)
    model_id = get_model_id(model_name, OPENAI_MODELS)
    client = _openai_compatible_client("openai")
    request: dict[str, object] = {"model": model_id, "input": prompt}
    # Current reasoning models reject sampling controls unless a compatible
    # reasoning mode is also selected. Older non-reasoning models accept them.
    if model_id.startswith(("gpt-4.1", "gpt-4o")):
        request.update(temperature=temperature, top_p=top_p)
    try:
        response = client.responses.create(**request)
        logging.info("LLM usage: %s", response.usage)
        return response.output_text or ""
    finally:
        client.close()


RUNNERS: dict[str, Callable[[str | None, str, float, float], str]] = {
    "gemini": run_gemini,
    "deepseek": run_deepseek,
    "nvidia": run_nvidia,
    "openai": run_openai,
}


def run_model(
    provider: str,
    model_name: str | None,
    prompt: str,
    temperature: float,
    top_p: float,
) -> str:
    provider = resolve_provider_name(provider)
    model_name = resolve_model_name(provider, model_name)
    return RUNNERS[provider](model_name, prompt, temperature, top_p)

"""Multi-provider LLM API client with fallback cascade."""

import json
import os
import time
from typing import Any

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _get_api_keys(*patterns: str) -> list[str]:
    """Extract valid non-empty API keys from environment matching given patterns."""
    keys: list[str] = []
    for key, val in os.environ.items():
        if val.strip() and any(pat.upper() in key.upper() for pat in patterns):
            for part in val.split(","):
                clean = part.strip().replace("Bearer ", "")
                if clean and clean not in keys:
                    keys.append(clean)
    return keys


class Provider:
    """Dispatches chat completion requests across multiple LLM providers."""

    def __init__(
        self, model: str | None = None, provider: str | None = None
    ) -> None:
        """Initialize provider configurations and API keys from environment."""
        self.blacklisted_models: set[str] = set()
        gemini_keys = _get_api_keys("GEMINI", "GOOGLE")
        openai_keys = _get_api_keys("OPENAI", "OPEN_AI")
        openrouter_keys = _get_api_keys("OPENROUTER", "OPEN_ROUTER")
        nvidia_keys = _get_api_keys("NVIDIA")
        groq_keys = _get_api_keys("GROQ", "GROK")

        if model or provider:
            target_url = provider or ""
            target_model = model or ""

            if not target_url:
                if target_model.startswith("gemini"):
                    target_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                elif (
                    target_model.startswith("nvidia/")
                    or "nemotron" in target_model
                ):
                    target_url = "https://integrate.api.nvidia.com/v1"
                elif "/" in target_model:
                    target_url = "https://openrouter.ai/api/v1"
                else:
                    target_url = "https://api.openai.com/v1"

            url_lower = target_url.lower()
            if "openrouter" in url_lower:
                keys = openrouter_keys or openai_keys
            elif "googleapis" in url_lower or "gemini" in url_lower:
                keys = gemini_keys
            elif "openai" in url_lower:
                keys = openai_keys
            elif "nvidia" in url_lower:
                keys = nvidia_keys
            elif "groq" in url_lower:
                keys = groq_keys
            else:
                generic_key = os.environ.get("LLM_API_KEY")
                keys = (
                    [generic_key]
                    if generic_key
                    else (
                        openai_keys
                        or gemini_keys
                        or openrouter_keys
                        or nvidia_keys
                        or groq_keys
                    )
                )

            self.provider: list[dict[str, Any]] = [
                {
                    "name": "Custom",
                    "base_url": target_url.rstrip("/"),
                    "api_keys": keys,
                    "models": [target_model] if target_model else ["default"],
                }
            ]
        else:
            self.provider = [
                {
                    "name": "Gemini",
                    "base_url": (
                        "https://generativelanguage.googleapis.com/v1beta/openai"
                    ),
                    "api_keys": gemini_keys,
                    "models": [
                        "gemini-3.5-flash-lite",
                        "gemini-3.1-flash-lite",
                    ],
                },
                {
                    "name": "OpenRouter",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_keys": openrouter_keys or openai_keys,
                    "models": [
                        "meta-llama/llama-3.3-70b-instruct",
                        "qwen/qwen-2.5-coder-32b-instruct",
                        "mistralai/mistral-small-24b-instruct-2501",
                        "openai/gpt-4o",
                        "openai/gpt-4o-mini",
                    ],
                },
                {
                    "name": "NVIDIA",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                    "api_keys": nvidia_keys,
                    "models": [
                        "nvidia/nemotron-3-ultra-550b-a55b",
                    ],
                },
            ]

    @staticmethod
    def _reconstruct_stream(
        response: requests.Response, fallback_model: str
    ) -> dict[str, Any]:
        """Collect SSE chunks from stream and reconstruct standard response dict."""
        collected: list[str] = []
        model_name = fallback_model
        usage: dict[str, Any] = {}

        for line in response.iter_lines():
            if not line:
                continue
            line_str = (
                line.decode("utf-8") if isinstance(line, bytes) else line
            )
            if not line_str.startswith("data:"):
                continue
            raw_data = line_str[5:].strip()
            if raw_data == "[DONE]":
                break
            try:
                chunk = json.loads(raw_data)
                if chunk.get("error"):
                    err = chunk["error"].get("message", "API stream error")
                    raise RuntimeError(err)
                if chunk.get("model"):
                    model_name = chunk["model"]
                if chunk.get("usage"):
                    usage = chunk["usage"]
                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        collected.append(content)
            except json.JSONDecodeError:
                continue

        return {
            "model": model_name,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "".join(collected),
                    }
                }
            ],
            "usage": usage,
        }

    def send_request(self, payload: dict[str, Any]) -> tuple[Any, int]:
        """Send chat completion request trying providers and models in cascade."""
        retries = 0
        max_retries = 2
        last_error = None
        for provider in self.provider:
            api_keys = [k for k in provider["api_keys"]]
            if not api_keys:
                continue
            for model in provider["models"]:
                if model in self.blacklisted_models:
                    continue
                skip_model = False
                for key in api_keys:
                    if skip_model:
                        break
                    try:
                        print(
                            f"🔄 Attempting with [{provider['name']}]"
                            f" | Model: {model}"
                        )

                        endpoint = f"{provider['base_url']}/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        }
                        if "openrouter" in provider["base_url"]:
                            headers["HTTP-Referer"] = (
                                "https://example.com/agent-smith"
                            )
                            headers["X-Title"] = "Agent-Smith"

                        payload["model"] = model
                        payload["stream"] = True
                        payload["stream_options"] = {"include_usage": True}
                        for attempt in range(max_retries):
                            try:
                                response = requests.post(
                                    endpoint,
                                    json=payload,
                                    headers=headers,
                                    stream=True,
                                    timeout=(2, 5),
                                )
                                if response.status_code in (401, 403, 429):
                                    retries += 1
                                    print(
                                        f"⚠️ Key/Quota issue ({response.status_code}) for model"
                                        f" '{model}'. Trying next API key..."
                                    )
                                    break
                                if response.status_code in (
                                    404,
                                    500,
                                    502,
                                    503,
                                    504,
                                ):
                                    retries += 1
                                    print(
                                        f"⚠️ Server/Model error ({response.status_code})"
                                        f" for [{provider['name']}] | Model: {model}."
                                        " Skipping model..."
                                    )
                                    skip_model = True
                                    break
                                if 400 <= response.status_code < 500:
                                    retries += 1
                                    print(
                                        f"⚠️ Client error ({response.status_code})"
                                        f" for [{provider['name']}] | Model: {model}."
                                        " Skipping model..."
                                    )
                                    skip_model = True
                                    break
                                response.raise_for_status()
                                data: dict[str, Any] = (
                                    self._reconstruct_stream(response, model)
                                )

                                print(
                                    f"✅ Success with [{provider['name']}]"
                                    f" | Model: {model}"
                                )
                                data["url"] = provider["base_url"]
                                return (data, retries)
                            except Exception as err:
                                retries += 1
                                print(
                                    f"attempt {attempt + 1}/{max_retries} failed {err}"
                                )
                                if attempt < max_retries - 1:
                                    time.sleep(2)
                                else:
                                    last_error = err
                                    print(
                                        f"Failed after {max_retries} attempt on model {model}. Skipping model..."
                                    )
                                    skip_model = True

                        if skip_model:
                            break
                    except Exception as err:
                        retries += 1
                        last_error = err
                        print(
                            f"⚠️ Attempt failed ({err}),"
                            f" falling back to next option..."
                        )

                if model not in self.blacklisted_models:
                    self.blacklisted_models.add(model)
                    print(
                        f"🚫 Blacklisting model '{model}' for remaining iterations of this task."
                    )
        raise RuntimeError(
            f"❌ Total LLM cascade failure. "
            f"Last encountered error: {last_error}"
        )

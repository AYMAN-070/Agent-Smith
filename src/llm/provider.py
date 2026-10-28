"""Multi-provider LLM API client with fallback cascade."""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def _get_api_keys(*patterns: str) -> list[str]:
    """Extract valid non-empty API keys from environment matching given patterns."""
    return [
        val.strip()
        for key, val in os.environ.items()
        if val.strip() and any(pat.upper() in key.upper() for pat in patterns)
    ]


class Provider:
    """Dispatches chat completion requests across multiple LLM providers."""

    def __init__(
        self, model: str | None = None, provider: str | None = None
    ) -> None:
        """Initialize provider configurations and API keys from environment."""
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
                    target_url = (
                        "https://generativelanguage.googleapis.com/v1beta/openai"
                    )
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
            elif "openai" in url_lower:
                keys = openai_keys
            elif "googleapis" in url_lower or "gemini" in url_lower:
                keys = gemini_keys
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
                    "name": "NVIDIA",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                    "api_keys": nvidia_keys,
                    "models": [
                        "nvidia/nemotron-3-ultra-550b-a55b",
                    ],
                },
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
                        "openai/gpt-4o",
                        "meta-llama/llama-3.3-70b-instruct",
                    ],
                },
            ]

    def send_request(self, payload: dict[str, Any]) -> tuple[Any, int]:
        """Send chat completion request trying providers and models in cascade."""
        retries = 0
        max_retries = 3
        last_error = None
        for provider in self.provider:
            api_keys = [k for k in provider["api_keys"]]
            if not api_keys:
                continue
            for key in api_keys:
                for model in provider["models"]:
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
                                "https://github.com/agent-smith"
                            )
                            headers["X-Title"] = "Agent-Smith"

                        payload["model"] = model
                        for attempt in range(max_retries):
                            try:
                                response = requests.post(
                                    endpoint,
                                    json=payload,
                                    headers=headers,
                                )
                                if response.status_code == 429:
                                    retries += 1
                                    print(
                                        f"⚠️ Quota exceeded (429) for model"
                                        f" '{model}'. Skipping to next candidate..."
                                    )
                                    break
                                if response.status_code in (
                                    400,
                                    401,
                                    403,
                                    404,
                                ):
                                    retries += 1
                                    print(
                                        f"⚠️ Client error ({response.status_code})"
                                        f" for [{provider['name']}] | Model: {model}."
                                        " Skipping..."
                                    )
                                    break
                                response.raise_for_status()
                                data: dict[str, Any] = response.json()
                                if "error" in data:
                                    print(
                                        f"⚠️ API Error: {data['error'].get('message')}"
                                    )
                                    raise RuntimeError(
                                        data["error"].get("message")
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
                                        f"Failed after {max_retries} attempt on model {model}"
                                    )

                    except Exception as err:
                        retries += 1
                        last_error = err
                        print(
                            f"⚠️ Attempt failed ({err}),"
                            f" falling back to next option..."
                        )
        raise RuntimeError(
            f"❌ Total LLM cascade failure. "
            f"Last encountered error: {last_error}"
        )

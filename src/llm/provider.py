"""Multi-provider LLM API client with fallback cascade."""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class Provider:
    """Dispatches chat completion requests across multiple LLM providers."""

    def __init__(
        self, model: str | None = None, provider: str | None = None
    ) -> None:
        """Initialize provider configurations and API keys from environment."""
        gemini_keys = [
            val
            for key, val in os.environ.items()
            if key.startswith("GEMINI_API")
        ]
        openai_keys = [
            val for key, val in os.environ.items() if key.startswith("OPEN")
        ]

        nvidia_keys = [
            val
            for key, val in os.environ.items()
            if key.startswith("NVIDIA_API")
        ]

        if model and provider:
            keys = gemini_keys or openai_keys or nvidia_keys
            self.provider = [
                {
                    "name": "Custom",
                    "base_url": provider,
                    "api_keys": keys,
                    "models": [model],
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
                    "name": "NVIDIA",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                    "api_keys": nvidia_keys,
                    "models": [
                        "nvidia/nemotron-3-ultra-550b-a55b",
                    ],
                },
                {
                    "name": "OpenRouter",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_keys": openai_keys,
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
                        payload["model"] = model
                        for attempt in range(max_retries):
                            try:
                                response = requests.post(
                                    endpoint,
                                    json=payload,
                                    headers=headers,
                                    timeout=30,
                                )
                                if response.status_code == 429:
                                    retries += 1
                                    print(
                                        f"⚠️ Quota exceeded (429) for model"
                                        f" '{model}'. Skipping to next candidate..."
                                    )
                                    break
                                response.raise_for_status()
                                data = response.json()
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

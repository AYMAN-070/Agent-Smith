import os

import requests
from dotenv import load_dotenv
from typing import Any

load_dotenv()


class Provider:
    def __init__(self) -> None:
        gemini_keys = [
            val
            for key, val in os.environ.items()
            if key.startswith("GEMINI_API")
        ]
        openai_keys = [
            val for key, val in os.environ.items() if key.startswith("OPEN")
        ]
        groq_keys = [
            val for key, val in os.environ.items() if key.startswith("GROQ")
        ]
        self.provider = [
            {
                "name": "Gemini",
                "base_url": (
                    "https://generativelanguage.googleapis.com/v1beta/openai"
                ),
                "api_keys": gemini_keys,
                "models": ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
            },
            {
                "name": "OpenRouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_keys": openai_keys,
                "models": ["meta-llama/llama-3.3-70b-instruct"],
            },
            {
                "name": "Groq",
                "base_url": "https://api.groq.com/openai/v1",
                "api_keys": groq_keys,
                "models": ["llama-3.3-70b-versatile"],
            },
        ]

    def send_request(self, payload: dict) -> tuple[Any, int]:
        retries = 0
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
                        response = requests.post(
                            endpoint, json=payload, headers=headers
                        )
                        if response.status_code == 429:
                            retries += 1
                            print(
                                f"⚠️ Quota exceeded (429) for model"
                                f" '{model}'. Skipping to next candidate..."
                            )
                            continue
                        response.raise_for_status()
                        data = response.json()
                        if "error" in data:
                            retries += 1
                            print(
                                f"⚠️ API Error: {data['error'].get('message')}"
                            )
                            continue
                        print(
                            f"✅ Success with [{provider['name']}]"
                            f" | Model: {model}"
                        )
                        data["url"] = provider["base_url"]
                        return (data, retries)
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

    def cli(self):



# if __name__ == "__main__":
#     test = Provider()
#     test.send_request({"t": "u"})

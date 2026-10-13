import os

import requests
from dotenv import load_dotenv

from src.agent.parser import ExtractCode
from src.agent.prompt import Prompt

load_dotenv()


def llm(prompt: Prompt) -> str:

    llm_url = os.getenv("GEMINI_URL")
    keys = [
        val for key, val in os.environ.items() if key.startswith("GEMINI_API")
    ]
    api_key = keys[0]
    model = "gemini-3.5-flash-lite"
    endpoint = f"{llm_url}/v1beta/models/{model}:generateContent?key={api_key}"
    payload = prompt.payload

    headers = {"Content-Type": "application/json"}
    response = requests.post(endpoint, json=payload, headers=headers)
    data = response.json()
    text: str = data["candidates"][0]["content"]["parts"][0]["text"]
    # token = data["usageMetadata"]
    extractor = ExtractCode(text)
    code = extractor.code(text)
    print(code)
    return code

    # return (
    #     f"reponse : {text}\n token of the question"
    #     f"= {token['promptTokenCount']}\n"
    #     f"token for the answer = {token['candidatesTokenCount']}"
    # )

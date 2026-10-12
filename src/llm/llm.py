import os
import requests
from dotenv import load_dotenv
load_dotenv()


def llm(prompt: str) -> str:

    llm_url = os.getenv("GEMINI_URL")
    keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API")]

    api_key = keys[0]
    model = "gemini-3.5-flash-lite"
    endpoint = f"{llm_url}/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        # System instructions to define the model's persona, constraints, and behavior
        "system_instruction": {
            "parts": [
                {
                    "text": "You are a professional Python developer. Answer concisely and only in Python code when applicable."
                }
            ]
        },

        # User prompt / conversation history
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],

        # Generation parameters to tune the output
        "generationConfig": {
            "temperature": 0.2,       # Lower values result in more deterministic and focused responses
            "maxOutputTokens": 1000,   # Maximum number of tokens the model can generate
            "topP": 0.95,             # Nucleus sampling: selects tokens whose cumulative probability reaches P
            "topK": 40                # Top-K sampling: limits selection to the top K most probable tokens
        }
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(endpoint, json=payload, headers=headers)
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    token = data["usageMetadata"]
    return (f"reponse : {text}\n token of the question"
            f"= {token["promptTokenCount"]}\n"
            f"token for the answer = {token["candidatesTokenCount"]}")


if __name__ == "__main__":
    prompt = "Hello, present youserlf in 2 sentence and tell me what model you are"
    reponse = llm(prompt)
    print(reponse)

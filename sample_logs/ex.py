import os
import requests
from dotenv import load_dotenv

load_dotenv()

response = requests.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY")},
    timeout=30,
)

for m in response.json()["models"]:
    if "generateContent" in m.get("supportedGenerationMethods", []):
        print(m["name"])
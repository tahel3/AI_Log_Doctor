import json
import os
import time
from typing import Optional

import requests

from .models import ErrorGroup


class LLMError(Exception):
    """Raised when the LLM API call fails."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMClient:
    """Sends error groups to Gemini and stores the analysis back on each group.
    Requires GEMINI_API_KEY and optionally GEMINI_MODEL environment variables.
    """

    DEFAULT_MODEL = "gemini-flash-lite-latest"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None, max_retries: int = 3,
base_delay: float = 2.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.max_retries = max_retries
        self.base_delay = base_delay
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not set")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse_group(self, group: ErrorGroup) -> ErrorGroup:
        """Fill group.ai_analysis and group.suggested_fix in-place, then return it."""
        prompt = self._build_prompt(group)
        response_text =self._chat_with_retry(prompt)
        group.ai_analysis, group.suggested_fix = self._parse_response(response_text)
        return group

    def analyse_groups(self, groups: list[ErrorGroup]) -> list[ErrorGroup]:
        """Analyse every group in the list (sequential calls)."""
        for group in groups:
            try:
                self.analyse_group(group)
            except LLMError as e:
                group.ai_analysis=f"Analysis failed:{e}"
                group.suggested_fix =""
            time.sleep(1)
        return groups

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, group: ErrorGroup) -> str:
        samples = "\n".join(
            f"  [{i+1}] {e.raw}" for i, e in enumerate(group.entries[:5])
        )
        return (
            "You are an expert software engineer analysing log errors.\n\n"
            f"The following {group.count} log entries share the same root-cause signature:\n"
            f"Signature: {group.signature}\n\n"
            f"Sample entries (up to 5):\n{samples}\n\n"
            "Respond with a JSON object with exactly two keys:\n"
            '"root_cause": one paragraph explaining the root cause,\n'
            '"fix": concrete steps to resolve the issue.'
        )

    def _chat(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{self.model}:generateContent"
        )
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        try:
            response = requests.post(url, headers=headers, json=body, timeout=60)

        except requests.Timeout as e:
            raise LLMError("Request timed out", retryable=True) from e
        except requests.ConnectionError as e:
            raise LLMError("Connection failed", retryable=True) from e
        if response.status_code != 200:
            retryable = response.status_code in (429, 500, 502, 503, 504)
            message = self._error_message(response)
            raise LLMError(
                f"HTTP {response.status_code}: {message}", retryable=retryable
            )

        data = response.json()
        if not data.get("candidates"):
            raise LLMError("No candidates in response", retryable=False)
        reason = data["candidates"][0].get("finishReason")
        if reason != "STOP":
            raise LLMError(f"Generation stopped: {reason}", retryable=False)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    def _chat_with_retry(self, prompt: str) -> str:
        for attempt in range(self.max_retries + 1):
            try:
                return self._chat(prompt)
            except LLMError as e:
                if not e.retryable:
                    raise
                if attempt==self.max_retries:
                    raise
                
                delay=self.base_delay * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed ({e}), retrying in {delay}s...")
                time.sleep(delay)
    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            return response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            return response.text
    @staticmethod
    def _parse_response(text: str) -> tuple[str, str]:
        try:
            data = json.loads(text)
            return data["root_cause"], data["fix"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return "Could not parse AI response", text


if __name__ == "__main__":
    from dotenv import load_dotenv
    from .parser import LogParser
    from .grouper import ErrorGrouper

    load_dotenv()
    log_path = os.path.join(os.path.dirname(__file__), "..", "sample_logs", "app.log")
    entries = LogParser().parse_file(log_path)
    groups = ErrorGrouper().group(entries)

    LLMClient().analyse_groups(groups)

    for g in groups:
        print(f"[{g.count}] {g.signature}")
        print("   ROOT CAUSE:", g.ai_analysis[:100])
        print()
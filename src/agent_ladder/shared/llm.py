"""Shared LiteLLM client helpers for tutorial steps."""

import os
from pathlib import Path

import litellm
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DEFAULT_MODEL = "qwen3-max"


def complete(messages, model=DEFAULT_MODEL, **kwargs):
    """Send chat messages to a model and return the raw LiteLLM response."""
    return litellm.completion(
        model=f"anthropic/{model}",
        api_base=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
        messages=messages,
        **kwargs,
    )

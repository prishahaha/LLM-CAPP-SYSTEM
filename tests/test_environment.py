"""Environment sanity check for the LLM-CAPP research project.

Run with: pytest tests/test_environment.py -v
Or directly: python tests/test_environment.py
"""

import os
import sys

import anthropic
import chromadb
import fpdf
import langchain
import langchain_anthropic
import langchain_community
import matplotlib
import numpy
import pandas
import seaborn
import sentence_transformers
import streamlit
import tiktoken
from dotenv import load_dotenv


def test_environment():
    load_dotenv()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    assert api_key, (
        "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
    )

    model = os.environ.get("LLM_MODEL", "claude-sonnet-5")
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=16,
            messages=[{"role": "user", "content": "Respond with just the word OK"}],
        )
    except anthropic.AuthenticationError:
        raise AssertionError("Invalid ANTHROPIC_API_KEY — authentication failed.")
    except anthropic.NotFoundError:
        raise AssertionError(f"Model '{model}' not found — check LLM_MODEL in .env.")
    except anthropic.RateLimitError:
        raise AssertionError("Rate limited by the Anthropic API — try again shortly.")
    except anthropic.APIConnectionError:
        raise AssertionError("Could not connect to the Anthropic API — check your network.")
    except anthropic.APIStatusError as e:
        raise AssertionError(f"Anthropic API error ({e.status_code}): {e.message}")

    reply_text = next(
        (block.text for block in response.content if block.type == "text"), ""
    )
    print(f"\nModel used: {model}")
    print(f"Claude replied: {reply_text!r}")

    assert reply_text.strip(), "Received an empty response from the API."

    print("All systems ready")


if __name__ == "__main__":
    try:
        test_environment()
    except AssertionError as e:
        print(f"Environment check FAILED: {e}", file=sys.stderr)
        sys.exit(1)

"""
Centralised configuration for foundry-doc-assistant.

Reads environment variables from .env (if present) and exposes typed settings.
All Azure Foundry API access flows through here so there's one place to swap
endpoints, keys, or model deployments.

Importing this module validates required env vars; missing values raise a
clear error at import time rather than failing later inside an API call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (same directory as this file).
load_dotenv(Path(__file__).parent / ".env")


@dataclass(frozen=True)
class Settings:
    """All settings the system needs to talk to Azure Foundry."""

    foundry_base_url: str
    foundry_api_key: str
    generator_deployment: str
    embedding_deployment: str

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.environ.get("AZURE_FOUNDRY_BASE_URL")
        api_key = os.environ.get("AZURE_FOUNDRY_API_KEY")
        generator = os.environ.get("GENERATOR_DEPLOYMENT", "gpt-4o")
        embedding = os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

        missing = []
        if not base_url:
            missing.append("AZURE_FOUNDRY_BASE_URL")
        if not api_key:
            missing.append("AZURE_FOUNDRY_API_KEY")

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in your values."
            )

        # Strip trailing slash so SDK paths don't double up.
        return cls(
            foundry_base_url=base_url.rstrip("/"),
            foundry_api_key=api_key,
            generator_deployment=generator,
            embedding_deployment=embedding,
        )


# Module-level singleton — importing this module validates env immediately.
settings = Settings.from_env()

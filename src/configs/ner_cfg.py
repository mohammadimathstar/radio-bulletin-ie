from dataclasses import dataclass

from openai import OpenAI


@dataclass
class ApiConfig:
    """Bundles per-run API settings so call sites take a single argument."""
    client: OpenAI
    model: str

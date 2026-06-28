"""Ollama API client."""

import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def normalize_ollama_url(url: str | None) -> str:
    """Validate and normalize an Ollama base URL."""
    raw = (url or DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    if not raw:
        raise ValueError("Ollama URL is required")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Ollama URL must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("Invalid Ollama URL")
    return raw


def resolve_base_url(override: str | None = None) -> str:
    if override and override.strip():
        return normalize_ollama_url(override)
    return normalize_ollama_url(DEFAULT_OLLAMA_BASE_URL)


async def list_models(base_url: str | None = None) -> list[str]:
    url = resolve_base_url(base_url)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{url}/api/tags")
        r.raise_for_status()
        models = r.json().get("models", [])
        return [m["name"] for m in models]


async def chat(
    messages: list[dict],
    model: str | None = None,
    stream: bool = False,
    base_url: str | None = None,
) -> dict:
    url = resolve_base_url(base_url)
    model = model or DEFAULT_MODEL
    payload = {"model": model, "messages": messages, "stream": stream}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{url}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()


def extract_plot_spec(text: str) -> dict | None:
    """Parse ```plot ... ``` JSON block from model response."""
    patterns = [
        r"```plot\s*([\s\S]*?)```",
        r"```json\s*([\s\S]*?)```",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            try:
                spec = json.loads(raw)
                if isinstance(spec, dict) and "type" in spec:
                    return spec
            except json.JSONDecodeError:
                continue
    return None


def strip_plot_block(text: str) -> str:
    text = re.sub(r"```plot\s*[\s\S]*?```", "", text)
    text = re.sub(r"```report\s*[\s\S]*?```", "", text)
    return text.strip()


def extract_report_updates(text: str) -> list[dict]:
    """Parse ```report ... ``` or ```json ... ``` blocks with report actions."""
    updates = []
    seen: set[str] = set()
    patterns = [
        r"```report\s*([\s\S]*?)```",
        r"```json\s*([\s\S]*?)```",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            raw = m.group(1).strip()
            if raw in seen:
                continue
            seen.add(raw)
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict) and "action" in obj:
                    updates.append(obj)
                elif isinstance(obj, list):
                    updates.extend(x for x in obj if isinstance(x, dict) and "action" in x)
            except json.JSONDecodeError:
                continue
    return updates


async def health_check(base_url: str | None = None) -> dict[str, Any]:
    url = resolve_base_url(base_url)
    try:
        models = await list_models(url)
        return {"ok": True, "url": url, "models": models}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}

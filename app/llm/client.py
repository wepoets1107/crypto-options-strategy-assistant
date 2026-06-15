from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings


async def chat_json(settings: Settings, system: str, user: str) -> dict[str, Any] | None:
    if not settings.llm_enabled:
        return None
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(f"{settings.llm_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


async def chat_text(settings: Settings, system: str, user: str) -> str | None:
    if not settings.llm_enabled:
        return None
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(f"{settings.llm_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

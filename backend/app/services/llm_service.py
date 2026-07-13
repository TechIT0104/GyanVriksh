"""LLM client.

Two modes, chosen automatically:
  * If a real OpenAI API key is set in .env  -> GPT-4o primary, Ollama fallback.
  * If the key is empty/placeholder          -> Ollama is used directly (free,
    fully local, no API cost). The Ollama model is resolved at runtime: it uses
    settings.ollama_model if that model is installed, otherwise the first model
    reported by `ollama list`. This means it "just works" with whatever model
    you already pulled.
"""
import json
import logging

import httpx
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_openai: OpenAI | None = None
_resolved_ollama_model: str | None = None


def _use_ollama() -> bool:
    """True when no usable OpenAI key is configured."""
    key = (settings.openai_api_key or "").strip()
    return (not key) or ("REPLACE" in key) or (not key.startswith("sk-"))


def get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=settings.openai_api_key)
    return _openai


def _resolve_ollama_model() -> str:
    """Pick an installed Ollama model. Prefer settings.ollama_model; if it isn't
    installed, fall back to the first model `ollama list` returns."""
    global _resolved_ollama_model
    if _resolved_ollama_model:
        return _resolved_ollama_model
    preferred = settings.ollama_model
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=10)
        resp.raise_for_status()
        installed = [m["name"] for m in resp.json().get("models", [])]
        if preferred in installed:
            _resolved_ollama_model = preferred
        elif installed:
            _resolved_ollama_model = installed[0]
            logger.warning("Ollama model %s not installed; using %s instead",
                           preferred, _resolved_ollama_model)
        else:
            logger.error("No Ollama models installed. Run: ollama pull %s", preferred)
            _resolved_ollama_model = preferred
    except Exception as e:
        logger.warning("Could not query Ollama (%s); assuming %s", e, preferred)
        _resolved_ollama_model = preferred
    return _resolved_ollama_model


def _ollama_chat(messages: list[dict], temperature: float, json_mode: bool = False) -> str:
    payload = {
        "model": _resolve_ollama_model(),
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 512, "num_ctx": 4096},
    }
    if json_mode:
        payload["format"] = "json"
    resp = httpx.post(f"{settings.ollama_base_url}/api/chat", json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _ollama_stream(messages: list[dict], temperature: float):
    payload = {
        "model": _resolve_ollama_model(),
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature, "num_predict": 512, "num_ctx": 4096},
    }
    with httpx.stream("POST", f"{settings.ollama_base_url}/api/chat",
                      json=payload, timeout=300) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = data.get("message", {}).get("content")
            if token:
                yield token


def chat(messages: list[dict], temperature: float = 0.1, json_mode: bool = False) -> str:
    """Synchronous completion. Ollama-direct if no OpenAI key, else OpenAI with
    automatic Ollama fallback on any error."""
    if _use_ollama():
        return _ollama_chat(messages, temperature, json_mode)
    try:
        kwargs = {"model": settings.openai_model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = get_openai().chat.completions.create(**kwargs)
        return resp.choices[0].message.content
    except Exception as e:
        if settings.llm_fallback != "ollama":
            raise
        logger.warning("OpenAI failed (%s) — falling back to Ollama", e)
        return _ollama_chat(messages, temperature, json_mode)


def chat_json(messages: list[dict], temperature: float = 0.0) -> dict:
    raw = chat(messages, temperature=temperature, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Strip markdown fences the fallback model sometimes adds
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        return json.loads(cleaned)


def stream_chat(messages: list[dict], temperature: float = 0.1):
    """Generator yielding tokens. Streams from Ollama if no OpenAI key is set,
    otherwise from OpenAI."""
    if _use_ollama():
        yield from _ollama_stream(messages, temperature)
        return
    try:
        stream = get_openai().chat.completions.create(
            model=settings.openai_model, messages=messages,
            temperature=temperature, stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        if settings.llm_fallback != "ollama":
            raise
        logger.warning("OpenAI stream failed (%s) — falling back to Ollama", e)
        yield from _ollama_stream(messages, temperature)

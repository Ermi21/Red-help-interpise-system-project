"""Multi-provider LLM engine supporting Groq, Google Gemini (free API), and Ollama local API with automatic failover and token limit recovery."""

import json
import logging
import sys
import requests
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Ensure local site-packages are always in sys.path
for p in ["/home/appuser/.local/lib/python3.12/site-packages", "/usr/local/lib/python3.12/site-packages"]:
    if p not in sys.path:
        sys.path.append(p)


class LLMResult:
    def __init__(self, content: str, provider: str = "unknown", model: str = ""):
        self.content = content
        self.provider = provider
        self.model = model


def _call_groq(messages: list, api_key: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.1, timeout: int = 30) -> str:
    """Call Groq chat completion API directly via official client or HTTP."""
    from groq import Groq
    client = Groq(api_key=api_key, timeout=timeout)
    
    groq_msgs = []
    for m in messages:
        role = "user"
        if hasattr(m, "type"):
            role = "system" if m.type == "system" else "user"
        elif hasattr(m, "role"):
            role = "system" if m.role == "system" else "user"
        content = m.content if hasattr(m, "content") else str(m)
        groq_msgs.append({"role": role, "content": content})

    # Supported models on this Groq environment
    models_to_try = [model, "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]
    last_err = None
    for m_name in dict.fromkeys(models_to_try):
        try:
            resp = client.chat.completions.create(
                model=m_name,
                messages=groq_msgs,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            # If rate limit or token limit, continue to next or fail over
            if "rate_limit" in str(e).lower() or "token" in str(e).lower():
                raise
            continue
    if last_err:
        raise last_err
    return ""


def _call_gemini(messages: list, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.1, timeout: int = 30) -> str:
    """Call Google Gemini Free API directly via REST endpoint."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    # Convert LangChain/custom messages into Gemini contents format
    contents = []
    system_instruction = None

    for m in messages:
        role = getattr(m, "type", getattr(m, "role", "user"))
        content = m.content if hasattr(m, "content") else str(m)
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        else:
            contents.append({
                "role": "model" if role in ("assistant", "ai") else "user",
                "parts": [{"text": content}]
            })

    if not contents and system_instruction:
        contents.append({"role": "user", "parts": [{"text": "Hello"}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2048,
        }
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
    if not res.ok:
        # Fallback to gemini-2.0-flash or gemini-1.5-pro if 404/model unavailable
        if res.status_code in (404, 400) and model != "gemini-2.0-flash":
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            res2 = requests.post(fallback_url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
            if res2.ok:
                data2 = res2.json()
                return data2["candidates"][0]["content"]["parts"][0]["text"]
        raise RuntimeError(f"Gemini API error ({res.status_code}): {res.text[:300]}")

    data = res.json()
    candidates = data.get("candidates", [])
    if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
        return candidates[0]["content"]["parts"][0]["text"]
    return ""


def _call_ollama(messages: list, base_url: str = "http://ollama:11434", model: str = "llama3.1", temperature: float = 0.1, timeout: int = 30) -> str:
    """Call Ollama local chat API."""
    url = f"{base_url.rstrip('/')}/api/chat"
    ollama_msgs = []
    for m in messages:
        role = "user"
        if hasattr(m, "type"):
            role = "system" if m.type == "system" else "user"
        elif hasattr(m, "role"):
            role = "system" if m.role == "system" else "user"
        content = m.content if hasattr(m, "content") else str(m)
        ollama_msgs.append({"role": role, "content": content})

    res = requests.post(url, json={
        "model": model,
        "messages": ollama_msgs,
        "stream": False,
        "options": {"temperature": temperature}
    }, timeout=timeout)
    
    if not res.ok:
        raise RuntimeError(f"Ollama local API error ({res.status_code}): {res.text[:200]}")
    
    data = res.json()
    return data.get("message", {}).get("content", "")


class MultiProviderLLM:
    """
    Intelligent cascade LLM switcher:
      1. Tries Groq API (fast, high throughput).
      2. If Groq missing, rate limited, or token exceeded -> Tries Gemini Free API.
      3. If Gemini fails -> Tries local Ollama API.
      4. If all AI providers fail -> Returns None so deterministic live telemetry synthesis runs seamlessly.
    """
    def __init__(self, temperature: float = 0.1):
        self.temperature = temperature
        self.settings = get_settings()

    def invoke(self, messages) -> LLMResult:
        errors = []

        # ── 1. Groq Provider ──
        groq_key = (self.settings.groq_api_key or "").strip().strip('"').strip("'")
        if groq_key:
            try:
                model = self.settings.groq_chat_model or "llama-3.3-70b-versatile"
                content = _call_groq(messages, api_key=groq_key, model=model, temperature=self.temperature, timeout=self.settings.groq_request_timeout_s or 30)
                if content:
                    logger.info("Successfully generated response using Groq (%s)", model)
                    return LLMResult(content=content, provider="Groq", model=model)
            except Exception as e:
                logger.warning("Groq failed or rate-limited: %s. Switching to next provider...", e)
                errors.append(f"Groq: {e}")

        # ── 2. Gemini Free API Provider ──
        gemini_key = (getattr(self.settings, "gemini_api_key", "") or "").strip().strip('"').strip("'")
        if gemini_key:
            try:
                g_model = getattr(self.settings, "gemini_model", "gemini-1.5-flash") or "gemini-1.5-flash"
                content = _call_gemini(messages, api_key=gemini_key, model=g_model, temperature=self.temperature, timeout=getattr(self.settings, "gemini_request_timeout_s", 30))
                if content:
                    logger.info("Successfully generated response using Google Gemini (%s)", g_model)
                    return LLMResult(content=content, provider="Google Gemini", model=g_model)
            except Exception as e:
                logger.warning("Gemini failed or rate-limited: %s. Switching to next provider...", e)
                errors.append(f"Gemini: {e}")

        # ── 3. Ollama Local Provider ──
        try:
            ollama_url = self.settings.ollama_base_url or "http://ollama:11434"
            # Try host.docker.internal or ollama container
            for base in [ollama_url, "http://ollama:11434", "http://localhost:11434"]:
                try:
                    content = _call_ollama(messages, base_url=base, model="llama3.1", temperature=self.temperature, timeout=10)
                    if content:
                        logger.info("Successfully generated response using Ollama local")
                        return LLMResult(content=content, provider="Ollama Local", model="llama3.1")
                except Exception:
                    continue
        except Exception as e:
            errors.append(f"Ollama: {e}")

        # If all LLM APIs are unreachable or empty, return empty result to trigger live telemetry engine
        logger.warning("All LLM providers passed or unavailable (%s). Falling back to deterministic live engine.", "; ".join(errors))
        return LLMResult(content="", provider="Live Telemetry Engine", model="Direct DB/Server/Security")


def get_chat_llm(temperature: float = 0.1) -> MultiProviderLLM:
    """Return the multi-provider LLM instance with automatic switching."""
    return MultiProviderLLM(temperature=temperature)

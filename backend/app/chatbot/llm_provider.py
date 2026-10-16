"""LLM provider using Groq for chat generation."""

import sys
from functools import lru_cache
from app.config.settings import get_settings

# Ensure local site-packages are always in sys.path
for p in ["/home/appuser/.local/lib/python3.12/site-packages", "/usr/local/lib/python3.12/site-packages"]:
    if p not in sys.path:
        sys.path.append(p)


class _DirectGroqLLM:
    """Direct Groq client fallback that implements LangChain's invoke interface."""
    def __init__(self, model: str, api_key: str, temperature: float = 0.1, timeout: int = 60):
        from groq import Groq
        self.client = Groq(api_key=api_key, timeout=timeout)
        self.model = model
        self.temperature = temperature

    def invoke(self, messages):
        groq_msgs = []
        for m in messages:
            role = "user"
            if hasattr(m, "type"):
                role = "system" if m.type == "system" else "user"
            elif hasattr(m, "role"):
                role = "system" if m.role == "system" else "user"
            content = m.content if hasattr(m, "content") else str(m)
            groq_msgs.append({"role": role, "content": content})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=groq_msgs,
            temperature=self.temperature,
        )
        content = resp.choices[0].message.content or ""

        class _Result:
            def __init__(self, c):
                self.content = c

        return _Result(content)


@lru_cache(maxsize=8)
def get_chat_llm(temperature: float = 0.1):
    """Create and cache the configured Groq chat model."""
    settings = get_settings()

    api_key = (settings.groq_api_key or "").strip().strip('"').strip("'")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. "
            "Please provide a valid GROQ_API_KEY in your backend .env file."
        )

    raw_model = (settings.groq_chat_model or "").strip().strip('"').strip("'")
    # The Groq endpoint for this environment supports openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b
    if not raw_model or "llama" in raw_model.lower():
        model_name = "openai/gpt-oss-120b"
    else:
        model_name = raw_model

    # Try LangChain ChatGroq first
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            timeout=settings.groq_request_timeout_s or 60,
            max_retries=2,
        )
    except Exception:
        # High-performance direct fallback
        return _DirectGroqLLM(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            timeout=settings.groq_request_timeout_s or 60,
        )
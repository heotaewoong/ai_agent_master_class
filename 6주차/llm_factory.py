"""
LLM 팩토리 — 무료/유료 프로바이더 통합

.env 또는 환경변수 LLM_PROVIDER 로 프로바이더 선택:

  LLM_PROVIDER=groq      → Groq (무료, 권장) — https://console.groq.com
  LLM_PROVIDER=ollama    → Ollama (로컬 완전무료)
  LLM_PROVIDER=gemini    → Google Gemini (무료 티어 1500req/day)
  LLM_PROVIDER=openai    → OpenAI (유료)

Groq 무료 한도:
  llama-3.1-8b-instant  : 6000 토큰/분, 14400 요청/일
  llama-3.3-70b-versatile: 6000 토큰/분, 1000 요청/일 (품질 ↑)
"""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_core.language_models import BaseChatModel


def get_llm(temperature: float = 0) -> BaseChatModel:
    """환경변수 LLM_PROVIDER에 따라 LLM 인스턴스를 반환한다."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        return _groq_llm(temperature)
    elif provider == "ollama":
        return _ollama_llm(temperature)
    elif provider == "gemini":
        return _gemini_llm(temperature)
    elif provider == "openai":
        return _openai_llm(temperature)
    else:
        return _groq_llm(temperature)


# ──────────────────────────────────────────────
# 프로바이더별 팩토리
# ──────────────────────────────────────────────

def _groq_llm(temperature: float) -> BaseChatModel:
    """Groq — 완전 무료 (월 제한 있음, 매우 빠름)"""
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        raise ImportError("pip install langchain-groq")

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY가 없습니다.\n"
            "무료 발급: https://console.groq.com → API Keys → Create API Key\n"
            ".env에 GROQ_API_KEY=gsk-... 추가"
        )
    return ChatGroq(model=model, temperature=temperature, api_key=api_key)


def _ollama_llm(temperature: float) -> BaseChatModel:
    """Ollama — 완전 무료, 로컬 실행"""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError("pip install langchain-ollama")

    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model=model, temperature=temperature, base_url=base_url)


def _gemini_llm(temperature: float) -> BaseChatModel:
    """Google Gemini — 무료 티어 (1500 req/day)"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError("pip install langchain-google-genai")

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY가 없습니다. https://aistudio.google.com/app/apikey")
    return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)


def _openai_llm(temperature: float) -> BaseChatModel:
    """OpenAI — 유료 (기본값)"""
    from langchain_openai import ChatOpenAI
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=temperature)

"""
노드 5 — Newsletter Writer (뉴스레터 작성)

큐레이션된 기사들로 프리미엄 뉴스레터 초안을 생성한다.
- 마크다운 형식
- Claude에 바로 붙여넣기 가능한 형태
- 파일로 자동 저장
"""

from __future__ import annotations

import os
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage

from state import NewsHubState
from llm_factory import get_llm


def newsletter_writer_node(state: NewsHubState) -> dict:
    """큐레이션된 기사로 뉴스레터 초안을 작성한다."""

    curated_articles = state.get("curated_articles", [])
    trend_summary = state.get("trend_summary", "")
    trend_alerts = state.get("trend_alerts", [])
    article_clusters = state.get("article_clusters", [])
    key_insight = state.get("key_insight", "")
    topics = state.get("topics", ["AI"])

    if not curated_articles:
        return {
            "newsletter_draft": "# 뉴스레터를 생성할 기사가 없습니다.\n\n토픽이나 소스를 확인해주세요.",
            "newsletter_format": "markdown",
        }

    # 기사 정보 구성 (소스 다양성 표시 포함)
    articles_text = ""
    for i, article in enumerate(curated_articles, 1):
        score = article.get("score", 0)
        has_transcript = "🎬 자막 요약 포함" if article.get("has_transcript") else ""
        articles_text += f"""[기사 {i}] 관련도 {score:.0%} {has_transcript}
제목: {article.get('title', '제목 없음')}
소스: {article.get('source', '알 수 없음')}
요약: {article.get('summary', '요약 없음')[:400]}
URL: {article.get('url', '')}
---
"""

    # 클러스터 정보
    cluster_text = ""
    if article_clusters:
        cluster_text = "\n\n[테마 클러스터]\n" + "\n".join(
            f"- {c['theme']}: 기사 {c['indices']} — {c.get('theme_summary','')}"
            for c in article_clusters
        )

    # 급상승 트렌드
    spike_text = ""
    if trend_alerts:
        spike_text = "\n\n[급상승 키워드]\n" + "\n".join(
            f"- {a['keyword']} ({a['sources_count']}개 소스, {a['total_mentions']}회)"
            for a in trend_alerts[:8]
        )

    llm = get_llm(temperature=0.7)
    today = datetime.now().strftime("%Y년 %m월 %d일")
    topic_str = ", ".join(topics)
    
    evaluation_feedback = state.get("evaluation_feedback", "")
    feedback_instruction = f"\n\n[이전 버전의 피드백 - 이를 반드시 반영하여 개선하세요]:\n{evaluation_feedback}" if evaluation_feedback else ""

    system_prompt = f"""당신은 테크/AI 분야 최고의 뉴스레터 에디터입니다.
The Batch, Morning Brew, TLDR 수준의 전문적이고 읽기 쉬운 뉴스레터를 작성하세요.{feedback_instruction}

오늘 날짜: {today}
관심 토픽: {topic_str}
핵심 인사이트: {key_insight}

트렌드 분석:
{trend_summary}{cluster_text}{spike_text}

=== 뉴스레터 작성 형식 (이 구조를 반드시 따르세요) ===

# [임팩트 있는 제목 — 오늘의 가장 중요한 트렌드를 담을 것]
> **한 줄 요약**: 오늘 뉴스의 핵심을 한 문장으로

---

## ⚡ 오늘의 핵심 (2분 브리핑)
- **[포인트 1]**: 구체적 사실 (수치/회사명/제품명 포함)
- **[포인트 2]**: 구체적 사실
- **[포인트 3]**: 구체적 사실

---

## 📌 테마별 심층 분석

### [테마 1 이름] (클러스터 기반으로 섹션 구성)
**왜 중요한가**: 이 테마가 AI/테크 생태계에서 갖는 의미

각 기사에 대해:
#### [기사 제목]([URL])
- **무슨 일**: 핵심 사실 1~2문장
- **왜 중요**: 산업/기술적 의미
- **주목할 점**: 놓치기 쉬운 세부사항 또는 다음 움직임 예측

### [테마 2 이름]
(동일 구조 반복)

---

## 🔥 커뮤니티 반응 (HN/Reddit 인사이트)
Hacker News나 Reddit에서 화제가 된 내용이 있다면 커뮤니티의 시각을 요약

---

## 🔮 이번 주 주목할 것
- **단기 (1주)**: 곧 일어날 일
- **중기 (1개월)**: 이 트렌드가 향하는 방향
- **놓치면 안 되는 신호**: 아직 주류가 아니지만 중요한 움직임

---

*NewsHub Agent | {today} | 소스: YouTube + RSS + HN + Reddit + Arxiv*

=== 작성 원칙 ===
- 단순 요약 금지. 반드시 "왜 중요한지" "다음엔 무슨 일이 일어날지" 포함
- 구체적 수치, 회사명, 제품명을 적극 사용
- 기술 용어는 한국어 + 영문 병기 (예: 대형언어모델 LLM)
- 전체 길이: 800~1200자 (너무 길지 않게)
- 한국어로 작성
"""

    llm_error = None
    newsletter = None

    # 1차: 설정된 LLM (Gemini 등)
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=articles_text),
        ])
        newsletter = response.content.strip()
    except Exception as e:
        llm_error = str(e)

    # 2차: Gemini 실패 시 Groq로 재시도 (같은 프롬프트 유지)
    if not newsletter:
        try:
            from llm_factory import get_llm
            fallback_llm = get_llm(temperature=0.7)
            response = fallback_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=articles_text),
            ])
            newsletter = response.content.strip()
            llm_error = f"Gemini 실패 → Groq 폴백 사용 ({llm_error[:80]}...)"
        except Exception as e2:
            llm_error = f"LLM 전부 실패: {str(e2)}"
            newsletter = _fallback_newsletter(curated_articles, topics, trend_summary, today)

    # 파일로 저장
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"newsletter_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(newsletter)

    errors = [f"뉴스레터 LLM 실패: {llm_error}"] if llm_error else []
    return {
        "newsletter_draft": newsletter,
        "newsletter_format": "markdown",
        "error_messages": errors,
    }


def _fallback_newsletter(articles, topics, trend_summary, today):
    """LLM 실패 시 기본 템플릿으로 뉴스레터 생성"""
    topic_str = ", ".join(topics)

    lines = [
        f"# 📡 NewsHub Daily — {topic_str}",
        f"**{today}** | AI가 큐레이션한 오늘의 뉴스",
        "",
        "---",
        "",
        "## 🌟 트렌드 요약",
        trend_summary or "오늘의 트렌드 정보가 없습니다.",
        "",
        "---",
        "",
        "## 📰 주요 기사",
        "",
    ]

    for i, article in enumerate(articles, 1):
        title = article.get("title", "제목 없음")
        url = article.get("url", "#")
        source = article.get("source", "알 수 없음")
        summary = article.get("summary", "요약 없음")[:200]
        score = article.get("score", 0)

        lines.extend([
            f"### {i}. [{title}]({url})",
            f"📌 **출처**: {source} | **관련도**: {score:.0%}",
            f"> {summary}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 🔮 전망",
        "이 뉴스레터는 NewsHub Agent가 자동으로 큐레이션한 기사입니다.",
        "",
        "---",
        f"*Generated by NewsHub Agent on {today}*",
    ])

    return "\n".join(lines)

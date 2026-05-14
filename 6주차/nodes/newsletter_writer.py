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

    today = datetime.now().strftime("%Y년 %m월 %d일")
    topic_str = ", ".join(topics)

    # ── 기사 목록 구성 (링크를 마크다운으로 미리 변환해서 LLM에 전달) ──
    # 핵심: URL을 별도 필드로 주고 "반드시 이 링크를 그대로 사용"하도록 강제
    article_lines = []
    link_index = []  # 뉴스레터 하단 링크 모음용
    for i, article in enumerate(curated_articles, 1):
        title = article.get("title", "제목 없음")
        url   = article.get("url", "")
        src   = article.get("source", "알 수 없음")
        summ  = article.get("summary", "요약 없음")[:500]
        score = article.get("score", 0)
        md_link = f"[{title}]({url})" if url else title
        article_lines.append(
            f"[{i}] {md_link}\n"
            f"    출처: {src} | 관련도: {score:.0%}\n"
            f"    요약: {summ}\n"
            f"    URL: {url}"
        )
        if url:
            link_index.append(f"{i}. [{title}]({url}) — {src}")

    articles_text = "\n\n".join(article_lines)
    link_index_text = "\n".join(link_index)

    # 클러스터 정보
    cluster_text = ""
    if article_clusters:
        cluster_text = "\n\n[테마 클러스터]\n" + "\n".join(
            f"- {c['theme']}: 기사번호 {c['indices']} — {c.get('theme_summary','')}"
            for c in article_clusters
        )

    # 급상승 트렌드
    spike_text = ""
    if trend_alerts:
        spike_text = "\n\n[급상승 키워드]\n" + "\n".join(
            f"- {a['keyword']} ({a['sources_count']}개 소스, {a['total_mentions']}회)"
            for a in trend_alerts[:5]
        )

    llm = get_llm(temperature=0.7)

    evaluation_feedback = state.get("evaluation_feedback", "")
    feedback_instruction = f"\n\n[이전 피드백 - 반드시 반영]:\n{evaluation_feedback}" if evaluation_feedback else ""

    system_prompt = f"""당신은 AI/테크 분야 전문 뉴스레터 에디터입니다.
아래 수집된 기사들을 바탕으로 깊이 있는 한국어 뉴스레터를 작성하세요.{feedback_instruction}

오늘 날짜: {today} | 관심 토픽: {topic_str}
핵심 인사이트: {key_insight}
트렌드 요약: {trend_summary}{cluster_text}{spike_text}

━━━ 절대 규칙 (위반 시 실패) ━━━
① 각 기사를 소개할 때 반드시 원본 URL을 마크다운 링크 [제목](URL) 형식으로 포함한다.
② URL을 임의로 수정하거나 생략하지 않는다.
③ 아래 링크 모음 섹션의 링크를 뉴스레터 마지막에 그대로 붙인다.

━━━ 뉴스레터 구조 ━━━

# 📡 [핵심 트렌드를 담은 임팩트 있는 제목]
> 🗓️ {today} | ⏱️ 읽는 시간: 5분

---

## 🔍 오늘의 한눈 요약

> 💬 **핵심 한 줄**: [오늘 뉴스 전체를 관통하는 인사이트 1문장]

| 구분 | 내용 |
|------|------|
| 🔥 가장 뜨거운 소식 | 회사명·수치 포함한 구체적 사실 |
| 💡 주목할 기술/트렌드 | 기술명 + 한 줄 의미 |
| 🌏 국내 동향 | 국내 관련 소식 (없으면 글로벌 영향) |

---

## 📌 [테마 1 이름]

> **왜 지금인가?** 이 테마가 AI/테크 생태계에서 갖는 의미 2~3문장.

### 🔗 [기사제목](실제URL)  ← 반드시 실제 URL 사용
- **무슨 일이 있었나**: 핵심 사실 2~3문장. 수치·날짜·회사명 필수 포함.
- **왜 중요한가**: 이 사건이 업계·기술·사용자에게 미치는 영향.
- **놓치면 안 되는 것**: 뉴스 뒤에 숨겨진 시사점, 다음 움직임 예측.

### 🔗 [기사제목](실제URL)
- **무슨 일이 있었나**:
- **왜 중요한가**:
- **놓치면 안 되는 것**:

---

## 📌 [테마 2 이름]

> **왜 지금인가?** 배경 설명 2~3문장.

### 🔗 [기사제목](실제URL)
- **무슨 일이 있었나**:
- **왜 중요한가**:
- **놓치면 안 되는 것**:

---

## 💡 실무 적용 팁

오늘 뉴스에서 독자가 이번 주 바로 써먹을 수 있는 것들:

1. **[팁 제목]**: 구체적 행동 방법 (도구명/방법론 포함)
2. **[팁 제목]**: 구체적 행동 방법
3. **[팁 제목]**: 구체적 행동 방법

---

## 🔮 앞으로 주목할 것

- **⚡ 이번 주**: 곧 일어날 구체적 사건이나 발표
- **📈 한 달 뒤**: 이 트렌드가 향하는 방향
- **🌱 조용한 신호**: 아직 주류는 아니지만 중요한 움직임

---

## 🔗 이번 뉴스레터 출처 링크

[아래 링크 모음을 그대로 붙여넣을 것]

---
*📡 NewsHub Agent | {today}*

━━━ 작성 원칙 ━━━
- 단순 요약 금지. 반드시 "왜 중요한지" "어떻게 써먹는지" 포함
- 구체적 수치·회사명·제품명·날짜 적극 사용
- 기술 용어는 한국어+영문 병기 (예: 대형언어모델 LLM)
- 표, 이모지, 굵은 글씨로 시각적 가독성 확보
- 길이 제한 없음 — 내용이 충분히 깊어야 함
- 전체 한국어 작성
"""

    user_message = f"""=== 수집된 기사 목록 (번호·제목·URL·요약) ===

{articles_text}

=== 링크 모음 (뉴스레터 마지막 섹션에 그대로 붙여넣을 것) ===

{link_index_text}
"""

    llm_error = None
    newsletter = None

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ])
        newsletter = response.content.strip()
    except Exception as e:
        llm_error = str(e)
        try:
            fallback_llm = get_llm(temperature=0.7)
            response = fallback_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ])
            newsletter = response.content.strip()
            llm_error = f"폴백 사용: {llm_error[:80]}"
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

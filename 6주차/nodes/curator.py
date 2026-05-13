"""
노드 4 — Curator (큐레이션 에이전트)

수집된 YouTube 영상 + 뉴스 기사를 분석하여:
- 관련도 점수(score) 매기기
- 상위 기사 선별
- 전체 트렌드 요약 작성
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from state import NewsHubState
from llm_factory import get_llm


def curator_node(state: NewsHubState) -> dict:
    """수집된 기사들을 분석하고 큐레이션한다."""

    youtube_articles = state.get("youtube_articles", [])
    news_articles = state.get("news_articles", [])
    topics = state.get("topics", ["AI"])

    # 모든 기사 합치기
    all_articles = youtube_articles + news_articles

    # 중복 제거 (제목 기반 단순 제거)
    seen_titles = set()
    unique_articles = []
    for art in all_articles:
        title = art.get("title", "").strip().lower()
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_articles.append(art)
    
    all_articles = unique_articles

    if not all_articles:
        return {
            "curated_articles": [],
            "trend_summary": "수집된 기사가 없습니다. 토픽이나 소스를 확인해주세요.",
            "error_messages": ["큐레이션할 기사가 0건"],
        }

    # LLM으로 큐레이션
    llm = get_llm(temperature=0.3)

    # 기사 목록을 텍스트로 변환
    articles_text = ""
    for i, article in enumerate(all_articles[:30], 1):  # 최대 30개만 분석
        articles_text += f"""
[기사 {i}]
제목: {article.get('title', '제목 없음')}
소스: {article.get('source', '알 수 없음')}
요약: {article.get('summary', '요약 없음')[:200]}
URL: {article.get('url', '')}
---
"""

    system_prompt = f"""당신은 AI/테크 전문 뉴스 큐레이터입니다.
아래 수집된 기사들을 분석하여 JSON으로 응답하세요.

관심 토픽: {', '.join(topics)}

응답 형식 (JSON만 반환, 주석 없이):
{{
    "selected_indices": [1, 3, 5],
    "scores": {{"1": 0.95, "3": 0.88, "5": 0.75}},
    "clusters": [
        {{"theme": "테마명", "indices": [1, 3], "theme_summary": "이 테마의 핵심 1줄"}},
        {{"theme": "테마명2", "indices": [5], "theme_summary": "이 테마의 핵심 1줄"}}
    ],
    "trend_summary": "전체 트렌드 요약 (5~7문장, 구체적 수치와 회사명 포함, 한국어)",
    "key_insight": "독자가 꼭 알아야 할 핵심 인사이트 1문장"
}}

선별 기준 (최대 12개):
1. 관심 토픽 관련도 (최우선)
2. 구체적 사실/수치/발표 포함 여부 (높은 점수)
3. 출처 다양성 (같은 소스 중복 제한)
4. 커뮤니티 반응 (HN 점수, Reddit 인기도 고려)
5. 최신성 (오래된 기사 낮은 점수)

클러스터링: 비슷한 주제의 기사를 같은 테마로 묶어주세요.
예: "모델 출시", "투자/M&A", "오픈소스 동향", "규제/정책", "실용 도구"
"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=articles_text),
        ])

        import json
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        # 선별된 기사 추출
        selected_indices = result.get("selected_indices", list(range(1, min(10, len(all_articles) + 1))))
        scores = result.get("scores", {})
        trend_summary = result.get("trend_summary", "트렌드 요약을 생성하지 못했습니다.")
        clusters = result.get("clusters", [])
        key_insight = result.get("key_insight", "")

        curated = []
        for idx in selected_indices:
            if 1 <= idx <= len(all_articles):
                article = all_articles[idx - 1].copy()
                article["score"] = scores.get(str(idx), scores.get(idx, 0.5))
                curated.append(article)

        curated.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {
            "curated_articles": curated,
            "article_clusters": clusters,
            "key_insight": key_insight,
            "trend_summary": trend_summary,
        }

    except Exception as e:
        # LLM 실패 시 전체 기사 그대로 반환
        for article in all_articles:
            article["score"] = 0.5

        return {
            "curated_articles": all_articles[:10],
            "trend_summary": f"LLM 큐레이션 실패, 전체 기사 반환. ({str(e)})",
            "error_messages": [f"큐레이션 LLM 실패: {str(e)}"],
        }

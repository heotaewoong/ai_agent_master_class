"""
노드 6 — Evaluator (뉴스레터 품질 평가)

생성된 뉴스레터의 품질을 평가하고:
- 중복된 표현이나 기사가 있는지 확인
- 핵심 인사이트가 포함되었는지 확인
- 구조가 지침을 따르는지 확인

품질이 낮으면 재작성(newsletter_writer)을 요청한다.
"""

from __future__ import annotations

import json
from langchain_core.messages import SystemMessage, HumanMessage

from state import NewsHubState
from llm_factory import get_llm


def evaluator_node(state: NewsHubState) -> dict:
    """뉴스레터 초안의 품질을 평가한다."""

    newsletter = state.get("newsletter_draft", "")
    topics = state.get("topics", ["AI"])
    
    if not newsletter or "# 뉴스레터를 생성할 기사가 없습니다" in newsletter:
        return {"evaluation_result": "pass"}

    llm = get_llm(temperature=0)

    system_prompt = f"""당신은 뉴스레터 품질 검수 전문가입니다.
제시된 뉴스레터 초안을 분석하여 품질을 평가하고 'pass' 또는 'fail' 판정을 내리세요.

평가 기준:
1. 중복성: 비슷한 문장이나 동일한 기사가 반복되는가? (가장 중요)
2. 주제 적합성: {', '.join(topics)} 주제와 관련이 있는가?
3. 구조: 제목, 요약, 핵심 브리핑, 테마별 분석 구조를 갖추었는가?
4. 가독성: 마크다운 형식이 깔끔하고 가독성이 좋은가?

응답 형식 (JSON만 반환):
{{
    "score": 0~100,
    "decision": "pass" | "fail",
    "reason": "판정 이유 (한국어)",
    "feedback": "fail일 경우 개선 제안 (한국어)"
}}

만약 중복된 기사나 문장이 발견되면 반드시 'fail' 판정을 내리세요.
"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=newsletter),
        ])

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)
        
        # 횟수 제한 (무한 루프 방지)를 위해 상태에 시도 횟수를 기록하면 좋지만,
        # 일단은 결과만 반환합니다.
        return {
            "evaluation_result": result.get("decision", "pass"),
            "evaluation_feedback": result.get("feedback", ""),
            "error_messages": [f"평가 결과: {result.get('decision')} ({result.get('reason')})"]
        }

    except Exception as e:
        return {
            "evaluation_result": "pass",
            "error_messages": [f"평가 노드 오류 (자동 통과): {str(e)}"]
        }


def route_after_evaluation(state: NewsHubState):
    """평가 결과에 따라 다음 단계를 결정한다."""
    result = state.get("evaluation_result", "pass")
    
    # 무한 루프 방지를 위해 일단 1회만 재시도하도록 하거나,
    # 여기서는 단순하게 결과에 따라 분기합니다.
    if result == "fail":
        return "newsletter_writer"
    return "delivery"

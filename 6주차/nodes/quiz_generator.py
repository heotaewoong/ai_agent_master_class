"""
Quiz Generator — 뉴스레터 학습 퀴즈 생성

생성된 뉴스레터 내용을 바탕으로 4지선다 학습 퀴즈를 만든다.
그래프 파이프라인에서 호출하거나 UI에서 독립적으로 호출할 수 있다.
"""

from __future__ import annotations

import json

from langchain_core.messages import SystemMessage, HumanMessage

from llm_factory import get_llm


def generate_quiz(newsletter_text: str, num_questions: int = 5) -> list[dict]:
    """
    뉴스레터 내용을 바탕으로 학습 퀴즈를 생성한다.

    Returns:
        list[dict] — 각 항목: {question, options, correct, explanation}
        실패 시 빈 리스트 반환.
    """
    if not newsletter_text or len(newsletter_text) < 100:
        return []

    llm = get_llm(temperature=0.5)

    system_prompt = f"""당신은 교육 콘텐츠 전문가입니다.
아래 뉴스레터를 읽고, 독자가 핵심 내용을 이해했는지 확인하는 4지선다 퀴즈 {num_questions}개를 만드세요.

퀴즈 작성 원칙:
- 뉴스레터의 핵심 사실, 수치, 트렌드를 묻는 문제 위주
- 단순 암기보다 이해도를 확인하는 문제
- 오답 선지는 그럴듯하게 (너무 쉽게 답이 보이면 안 됨)
- 한국어로 작성

반드시 아래 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {{
    "question": "질문 내용",
    "options": ["A. 선택지1", "B. 선택지2", "C. 선택지3", "D. 선택지4"],
    "correct": "A",
    "explanation": "정답 해설 (뉴스레터의 어느 부분이 근거인지 포함)"
  }}
]
"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"뉴스레터 내용:\n\n{newsletter_text[:4000]}"),
        ])

        content = response.content.strip()
        # 코드 블록 제거
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        questions = json.loads(content)
        if isinstance(questions, list):
            return questions
        return []

    except Exception:
        return []

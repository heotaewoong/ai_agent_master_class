
import anthropic
import requests
import json

BASE_URL = "https://nomad-movies.nomadcoders.workers.dev"

client = anthropic.Anthropic()

# ─── 도구 정의 ───────────────────────────────────────────────────────────────

tools = [
    {
        "name": "get_popular_movies",
        "description": "현재 인기 있는 영화 목록을 가져옵니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_movie_details",
        "description": "특정 영화의 상세 정보를 가져옵니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "영화의 고유 ID"
                }
            },
            "required": ["movie_id"]
        }
    },
    {
        "name": "get_similar_movies",
        "description": "특정 영화와 유사한 영화 목록을 가져옵니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "영화의 고유 ID"
                }
            },
            "required": ["movie_id"]
        }
    }
]

# ─── 실제 API 호출 함수들 ─────────────────────────────────────────────────────

def get_popular_movies():
    response = requests.get(f"{BASE_URL}/movies")
    return response.json()

def get_movie_details(movie_id: int):
    response = requests.get(f"{BASE_URL}/movies/{movie_id}")
    return response.json()

def get_similar_movies(movie_id: int):
    response = requests.get(f"{BASE_URL}/movies/{movie_id}/similar")
    return response.json()

def call_tool(tool_name: str, tool_input: dict):
    """도구 이름에 따라 실제 API를 호출합니다."""
    if tool_name == "get_popular_movies":
        return get_popular_movies()
    elif tool_name == "get_movie_details":
        return get_movie_details(tool_input["movie_id"])
    elif tool_name == "get_similar_movies":
        return get_similar_movies(tool_input["movie_id"])
    else:
        return {"error": f"알 수 없는 도구: {tool_name}"}

# ─── 에이전트 루프 ─────────────────────────────────────────────────────────────

def run_agent(conversation_history: list, user_message: str) -> str:
    """
    완전한 에이전트 루프:
    1. 사용자 메시지를 history에 추가
    2. Claude 호출
    3. tool_use면 → 실제 API 호출 → 결과를 history에 추가 → 다시 Claude 호출
    4. 최종 텍스트 응답 반환
    """
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system="당신은 영화 전문 AI 에이전트입니다. 도구를 사용해 사용자의 질문에 답하세요. 한국어로 답변하세요.",
            tools=tools,
            messages=conversation_history
        )

        # tool_use: 도구 호출이 필요한 경우
        if response.stop_reason == "tool_use":
            # assistant 응답 전체를 history에 추가
            conversation_history.append({
                "role": "assistant",
                "content": response.content
            })

            # 모든 tool_use 블록 처리
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n[도구 호출] {block.name}({block.input})")
                    result = call_tool(block.name, block.input)
                    print(f"[도구 결과] {json.dumps(result, ensure_ascii=False)[:200]}...")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })

            # 도구 결과를 history에 추가 후 다시 루프
            conversation_history.append({
                "role": "user",
                "content": tool_results
            })

        # end_turn: 최종 답변
        elif response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            # assistant 최종 응답을 history에 추가
            conversation_history.append({
                "role": "assistant",
                "content": final_text
            })

            return final_text

        else:
            return f"예상치 못한 stop_reason: {response.stop_reason}"

# ─── 메인 챗 루프 ──────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("🎬 Movie Agent")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 50)

    conversation_history = []  # 멀티턴 대화를 위한 히스토리

    while True:
        user_input = input("\nUser: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("종료합니다.")
            break

        answer = run_agent(conversation_history, user_input)
        print(f"\nAgent: {answer}")

if __name__ == "__main__":
    main()

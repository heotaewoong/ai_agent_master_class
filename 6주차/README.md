# NewsHub Agent - 5주차 과제

LangGraph를 기반으로 한 개인형 뉴스 큐레이션 에이전트입니다. 유튜브 구독 채널과 뉴스 RSS, 웹 검색을 결합하여 맞춤형 뉴스레터를 생성합니다.

## 주요 기능

1. **의도 분석 (Intake)**: 사용자 질문을 분석하여 유튜브 수집, 뉴스 검색, 또는 둘 다 수행할지 결정합니다.
2. **맞춤형 구독 관리**: `subscriptions.yaml`을 통해 선호하는 유튜브 채널과 뉴스 소스를 관리합니다.
3. **멀티 소스 수집**:
   - **YouTube**: 채널 RSS를 통해 최신 영상을 수집합니다.
   - **News RSS**: 구글 뉴스, 기술 블로그 등 RSS 피드를 파싱합니다.
   - **Web Search**: Tavily 및 DuckDuckGo를 활용한 보조 검색을 수행합니다.
4. **큐레이션 및 뉴스레터 생성**: 수집된 정보를 요약하고 마크다운 형식의 뉴스레터로 작성합니다.

## 프로젝트 구조

```text
5주차/
├── nodes/               # LangGraph 각 단계별 노드 정의
├── .env.example         # 환경 변수 설정 템플릿
├── graph.py             # LangGraph 그래프 정의 및 컴파일
├── llm_factory.py       # LLM 프로바이더 설정 (OpenAI, Groq, Gemini, Ollama)
├── main.py              # CLI 실행 진입점
├── pyproject.toml       # 의존성 및 프로젝트 메타데이터
├── state.py             # 에이전트 상태(State) 정의
├── subscriptions.yaml   # 구독 채널 및 소스 설정
└── tools.py             # 수집 및 검색 도구(Tools) 정의
```

## 시작하기

### 1. 환경 설정

`.env.example` 파일을 `.env`로 복사하고 필요한 API 키를 입력합니다.

```bash
cp .env.example .env
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
# 또는 pyproject.toml을 지원하는 도구(uv, poetry 등) 사용
```

### 3. 실행

```bash
# 대화형 모드 실행
python main.py

# 특정 주제로 바로 실행
python main.py "AI 최신 트렌드"

# 구독 목록 확인
python main.py --list-subs
```

## 아키텍처

이 에이전트는 LangGraph의 **Conditional Edges**와 **Send API**를 활용하여 의도에 따른 유연한 분기 및 병렬 수집을 구현했습니다.

# 📡 NewsHub Education Agent

> AI/테크 뉴스를 자동 수집·요약하고, 학습 퀴즈로 지식을 확인하는 **LangGraph 기반 교육형 뉴스 에이전트**

## 주요 기능

| 기능 | 설명 |
|------|------|
| 🧠 **의도 분석 (Intake)** | 사용자 질문을 분석해 YouTube 수집 / 뉴스 검색 / 혼합 중 자동 선택 |
| ⚡ **병렬 멀티 소스 수집** | YouTube RSS + 뉴스 RSS + 웹 검색을 LangGraph Send API로 동시 수집 |
| 📝 **AI 뉴스레터 생성** | 수집된 기사를 큐레이션해 마크다운 뉴스레터로 자동 작성 |
| ⚖️ **AI-as-Judge 품질 검수** | 뉴스레터 품질을 LLM이 자동 평가 — 미달 시 재작성(Harness) |
| 🎯 **학습 퀴즈 생성** | 뉴스레터 내용 기반 4지선다 퀴즈 자동 생성 및 채점 |

## 아키텍처

```
user_input
    │
[intake] → [subscription_loader]
                │
    ┌───────────┼────────────┐
    ↓           ↓            ↓
[youtube]  [both_collector] [news]   ← LangGraph Send API 병렬
    │       ↙         ↘      │
    └──[youtube] [news]──────┘
                │
           [curator]
                │
      [newsletter_writer]
                │
           [evaluator]  ← AI-as-Judge
                │
              END
```

## 기술 스택

- **LangGraph** — 멀티 노드 워크플로우, Conditional Edge, Send API 병렬 처리
- **LangChain** — LLM 추상화 (Groq / OpenAI / Gemini 지원)
- **Streamlit** — 채팅 UI, 퀴즈 인터페이스
- **feedparser** — YouTube RSS, 뉴스 RSS 파싱
- **DuckDuckGo / Tavily** — 웹 검색 (Tavily 없으면 DuckDuckGo 자동 사용)

## 로컬 실행

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. Streamlit 실행

```bash
streamlit run ui.py
```

또는 CLI로 실행:

```bash
python main.py "AI 최신 트렌드 알려줘"
```

## Streamlit Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) 접속
2. GitHub 저장소 연결
3. **Main file path**: `6주차/ui.py` 설정
4. **Secrets** 설정:

```toml
LLM_PROVIDER = "groq"
GROQ_API_KEY = "gsk-your-key"
# 웹 검색 강화 (선택)
# TAVILY_API_KEY = "tvly-your-key"
```

5. Deploy!

### 지원 LLM 프로바이더

| 프로바이더 | Secrets 키 | 무료 여부 |
|-----------|------------|---------|
| Groq | `GROQ_API_KEY` | ✅ 무료 (권장) |
| Gemini | `GOOGLE_API_KEY` | ✅ 무료 티어 |
| OpenAI | `OPENAI_API_KEY` | 💳 유료 |

## 프로젝트 구조

```
6주차/
├── ui.py                  # Streamlit 메인 앱 (진입점)
├── graph.py               # LangGraph 그래프 정의
├── state.py               # 공유 상태(State) 스키마
├── llm_factory.py         # LLM 프로바이더 통합
├── tools.py               # RSS/검색 도구
├── subscriptions.yaml     # 구독 채널·소스 설정
├── requirements.txt       # 의존성
├── nodes/
│   ├── intake.py          # 의도 분석
│   ├── subscription_loader.py
│   ├── both_collector.py  # Send API 병렬 팬아웃
│   ├── youtube_collector.py
│   ├── news_searcher.py
│   ├── curator.py         # 기사 선별·클러스터링
│   ├── newsletter_writer.py
│   ├── evaluator.py       # AI-as-Judge
│   └── quiz_generator.py  # 학습 퀴즈 생성
└── main.py                # CLI 실행 진입점
```

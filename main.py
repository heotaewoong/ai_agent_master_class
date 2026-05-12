"""
NewsHub Agent — 실행 진입점

사용법:
  python main.py                        # 대화형 모드 (인텐트 자동 분류)
  python main.py "AI 최신 트렌드"        # 인수로 바로 실행
  python main.py --list-subs            # 현재 구독 목록 출력
  python main.py --add-youtube          # YouTube 채널 추가 가이드
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

load_dotenv()

console = Console()


# ──────────────────────────────────────────────────────────
# 구독 목록 조회
# ──────────────────────────────────────────────────────────
def cmd_list_subscriptions() -> None:
    """subscriptions.yaml의 현재 구독 목록을 테이블로 출력한다."""
    try:
        import yaml
    except ImportError:
        console.print("[red]pyyaml 미설치: pip install pyyaml[/red]")
        return

    yaml_path = Path(__file__).parent / "subscriptions.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # YouTube 채널 테이블
    yt_table = Table(title="YouTube 채널", show_lines=True)
    yt_table.add_column("이름", style="cyan")
    yt_table.add_column("카테고리")
    yt_table.add_column("태그")
    yt_table.add_column("활성화", justify="center")

    for ch in config.get("youtube", []):
        enabled = "[green]✓[/green]" if ch.get("enabled") else "[red]✗[/red]"
        yt_table.add_row(
            ch.get("name", ""),
            ch.get("category", ""),
            ", ".join(ch.get("tags", [])),
            enabled,
        )

    console.print(yt_table)

    # RSS 피드 테이블
    rss_table = Table(title="웹사이트 / RSS 피드", show_lines=True)
    rss_table.add_column("이름", style="cyan")
    rss_table.add_column("카테고리")
    rss_table.add_column("태그")
    rss_table.add_column("활성화", justify="center")

    for site in config.get("websites", []):
        enabled = "[green]✓[/green]" if site.get("enabled") else "[red]✗[/red]"
        rss_table.add_row(
            site.get("name", ""),
            site.get("category", ""),
            ", ".join(site.get("tags", [])),
            enabled,
        )

    console.print(rss_table)
    console.print(
        f"\n[dim]편집: {yaml_path}[/dim]\n"
        "[dim]enabled: true/false 로 개별 소스를 켜고 끌 수 있습니다.[/dim]"
    )


# ──────────────────────────────────────────────────────────
# YouTube 채널 추가 가이드
# ──────────────────────────────────────────────────────────
def cmd_add_youtube() -> None:
    yaml_path = Path(__file__).parent / "subscriptions.yaml"
    console.print(Panel(
        "[bold cyan]YouTube 채널 추가 방법[/bold cyan]\n\n"
        "1. 유튜브 채널 페이지에서 채널 ID 확인:\n"
        "   브라우저에서 채널 URL 열기 → 페이지 소스(Ctrl+U) → 'channelId' 검색\n"
        "   또는: https://www.youtube.com/@channelname 접속 후 URL에서 ID 복사\n\n"
        "2. RSS로 미리 테스트:\n"
        "   https://www.youtube.com/feeds/videos.xml?channel_id=<YOUR_ID>\n\n"
        f"3. [bold]{yaml_path}[/bold] 파일의 youtube: 섹션 하단에 추가:\n\n"
        "  - name: \"채널 이름\"\n"
        "    channel_id: \"UCxxxxxxxxx\"\n"
        "    category: ai   # ai | tech | finance | korean | academic | startup\n"
        "    tags: [AI, 도구]\n"
        "    enabled: true",
        title="채널 추가 가이드",
        border_style="cyan",
    ))


# ──────────────────────────────────────────────────────────
# 에이전트 실행
# ──────────────────────────────────────────────────────────
def run_agent(user_input: str) -> None:
    """NewsHub 에이전트를 실행하고 결과를 출력한다."""

    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.[/red]")
        sys.exit(1)

    from graph import app

    console.print(Panel(
        f"[bold cyan]NewsHub Agent[/bold cyan] 시작\n"
        f"입력: [italic]{user_input}[/italic]",
        border_style="blue",
    ))

    initial_state = {"user_input": user_input}

    with console.status("[bold green]에이전트 실행 중...[/bold green]", spinner="dots"):
        try:
            result = app.invoke(initial_state)
        except Exception as e:
            console.print(f"[red]에이전트 실행 실패: {e}[/red]")
            raise

    # ── 결과 출력 ──────────────────────────────────────
    intent = result.get("intent", "?")
    topics = result.get("topics", [])
    active_feeds = result.get("active_rss_feeds", {})
    yt_articles = result.get("youtube_articles", [])
    news_articles = result.get("news_articles", [])
    curated = result.get("curated_articles", [])
    trend = result.get("trend_summary", "")
    newsletter = result.get("newsletter_draft", "")
    errors = result.get("error_messages", [])

    # 실행 요약
    summary = (
        f"인텐트: [bold]{intent}[/bold] | "
        f"토픽: {', '.join(topics)} | "
        f"활성 RSS: {len(active_feeds)}개 | "
        f"YouTube: {len(yt_articles)}건 | "
        f"뉴스: {len(news_articles)}건 | "
        f"큐레이션: [green]{len(curated)}건[/green]"
    )
    console.print(Panel(summary, title="실행 요약", border_style="green"))

    # 트렌드 요약
    if trend:
        console.print(Panel(trend, title="트렌드 요약", border_style="yellow"))

    # 에러 출력
    if errors:
        console.print("[dim yellow]경고/에러:[/dim yellow]")
        for err in errors:
            console.print(f"  [dim]• {err}[/dim]")

    # 뉴스레터 출력
    if newsletter:
        console.print("\n")
        console.print(Markdown(newsletter))

    # 저장 경로 안내
    output_dir = Path(__file__).parent / "output"
    if output_dir.exists():
        files = sorted(output_dir.glob("newsletter_*.md"), reverse=True)
        if files:
            console.print(f"\n[dim]저장됨: {files[0]}[/dim]")


# ──────────────────────────────────────────────────────────
# CLI 진입점
# ──────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="NewsHub Agent — LangGraph 기반 AI/테크 뉴스 큐레이터"
    )
    parser.add_argument("query", nargs="?", help="검색 쿼리 (없으면 대화형 입력)")
    parser.add_argument("--list-subs", action="store_true", help="구독 목록 출력")
    parser.add_argument("--add-youtube", action="store_true", help="YouTube 채널 추가 가이드")

    args = parser.parse_args()

    if args.list_subs:
        cmd_list_subscriptions()
        return

    if args.add_youtube:
        cmd_add_youtube()
        return

    query = args.query
    if not query:
        console.print("[bold cyan]NewsHub Agent[/bold cyan] — 무엇을 알고 싶으신가요?")
        console.print("[dim]예시: AI 최신 뉴스 / 유튜브 자동화 / LLM 트렌드 뉴스레터[/dim]")
        try:
            query = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]종료[/dim]")
            return

    if not query:
        query = "AI 최신 트렌드"

    run_agent(query)


if __name__ == "__main__":
    main()

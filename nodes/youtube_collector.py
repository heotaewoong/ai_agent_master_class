"""
노드 2 — YouTube Collector (유튜브 구독 수집)

등록된 YouTube 채널들의 RSS 피드에서 최신 영상을 수집한다.
★ youtube_rss_tool 사용 (Tool 연동)

태그 기반 필터링:
- state.topics와 매칭되는 태그를 가진 채널만 수집
- 태그 매칭이 없으면 전체 채널 수집
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from state import NewsHubState
import sys
import os
from pathlib import Path

# 루트 경로 추가
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.append(root)

from tools import youtube_rss_tool, youtube_transcript_tool, SAMPLE_YOUTUBE_CHANNELS
from llm_factory import get_llm


def youtube_collector_node(state: NewsHubState) -> dict:
    """YouTube 채널 RSS에서 최신 영상을 수집한다."""

    topics = state.get("topics", [])
    channels = state.get("youtube_channels") or SAMPLE_YOUTUBE_CHANNELS

    # 토픽 기반 태그 매칭 필터링
    if topics:
        topic_lower = [t.lower() for t in topics]
        matched_channels = []
        for ch in channels:
            ch_tags = [t.lower() for t in ch.get("tags", [])]
            # 태그가 토픽과 하나라도 겹치면 포함
            if any(tag in topic_lower or any(t in tag for t in topic_lower) for tag in ch_tags):
                matched_channels.append(ch)

        # 매칭된 채널이 없으면 전체 채널 사용
        if not matched_channels:
            matched_channels = channels
    else:
        matched_channels = channels

    all_videos = []
    errors = []

    for channel in matched_channels:
        channel_id = channel.get("channel_id", "")
        channel_name = channel.get("name", "")
        channel_tags = channel.get("tags", [])

        if not channel_id:
            continue

        try:
            # ★ Tool 호출 — youtube_rss_tool
            result = youtube_rss_tool.invoke({
                "channel_id": channel_id,
                "max_items": 3,
            })

            if isinstance(result, list):
                for item in result:
                    if "error" in item:
                        errors.append(f"[YouTube:{channel_name}] {item['error']}")
                        continue
                    # 채널 태그를 기사에 추가
                    item["tags"] = channel_tags
                    item["source"] = f"YouTube: {channel_name}"
                    all_videos.append(item)
        except Exception as e:
            errors.append(f"[YouTube:{channel_name}] 수집 실패: {str(e)}")

    # ── 자막 기반 요약 강화 (상위 3개 영상) ──
    enriched = _enrich_with_transcripts(all_videos[:3], topics, errors)
    all_videos[:3] = enriched

    return {
        "youtube_articles": all_videos,
        "error_messages": errors if errors else [],
    }


def _enrich_with_transcripts(videos: list, topics: list, errors: list) -> list:
    """상위 영상의 자막을 가져와 LLM으로 요약을 강화한다."""
    if not videos:
        return videos

    llm = get_llm(temperature=0.3)

    for video in videos:
        url = video.get("url", "")
        if not url:
            continue
        try:
            result = youtube_transcript_tool.invoke({"video_url": url, "max_chars": 3000})
            transcript = result.get("transcript", "")
            if not transcript or result.get("error"):
                continue

            response = llm.invoke([
                SystemMessage(content="유튜브 영상 자막을 3~5문장으로 핵심만 한국어로 요약하세요."),
                HumanMessage(content=f"제목: {video.get('title','')}\n\n자막:\n{transcript}"),
            ])
            video["summary"] = response.content.strip()[:600]
            video["has_transcript"] = True
        except Exception as e:
            errors.append(f"[transcript:{url[:50]}] {str(e)}")

    return videos

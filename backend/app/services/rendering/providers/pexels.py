"""Pexels Video API Provider for stock footage retrieval."""

from __future__ import annotations

import logging
import pathlib
import urllib.parse
import urllib.request
import json
from typing import Any

from app.config import settings
from app.services.rendering.providers.base import SceneSpec, VideoSourceProvider

log = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


class PexelsProvider(VideoSourceProvider):
    """Retrieves high-definition stock footage from Pexels Video API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else settings.pexels_api_key

    @property
    def name(self) -> str:
        return "pexels"

    def fetch_clip(self, scene: SceneSpec, cache_dir: pathlib.Path) -> pathlib.Path | None:
        if not self.api_key:
            log.info("Pexels API key not configured — skipping Pexels stock search.")
            return None

        query = scene.search_query.strip()
        if not query:
            log.warning("Empty search query for scene %d — skipping Pexels.", scene.scene_id)
            return None

        orientation = "portrait" if scene.orientation == "vertical" else "landscape"
        params = {
            "query": query,
            "per_page": 5,
            "orientation": orientation,
            "size": "medium",
        }
        url = f"{PEXELS_SEARCH_URL}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": self.api_key,
                "User-Agent": "ContentBridge/1.0",
            },
        )

        try:
            log.info("Searching Pexels Video API for scene %d: %r", scene.scene_id, query)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    log.warning("Pexels API returned status %d", resp.status)
                    return None
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))

            videos = data.get("videos", [])
            if not videos:
                log.info("No Pexels videos found for query: %r", query)
                return None

            # Pick top candidate video file with MP4 link
            selected_url = None
            for video in videos:
                video_files = video.get("video_files", [])
                # Filter for mp4 files
                mp4_files = [f for f in video_files if f.get("file_type") == "video/mp4" and f.get("link")]
                if not mp4_files:
                    continue
                # Prefer HD (720p/1080p)
                mp4_files.sort(key=lambda x: (x.get("width", 0) * x.get("height", 0)), reverse=True)
                selected_url = mp4_files[0]["link"]
                break

            if not selected_url:
                log.info("No suitable MP4 stream found in Pexels results for query: %r", query)
                return None

            # Download clip locally
            target_path = cache_dir / f"pexels_scene_{scene.scene_id:02d}.mp4"
            log.info("Downloading Pexels clip for scene %d -> %s", scene.scene_id, target_path)
            
            dl_req = urllib.request.Request(selected_url, headers={"User-Agent": "ContentBridge/1.0"})
            with urllib.request.urlopen(dl_req, timeout=30) as dl_resp:
                clip_bytes = dl_resp.read()
                target_path.write_bytes(clip_bytes)

            log.info("Successfully fetched Pexels video clip (%d bytes)", len(clip_bytes))
            return target_path

        except Exception as exc:
            log.warning("Pexels Video API request failed for scene %d: %s", scene.scene_id, exc)
            return None

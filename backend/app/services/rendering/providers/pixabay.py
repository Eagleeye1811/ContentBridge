"""Pixabay Video API Provider for stock footage retrieval."""

from __future__ import annotations

import json
import logging
import pathlib
import urllib.parse
import urllib.request
from typing import Any

from app.config import settings
from app.services.rendering.providers.base import SceneSpec, VideoSourceProvider

log = logging.getLogger(__name__)

PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"


class PixabayProvider(VideoSourceProvider):
    """Retrieves stock video footage from Pixabay Video API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else settings.pixabay_api_key

    @property
    def name(self) -> str:
        return "pixabay"

    def fetch_clip(self, scene: SceneSpec, cache_dir: pathlib.Path) -> pathlib.Path | None:
        if not self.api_key:
            log.info("Pixabay API key not configured — skipping Pixabay stock search.")
            return None

        query = scene.search_query.strip()
        if not query:
            log.warning("Empty search query for scene %d — skipping Pixabay.", scene.scene_id)
            return None

        params = {
            "key": self.api_key,
            "q": query,
            "video_type": "film",
            "per_page": 5,
        }
        url = f"{PIXABAY_SEARCH_URL}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ContentBridge/1.0"},
        )

        try:
            log.info("Searching Pixabay Video API for scene %d: %r", scene.scene_id, query)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    log.warning("Pixabay API returned status %d", resp.status)
                    return None
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))

            hits = data.get("hits", [])
            if not hits:
                log.info("No Pixabay video hits found for query: %r", query)
                return None

            selected_url = None
            for hit in hits:
                videos_dict = hit.get("videos", {})
                # Try medium, large, small in order
                for res_key in ["large", "medium", "small", "tiny"]:
                    vinfo = videos_dict.get(res_key, {})
                    vurl = vinfo.get("url")
                    if vurl and ".mp4" in vurl.lower():
                        selected_url = vurl
                        break
                if selected_url:
                    break

            if not selected_url:
                log.info("No MP4 video URL found in Pixabay hits for query: %r", query)
                return None

            target_path = cache_dir / f"pixabay_scene_{scene.scene_id:02d}.mp4"
            log.info("Downloading Pixabay clip for scene %d -> %s", scene.scene_id, target_path)

            dl_req = urllib.request.Request(selected_url, headers={"User-Agent": "ContentBridge/1.0"})
            with urllib.request.urlopen(dl_req, timeout=30) as dl_resp:
                clip_bytes = dl_resp.read()
                target_path.write_bytes(clip_bytes)

            log.info("Successfully fetched Pixabay video clip (%d bytes)", len(clip_bytes))
            return target_path

        except Exception as exc:
            log.warning("Pixabay Video API request failed for scene %d: %s", scene.scene_id, exc)
            return None

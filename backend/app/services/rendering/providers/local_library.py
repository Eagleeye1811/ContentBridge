"""Local Stock Video Asset Library Provider fallback."""

from __future__ import annotations

import hashlib
import logging
import pathlib
import shutil

from app.services.rendering.providers.base import SceneSpec, VideoSourceProvider

log = logging.getLogger(__name__)

MOTION_VIDEOS: dict[str, list[str]] = {
    "cyber": ["cyber_servers_motion.mp4", "digital_network_motion.mp4"],
    "tech": ["digital_network_motion.mp4", "tech_data_motion.mp4"],
    "city": ["smart_city_motion.mp4"],
    "strategy": ["tech_data_motion.mp4", "cyber_servers_motion.mp4"],
}


class LocalLibraryProvider(VideoSourceProvider):
    """Fallback provider serving local pre-packaged HD motion MP4 video assets."""

    @property
    def name(self) -> str:
        return "local_library"

    def fetch_clip(self, scene: SceneSpec, cache_dir: pathlib.Path) -> pathlib.Path | None:
        combined = f"{scene.title} {scene.visual_notes}".lower()
        category = "cyber"
        if any(k in combined for k in ["city", "india", "infrastruct"]):
            category = "city"
        elif any(k in combined for k in ["cyber", "security", "protect", "threat"]):
            category = "cyber"
        elif any(k in combined for k in ["tech", "ai", "network", "system"]):
            category = "tech"
        elif any(k in combined for k in ["strateg", "analys", "growth"]):
            category = "strategy"

        videos = MOTION_VIDEOS.get(category, MOTION_VIDEOS["cyber"])
        title_hash = int(hashlib.md5(scene.title.encode()).hexdigest(), 16)
        filename = videos[(scene.scene_id + title_hash) % len(videos)]

        assets_dir = pathlib.Path(__file__).parent.parent.parent.parent / "assets" / "videos"
        local_asset_path = assets_dir / filename

        if not local_asset_path.exists():
            log.warning("Local asset video file not found: %s", local_asset_path)
            return None

        target_path = cache_dir / f"local_scene_{scene.scene_id:02d}.mp4"
        shutil.copy(local_asset_path, target_path)
        log.info("Using local asset library video: %s -> %s", filename, target_path)
        return target_path

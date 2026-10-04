"""Base provider abstractions for ContentBridge hybrid video generation pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pathlib
from typing import Literal

Orientation = Literal["wide", "vertical"]


@dataclass
class SceneSpec:
    scene_id: int
    title: str
    narration: str
    visual_notes: str
    search_query: str
    duration: float
    orientation: Orientation = "wide"
    preferred_source: str = "stock"
    fallback_source: str = "ltx-video"
    extra_metadata: dict = field(default_factory=dict)


class VideoSourceProvider(ABC):
    """Abstract interface for video source providers (Pexels, Pixabay, LTX-Video, Local)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'pexels', 'pixabay', 'ltx_video', 'local_library')."""
        pass

    @abstractmethod
    def fetch_clip(self, scene: SceneSpec, cache_dir: pathlib.Path) -> pathlib.Path | None:
        """Search, download, or generate a video clip for the given scene.

        Args:
            scene: SceneSpec defining title, visual prompt, search query, etc.
            cache_dir: Local workspace directory to store downloaded/generated MP4 clips.

        Returns:
            pathlib.Path to downloaded/generated local MP4 file, or None if unavailable.
        """
        pass

"""Hybrid Video Pipeline and Scene Planner for ContentBridge Video Generation.

Implements the multi-tiered pipeline:
1. Primary: Stock Footage API (Pixabay Video API, optionally Pexels if configured)
2. Fallback: Local AI Generation (LTX-Video)
3. Offline/Local Assets: Pre-packaged HD video library
"""

from __future__ import annotations

import logging
import pathlib
import re
from typing import Any

from app.schemas.content_ir import Node
from app.services.rendering.providers.base import Orientation, SceneSpec, VideoSourceProvider
from app.services.rendering.providers.local_library import LocalLibraryProvider
from app.services.rendering.providers.ltx_video import LTXVideoProvider
from app.services.rendering.providers.pexels import PexelsProvider
from app.services.rendering.providers.pixabay import PixabayProvider

log = logging.getLogger(__name__)

# Stopwords to filter out when generating search queries from scene notes
_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "of", "from", "as", "is", "are", "was", "were", "be", "been",
    "show", "showing", "scene", "view", "clip", "shot", "video", "footage",
    "visual", "illustration", "screen", "display", "depicting", "featuring"
}


class ScenePlanner:
    """Extracts visual intent and generates targeted search queries for scene footage."""

    @classmethod
    def generate_search_query(cls, title: str, notes: str = "", narration: str = "") -> str:
        """Alias for extracting concise visual search query from scene notes."""
        return cls.extract_search_query(title, visual_notes=notes, narration=narration)

    @classmethod
    def extract_search_query(cls, title: str, visual_notes: str, narration: str = "") -> str:
        """Extract a concise 2-4 keyword visual search query for stock APIs."""
        raw_text = visual_notes if visual_notes.strip() else f"{title} {narration}"
        
        # Clean special chars
        cleaned = re.sub(r"[^\w\s]", " ", raw_text.lower())
        tokens = [t for t in cleaned.split() if t not in _STOPWORDS and len(t) > 2]
        
        # Domain keyword priorities
        domain_keywords = []
        cyber_keywords = ["cybersecurity", "security", "hacker", "network", "server", "data", "code", "firewall", "technology"]
        city_keywords = ["city", "skyline", "traffic", "infrastructure", "modern", "building", "urban"]
        business_keywords = ["business", "office", "strategy", "team", "meeting", "analytics", "dashboard"]
        
        for k in cyber_keywords + city_keywords + business_keywords:
            if k in tokens and k not in domain_keywords:
                domain_keywords.append(k)
        
        # Merge top domain keywords with other leading tokens
        query_tokens: list[str] = []
        for kw in domain_keywords:
            if kw not in query_tokens:
                query_tokens.append(kw)
            if len(query_tokens) >= 3:
                break
                
        for t in tokens:
            if t not in query_tokens:
                query_tokens.append(t)
            if len(query_tokens) >= 4:
                break
                
        if not query_tokens:
            query_tokens = ["technology", "digital"]
            
        return " ".join(query_tokens[:4])

    @classmethod
    def plan_scene(
        cls,
        node: Node,
        scene_id: int,
        duration: float,
        orientation: Orientation = "wide",
    ) -> SceneSpec:
        """Construct a SceneSpec with extracted search query and visual prompts."""
        title = (node.title or f"Scene {scene_id}").strip()
        narration = (node.text or "").strip()
        visual_notes = (node.notes or "").strip()
        
        search_query = cls.extract_search_query(title, visual_notes, narration)
        
        return SceneSpec(
            scene_id=scene_id,
            title=title,
            narration=narration,
            visual_notes=visual_notes,
            search_query=search_query,
            duration=duration,
            orientation=orientation,
            preferred_source="stock",
            fallback_source="ltx-video",
            extra_metadata={
                "items": node.items or [],
                "fact_ids": getattr(node, "fact_ids", []),
            },
        )


class HybridVideoPipeline:
    """Orchestrates resolution of scene video clips across multiple providers with fallbacks."""

    def __init__(self, providers: list[VideoSourceProvider] | None = None):
        if providers is not None:
            self.providers = providers
        else:
            # Default priority chain:
            # 1. Pixabay Video API (primary stock API)
            # 2. Pexels Video API (secondary stock API if key configured)
            # 3. LocalLibraryProvider (pre-packaged HD stock motion videos)
            # 4. LTX-Video (local AI generation fallback)
            self.providers = [
                PixabayProvider(),
                PexelsProvider(),
                LocalLibraryProvider(),
                LTXVideoProvider(),
            ]

    def resolve_scene_clip(
        self,
        scene: SceneSpec,
        cache_dir: pathlib.Path,
    ) -> tuple[pathlib.Path | None, str]:
        """Attempt to retrieve or generate video footage for the scene via provider fallback chain.

        Returns:
            Tuple of (clip_path, provider_name).
        """
        log.info(
            "HybridVideoPipeline: resolving scene %d (query: %r, duration: %.1fs)",
            scene.scene_id, scene.search_query, scene.duration,
        )

        for provider in self.providers:
            try:
                clip_path = provider.fetch_clip(scene, cache_dir)
                if clip_path and clip_path.exists() and clip_path.stat().st_size > 0:
                    log.info(
                        "Scene %d successfully resolved using provider [%s] -> %s",
                        scene.scene_id, provider.name, clip_path.name,
                    )
                    return clip_path, provider.name
            except Exception as exc:
                log.warning(
                    "Provider [%s] failed for scene %d: %s. Continuing to fallback...",
                    provider.name, scene.scene_id, exc,
                )

        log.warning("All video providers exhausted for scene %d — using static graphic fallback.", scene.scene_id)
        return None, "fallback_visual"

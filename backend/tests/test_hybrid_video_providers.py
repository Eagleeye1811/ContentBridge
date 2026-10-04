"""Tests for Hybrid Video Generation Pipeline & Providers."""

from __future__ import annotations

import pathlib
import tempfile
import pytest

from app.schemas.content_ir import Node
from app.services.rendering.providers.base import SceneSpec
from app.services.rendering.providers.hybrid_pipeline import HybridVideoPipeline, ScenePlanner
from app.services.rendering.providers.local_library import LocalLibraryProvider
from app.services.rendering.providers.ltx_video import LTXVideoProvider
from app.services.rendering.providers.pexels import PexelsProvider
from app.services.rendering.providers.pixabay import PixabayProvider


def test_scene_planner_query_generation():
    query1 = ScenePlanner.generate_search_query(
        title="Protecting Critical Infrastructure",
        notes="Show a cybersecurity analyst monitoring suspicious network activity in a SOC center",
    )
    assert "cybersecurity" in query1 or "security" in query1

    query2 = ScenePlanner.generate_search_query(
        title="Smart City Traffic Optimization",
        notes="Smart traffic signals and automated urban transport network",
    )
    assert "city" in query2 or "infrastructure" in query2 or "traffic" in query2


def test_scene_planner_plan_scene():
    node = Node(
        id="n1",
        kind="scene",
        title="Cyber Defense Operations",
        text="Analysts monitor network traffic in real time.",
        notes="Multiple computer screens displaying network data in SOC center",
    )
    spec = ScenePlanner.plan_scene(node, scene_id=1, duration=5.0, orientation="wide")
    assert spec.scene_id == 1
    assert spec.duration == 5.0
    assert spec.preferred_source == "stock"
    assert spec.fallback_source == "ltx-video"
    assert len(spec.search_query) > 0


def test_pexels_provider_no_key():
    provider = PexelsProvider(api_key="")
    spec = SceneSpec(
        scene_id=1,
        title="Test",
        narration="",
        visual_notes="",
        search_query="cybersecurity",
        duration=3.0,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        res = provider.fetch_clip(spec, pathlib.Path(tmpdir))
        assert res is None


def test_pixabay_provider_no_key():
    provider = PixabayProvider(api_key="")
    spec = SceneSpec(
        scene_id=1,
        title="Test",
        narration="",
        visual_notes="",
        search_query="technology",
        duration=3.0,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        res = provider.fetch_clip(spec, pathlib.Path(tmpdir))
        assert res is None


def test_local_library_provider():
    provider = LocalLibraryProvider()
    spec = SceneSpec(
        scene_id=1,
        title="Cyber Defense",
        narration="Narration text",
        visual_notes="Cyber servers",
        search_query="cyber security",
        duration=4.0,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        clip_path = provider.fetch_clip(spec, pathlib.Path(tmpdir))
        assert clip_path is not None
        assert clip_path.exists()
        assert clip_path.suffix == ".mp4"


def test_hybrid_pipeline_fallback_chain():
    pipeline = HybridVideoPipeline()
    spec = SceneSpec(
        scene_id=1,
        title="Cybersecurity Operations",
        narration="Analysts inspect network anomalies.",
        visual_notes="Security operations center",
        search_query="cybersecurity analyst",
        duration=3.0,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        clip_path, provider_name = pipeline.resolve_scene_clip(spec, pathlib.Path(tmpdir))
        assert clip_path is not None
        assert clip_path.exists()
        assert provider_name in ["pexels", "pixabay", "ltx_video", "local_library"]

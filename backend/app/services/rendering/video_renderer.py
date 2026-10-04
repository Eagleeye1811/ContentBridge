"""ContentIR → MP4 video renderer (Tier-1 CPU pipeline).

Uses MoviePy 2.x API (moviepy >= 2.0).  The 2.x release removed `moviepy.editor`
and renamed mutating methods to immutable `with_*` counterparts.

Pipeline per scene
------------------
1. Synthesise voice-over MP3 via edge-tts  (Microsoft Neural TTS, free).
2. Render a dark-themed background card    (Pillow, CPU-only).
3. Apply Ken Burns slow-zoom effect        (MoviePy ImageClip + resized lambda).
4. Attach narration audio; clip duration = exact audio duration.

Final assembly
--------------
5. Concatenate all scene clips with short padding gaps.
6. Opening title card prepended.
7. Encode H.264 / AAC → return raw MP4 bytes.

All work is CPU-only. No GPU or neural inference required.
"""

from __future__ import annotations

import functools
import logging
import pathlib
import tempfile
from typing import Literal

import numpy as np

from app.schemas.content_ir import ContentIR, Node
from app.services.rendering.scene_visual import Orientation, render_scene_image
from app.services.rendering.srt import MIN_CUE_SECONDS, WORDS_PER_SECOND
from app.services.rendering.tts import synthesize_sync

log = logging.getLogger(__name__)

# ── tunables ───────────────────────────────────────────────────────────────────

RESOLUTION: dict[str, tuple[int, int]] = {
    "wide": (1280, 720),
    "vertical": (720, 1280),
}
FPS = 24
SCENE_GAP = 0.3          # silent gap between scenes (seconds)
TITLE_CARD_SECONDS = 2.5
KEN_BURNS_ZOOM = 0.08    # 8 % zoom over the clip duration


# ── helpers ────────────────────────────────────────────────────────────────────

def _scene_nodes(ir: ContentIR) -> list[Node]:
    return [n for n in ir.nodes if n.kind == "scene" and (n.text or "").strip()]


def _pil_to_array(pil_img) -> np.ndarray:
    return np.array(pil_img.convert("RGB"))


def _load_font_fallback(size: int):
    from PIL import ImageFont
    for name in [
        "arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
        "FreeSans.ttf", "LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_title_card(title: str, duration: float, size: tuple[int, int]) -> np.ndarray:
    """Return a PIL Image for the opening title card."""
    from PIL import Image, ImageDraw

    width, height = size
    img = Image.new("RGB", (width, height), "#0a0a0a")
    draw = ImageDraw.Draw(img)

    # Gradient accent bar across the middle
    for i in range(width):
        ratio = i / width
        r = int(30 + 60 * ratio)
        g = int(60 + 80 * ratio)
        b = int(180 + 60 * ratio)
        draw.line([(i, height // 2 - 2), (i, height // 2 + 2)], fill=(r, g, b))

    # Title
    font = _load_font_fallback(42)
    bbox = font.getbbox(title)
    tx = (width - bbox[2]) // 2
    ty = height // 2 - bbox[3] - 20
    draw.text((tx + 2, ty + 2), title, font=font, fill=(0, 0, 0, 160))
    draw.text((tx, ty), title, font=font, fill=(255, 255, 255))

    # Subtitle
    sub_font = _load_font_fallback(20)
    sub = "Content Bridge • Verified Output"
    sbbox = sub_font.getbbox(sub)
    sx = (width - sbbox[2]) // 2
    draw.text((sx, height // 2 + 20), sub, font=sub_font, fill=(160, 160, 160))

    return _pil_to_array(img)


def _make_silent_audio(duration: float, fps: int = 44100):
    """Return a 2-channel silent PCM audio array clip of exact duration."""
    from moviepy import AudioArrayClip
    samples = int(duration * fps)
    arr = np.zeros((samples, 2), dtype=np.float32)
    return AudioArrayClip(arr, fps=fps)


# ── main renderer ──────────────────────────────────────────────────────────────

def render(ir: ContentIR, orientation: str = "wide", language: str = "en", **_: object) -> bytes:
    """Render *ir* as an MP4 video and return the raw bytes.

    This function is **blocking and CPU-intensive**.  Always call it inside
    ``anyio.to_thread.run_sync`` to keep the async event loop free.

    Args:
        ir:          The storyboard ContentIR (nodes of kind "scene").
        orientation: "wide" (1280×720) or "vertical" (720×1280).
        language:    BCP-47 language code forwarded to the TTS engine.

    Returns:
        MP4 bytes encoded as H.264/AAC.
    """
    # MoviePy 2.x: import directly from `moviepy`, not `moviepy.editor`
    try:
        from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip, concatenate_videoclips
    except ImportError as exc:
        raise RuntimeError(
            "moviepy >= 2.0 is not installed. Run: pip install 'moviepy>=2.0'"
        ) from exc

    from app.services.rendering.motion_video import render_lower_third_overlay
    from app.services.rendering.providers import HybridVideoPipeline, ScenePlanner

    orient: Orientation = "vertical" if orientation == "vertical" else "wide"
    size = RESOLUTION[orient]
    scenes = _scene_nodes(ir)

    if not scenes:
        raise ValueError("No scene nodes found in ContentIR — cannot render video.")

    log.info(
        "video_renderer: rendering %d scenes at %s, lang=%s", len(scenes), size, language
    )

    hybrid_pipeline = HybridVideoPipeline()
    scene_clips = []

    with tempfile.TemporaryDirectory(prefix="cb_video_", ignore_cleanup_errors=True) as tmpdir:
        tmp = pathlib.Path(tmpdir)
        allocated_clips = []

        try:
            for idx, node in enumerate(scenes):
                narration = (node.text or "").strip()
                title = (node.title or f"Scene {idx + 1}").strip()
                items = [i for i in (node.items or []) if i.strip()] or None
                visual_notes = (node.notes or "").strip()

                # ── Step 1: TTS voice-over ────────────────────────────────────────
                audio_path = tmp / f"scene_{idx:02d}.mp3"
                audio_clip = None
                clip_duration: float

                try:
                    mp3_bytes = synthesize_sync(narration, language=language)
                    audio_path.write_bytes(mp3_bytes)
                    audio_clip = AudioFileClip(str(audio_path))
                    allocated_clips.append(audio_clip)
                    clip_duration = audio_clip.duration
                except Exception as tts_exc:
                    log.warning(
                        "TTS failed for scene %d (%s); estimating duration", idx, tts_exc
                    )
                    clip_duration = max(
                        MIN_CUE_SECONDS, len(narration.split()) / WORDS_PER_SECOND
                    )

                clip_duration = max(clip_duration, MIN_CUE_SECONDS)

                # ── Step 2: Hybrid Provider Video Clip Retrieval (Pexels -> Pixabay -> LTX-Video -> Local)
                scene_spec = ScenePlanner.plan_scene(
                    node=node,
                    scene_id=idx + 1,
                    duration=clip_duration,
                    orientation=orient,
                )

                try:
                    motion_path, provider_name = hybrid_pipeline.resolve_scene_clip(scene_spec, tmp)
                except Exception as pipe_err:
                    log.warning("Hybrid video pipeline failed for scene %d: %s", idx + 1, pipe_err)
                    motion_path, provider_name = None, "fallback_visual"

                overlay_arr = render_lower_third_overlay(
                    title=title,
                    visual_notes=visual_notes,
                    items=items,
                    index=idx,
                    total=len(scenes),
                    orientation=orient,
                )
                overlay_clip = ImageClip(overlay_arr).with_duration(clip_duration)
                allocated_clips.append(overlay_clip)

                if motion_path and motion_path.exists():
                    try:
                        vclip = VideoFileClip(str(motion_path)).without_audio().resized(size)
                        allocated_clips.append(vclip)
                        # Loop clip if duration is shorter than audio narration, or trim if longer
                        if vclip.duration < clip_duration:
                            repeats = int(np.ceil(clip_duration / vclip.duration))
                            looped = concatenate_videoclips([vclip] * repeats).subclipped(0, clip_duration)
                            allocated_clips.append(looped)
                            vclip_ready = looped
                        else:
                            vclip_ready = vclip.subclipped(0, clip_duration)
                            allocated_clips.append(vclip_ready)
                        video_clip = CompositeVideoClip([vclip_ready, overlay_clip])
                        allocated_clips.append(video_clip)
                    except Exception as vid_err:
                        log.warning("Failed to process motion video %s: %s", motion_path, vid_err)
                        pil_img = render_scene_image(title, visual_notes, items, idx, len(scenes), orient)
                        base_clip = ImageClip(_pil_to_array(pil_img)).with_duration(clip_duration)
                        allocated_clips.append(base_clip)
                        video_clip = base_clip
                else:
                    pil_img = render_scene_image(title, visual_notes, items, idx, len(scenes), orient)
                    base_clip = ImageClip(_pil_to_array(pil_img)).with_duration(clip_duration)
                    allocated_clips.append(base_clip)
                    video_clip = base_clip

                # ── Step 4: attach audio (or silent track if TTS omitted) ─────────
                if audio_clip is not None:
                    video_clip = video_clip.with_audio(audio_clip)
                else:
                    silent = _make_silent_audio(clip_duration)
                    allocated_clips.append(silent)
                    video_clip = video_clip.with_audio(silent)

                scene_clips.append(video_clip)
                log.debug(
                    "  scene %d/%d: dur=%.1fs title=%r",
                    idx + 1, len(scenes), clip_duration, title,
                )

            # ── Step 5: opening title card (with synchronized silent audio) ───────
            title_arr = _make_title_card(ir.title, TITLE_CARD_SECONDS, size)
            title_card = ImageClip(title_arr).with_duration(TITLE_CARD_SECONDS)
            silent_title = _make_silent_audio(TITLE_CARD_SECONDS)
            allocated_clips.extend([title_card, silent_title])
            title_card = title_card.with_audio(silent_title)

            all_clips = [title_card] + scene_clips

            # ── Step 6: concatenate ───────────────────────────────────────────────
            final = concatenate_videoclips(all_clips, method="compose")
            allocated_clips.append(final)

            # ── Step 7: encode MP4 ────────────────────────────────────────────────
            out_path = tmp / "output.mp4"
            temp_audio = tmp / "temp-audio.m4a"
            final.write_videofile(
                str(out_path),
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=str(temp_audio),
                preset="ultrafast",
                ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                logger=None,
            )

            mp4_bytes = out_path.read_bytes()
        finally:
            for c in allocated_clips:
                try:
                    c.close()
                except Exception:
                    pass

    log.info(
        "video_renderer: MP4 ready — %d bytes (%.1f MB)",
        len(mp4_bytes), len(mp4_bytes) / 1e6,
    )
    return mp4_bytes

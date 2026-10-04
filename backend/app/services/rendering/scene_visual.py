"""Scene visual generator — produces cinematic, content-aware visual graphics for video scenes.

Strategy:
  1. Load high-resolution, real-world topic photographic background images matching scene prompt.
  2. Apply a dark cinematic color grade, vignette, and lower-third gradient.
  3. Overlay subtle futuristic perspective grid & glowing network graph node accents.
  4. Render broadcast video lower-third typography (topic pill, scene counter, title, key takeaway pills).
"""

from __future__ import annotations

import hashlib
import io
import math
import pathlib
import random
import requests
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

Orientation = Literal["wide", "vertical"]

WIDE = (1280, 720)
VERTICAL = (720, 1280)

# Curated high-budget color palettes (bg_top, bg_middle, bg_bottom, accent, glow)
THEMES: list[dict[str, str]] = [
    {
        "top": "#0b0f19",
        "mid": "#111827",
        "bot": "#1e1b4b",
        "accent": "#6366f1",
        "glow": "#818cf8",
        "label": "CYBER & INFRASTRUCTURE",
    },
    {
        "top": "#020617",
        "mid": "#0f172a",
        "bot": "#0284c7",
        "accent": "#38bdf8",
        "glow": "#7dd3fc",
        "label": "TECHNOLOGY & NETWORK",
    },
    {
        "top": "#090514",
        "mid": "#1e0e4b",
        "bot": "#581c87",
        "accent": "#c084fc",
        "glow": "#e879f9",
        "label": "INNOVATION & FUTURE",
    },
    {
        "top": "#061314",
        "mid": "#082f49",
        "bot": "#134e4a",
        "accent": "#2dd4bf",
        "glow": "#5eead4",
        "label": "STRATEGY & DATA",
    },
    {
        "top": "#18080a",
        "mid": "#2c0b0e",
        "bot": "#450a0a",
        "accent": "#f87171",
        "glow": "#fca5a5",
        "label": "SECURITY & PROTECTION",
    },
]

# Real-world photographic stock assets stored locally
LOCAL_TOPIC_PHOTOS: dict[str, list[str]] = {
    "cyber": ["cyber_server_room.jpg", "cyber_security_center.jpg", "matrix_data_code.jpg"],
    "tech": ["digital_network_globe.jpg", "ai_chip_circuit.jpg", "tech_team_workspace.jpg"],
    "city": ["smart_city_skyline.jpg", "modern_skyscrapers.jpg"],
    "strategy": ["business_strategy_dashboard.jpg", "high_tech_office.jpg"],
}

_IMAGE_CACHE: dict[str, Image.Image] = {}

_FONT_CANDIDATES = [
    "arial.ttf",
    "Arial.ttf",
    "DejaVuSans.ttf",
    "FreeSans.ttf",
    "LiberationSans-Regular.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _theme_for(title: str, text: str = "") -> dict[str, str]:
    """Pick a theme based on content domain keywords or fallback to title hash."""
    combined = f"{title} {text}".lower()
    if any(k in combined for k in ["cyber", "security", "protect", "threat", "attack", "shield", "defense"]):
        return THEMES[0]
    if any(k in combined for k in ["tech", "network", "system", "digital", "ai", "cloud", "data"]):
        return THEMES[1]
    if any(k in combined for k in ["innovat", "future", "modern", "smart", "ai"]):
        return THEMES[2]
    if any(k in combined for k in ["strateg", "analys", "growth", "policy", "india"]):
        return THEMES[3]
    if any(k in combined for k in ["risk", "alert", "critical", "resilien"]):
        return THEMES[4]

    idx = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(THEMES)
    return THEMES[idx]


def _fetch_topic_image(title: str, text: str = "", index: int = 0, size: tuple[int, int] = WIDE) -> Image.Image | None:
    """Fetch high-res topic photographic background image matching scene prompt."""
    combined = f"{title} {text}".lower()
    category = "cyber"
    if any(k in combined for k in ["city", "india", "infrastruct", "build"]):
        category = "city"
    elif any(k in combined for k in ["cyber", "security", "protect", "threat", "shield"]):
        category = "cyber"
    elif any(k in combined for k in ["tech", "ai", "network", "system", "data"]):
        category = "tech"
    elif any(k in combined for k in ["strateg", "analys", "growth", "practice", "approach"]):
        category = "strategy"

    photos = LOCAL_TOPIC_PHOTOS.get(category, LOCAL_TOPIC_PHOTOS["cyber"])
    # Pick photo deterministically based on title hash + scene index so each scene is unique
    title_hash = int(hashlib.md5(title.encode()).hexdigest(), 16)
    filename = photos[(index + title_hash) % len(photos)]

    # 1. Try local assets folder
    assets_dir = pathlib.Path(__file__).parent.parent.parent / "assets" / "photos"
    local_path = assets_dir / filename
    if local_path.exists():
        try:
            return Image.open(local_path).convert("RGB").resize(size)
        except Exception:
            pass

    return None


def _draw_perspective_grid(draw: ImageDraw.ImageDraw, width: int, height: int, accent: tuple[int, int, int]) -> None:
    """Draw a subtle futuristic 3D perspective horizon grid."""
    r, g, b = accent
    vanish_x, vanish_y = width // 2, int(height * 0.45)

    for x in range(-width // 2, width * 3 // 2, width // 10):
        draw.line([(vanish_x, vanish_y), (x, height)], fill=(r, g, b, 20), width=1)

    y = vanish_y + 10
    step = 5
    while y < height:
        draw.line([(0, y), (width, y)], fill=(r, g, b, int(10 + 25 * (y - vanish_y) / (height - vanish_y))), width=1)
        y += step
        step = int(step * 1.25)


def _draw_network_nodes(draw: ImageDraw.ImageDraw, width: int, height: int, accent: tuple[int, int, int], seed: int = 42) -> None:
    """Draw connected glowing network graph nodes."""
    rng = random.Random(seed)
    r, g, b = accent
    nodes: list[tuple[int, int]] = []

    for _ in range(12):
        nx = rng.randint(int(width * 0.05), int(width * 0.95))
        ny = rng.randint(int(height * 0.1), int(height * 0.85))
        nodes.append((nx, ny))

    for i, (x1, y1) in enumerate(nodes):
        for j, (x2, y2) in enumerate(nodes[i + 1 :]):
            dist = math.hypot(x2 - x1, y2 - y1)
            if dist < width * 0.25:
                alpha = int(35 * (1 - dist / (width * 0.25)))
                draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, alpha), width=1)

    for nx, ny in nodes:
        nr = rng.randint(3, 6)
        draw.ellipse([(nx - nr * 2, ny - nr * 2), (nx + nr * 2, ny + nr * 2)], fill=(r, g, b, 25))
        draw.ellipse([(nx - nr, ny - nr), (nx + nr, ny + nr)], fill=(r, g, b, 150))


def render_scene_image(
    title: str,
    visual_notes: str = "",
    items: list[str] | None = None,
    index: int = 0,
    total: int = 1,
    orientation: Orientation = "wide",
) -> Image.Image:
    """Render a high-budget, cinematic real-world topic video graphic for a scene.

    Args:
        title:        Scene title.
        visual_notes: Content visual description.
        items:        On-screen text overlays/key takeaways.
        index:        0-based scene index.
        total:        Total scene count.
        orientation:  "wide" (1280x720) or "vertical" (720x1280).
    """
    width, height = WIDE if orientation == "wide" else VERTICAL
    theme = _theme_for(title, visual_notes)
    accent_rgb = _hex(theme["accent"])
    glow_rgb = _hex(theme["glow"])

    # ── Step 1: Load Real-World Photographic Background ────────────────────────
    topic_bg = _fetch_topic_image(title, visual_notes, index=index, size=(width, height))

    if topic_bg:
        img = topic_bg.convert("RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        # Apply dark cinematic color grade overlay
        draw.rectangle([(0, 0), (width, height)], fill=(8, 14, 28, 100))

        # Bottom broadcast lower-third gradient panel
        grad_top = int(height * 0.5)
        for y in range(grad_top, height):
            alpha = int(240 * ((y - grad_top) / (height - grad_top)) ** 1.3)
            draw.line([(0, y), (width, y)], fill=(4, 8, 18, alpha))
    else:
        img = Image.new("RGBA", (width, height), (11, 15, 25, 255))
        draw = ImageDraw.Draw(img, "RGBA")

    # ── Step 2: Overlay Tech Perspective Grid & Network Nodes ────────────────
    _draw_perspective_grid(draw, width, height, accent_rgb)
    _draw_network_nodes(draw, width, height, glow_rgb, seed=index + 100)

    # ── Step 3: Top Right Scene Counter Badge ────────────────────────────────
    counter_font = _load_font(14)
    counter_txt = f"SCENE {index + 1:02d} / {total:02d}"
    draw.rounded_rectangle(
        [(width - 160, 24), (width - 24, 52)],
        radius=6,
        fill=(0, 0, 0, 190),
        outline=(glow_rgb[0], glow_rgb[1], glow_rgb[2], 180),
        width=1,
    )
    draw.text((width - 146, 30), counter_txt, font=counter_font, fill=(255, 255, 255, 240))

    # ── Step 4: Broadcast Lower-Third Layout ─────────────────────────────────
    lower_y = int(height * 0.54)
    badge_font = _load_font(13)

    # Domain Category Pill
    pill_txt = f"  {theme['label']}  "
    draw.rounded_rectangle(
        [(40, lower_y), (310, lower_y + 26)],
        radius=6,
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 230),
    )
    draw.text((48, lower_y + 5), pill_txt, font=badge_font, fill=(255, 255, 255, 255))

    # Main Scene Title Typography
    title_font_size = 44 if orientation == "wide" else 36
    title_font = _load_font(title_font_size)
    words = title.split()

    lines: list[str] = []
    curr = ""
    max_w = width - 100
    for w in words:
        test = f"{curr} {w}".strip()
        bbox = title_font.getbbox(test)
        if bbox[2] > max_w and curr:
            lines.append(curr)
            curr = w
        else:
            curr = test
    if curr:
        lines.append(curr)

    line_h = title_font_size + 8
    text_y = lower_y + 38

    for idx_line, line in enumerate(lines[:2]):
        # Drop shadow
        draw.text((42, text_y + idx_line * line_h + 2), line, font=title_font, fill=(0, 0, 0, 240))
        # High-contrast white text
        draw.text((40, text_y + idx_line * line_h), line, font=title_font, fill=(255, 255, 255, 255))

    # Key Takeaways Pill
    bullet_items = items if items else [title]
    bullet_font = _load_font(18)
    bullet_y = text_y + len(lines[:2]) * line_h + 12

    for item in bullet_items[:2]:
        item_txt = f"  ▸  {item}  "
        bbox = bullet_font.getbbox(item_txt)
        w_pill = min(bbox[2] + 24, max_w)

        draw.rounded_rectangle(
            [(40, bullet_y), (40 + w_pill, bullet_y + 30)],
            radius=6,
            fill=(0, 0, 0, 200),
            outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 140),
            width=1,
        )
        draw.text((48, bullet_y + 5), item_txt, font=bullet_font, fill=(230, 240, 255, 240))
        bullet_y += 38

    # ── Step 5: Vignette ───────────────────────────────────────────────────────
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    steps = 20
    half_w, half_h = width // 2, height // 2
    for step in range(steps):
        alpha = int(60 * (step / steps) ** 2)
        inset = step * min(half_w, half_h) // steps
        x0, y0 = inset, inset
        x1, y1 = width - inset - 1, height - inset - 1
        if x1 > x0 and y1 > y0:
            v_draw.rectangle([(x0, y0), (x1, y1)], outline=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, vignette).convert("RGB")
    return img

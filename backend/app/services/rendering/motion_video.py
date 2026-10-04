"""HD Motion Video Service — composites dynamic moving video footage for each scene."""

from __future__ import annotations

import hashlib
import pathlib
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Orientation = Literal["wide", "vertical"]

WIDE = (1280, 720)
VERTICAL = (720, 1280)

MOTION_VIDEOS: dict[str, list[str]] = {
    "cyber": ["cyber_servers_motion.mp4", "digital_network_motion.mp4"],
    "tech": ["digital_network_motion.mp4", "tech_data_motion.mp4"],
    "city": ["smart_city_motion.mp4"],
    "strategy": ["tech_data_motion.mp4", "cyber_servers_motion.mp4"],
}

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


def _theme_label(title: str, text: str = "") -> str:
    combined = f"{title} {text}".lower()
    if any(k in combined for k in ["cyber", "security", "protect", "threat"]):
        return "CYBER & INFRASTRUCTURE"
    if any(k in combined for k in ["tech", "network", "system", "digital", "ai"]):
        return "TECHNOLOGY & NETWORK"
    if any(k in combined for k in ["city", "india", "infrastruct"]):
        return "SMART CITY & INFRASTRUCTURE"
    return "STRATEGY & INNOVATION"


def render_lower_third_overlay(
    title: str,
    visual_notes: str = "",
    items: list[str] | None = None,
    index: int = 0,
    total: int = 1,
    orientation: Orientation = "wide",
) -> np.ndarray:
    """Render a transparent broadcast lower-third PNG overlay as a NumPy array for MoviePy."""
    width, height = WIDE if orientation == "wide" else VERTICAL
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Transparent overlay - NO darkening on upper 80% of video
    grad_top = int(height * 0.80)
    for y in range(grad_top, height):
        alpha = int(180 * ((y - grad_top) / (height - grad_top)) ** 1.3)
        draw.line([(0, y), (width, y)], fill=(2, 4, 10, alpha))

    # Lower-Third Category Pill & Title at the bottom 20%
    label = _theme_label(title, visual_notes)
    lower_y = int(height * 0.82)
    badge_font = _load_font(11)

    # Domain category pill
    draw.rounded_rectangle(
        [(36, lower_y), (270, lower_y + 20)],
        radius=4,
        fill=(99, 102, 241, 235),
    )
    draw.text((44, lower_y + 3), f"  {label}  ", font=badge_font, fill=(255, 255, 255, 255))

    # Main Scene Title Typography
    title_font_size = 30 if orientation == "wide" else 24
    title_font = _load_font(title_font_size)
    words = title.split()

    lines: list[str] = []
    curr = ""
    max_w = width - 80
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

    line_h = title_font_size + 6
    text_y = lower_y + 24

    for idx_line, line in enumerate(lines[:2]):
        # Drop shadow for clean readability over moving footage
        draw.text((38, text_y + idx_line * line_h + 2), line, font=title_font, fill=(0, 0, 0, 255))
        draw.text((36, text_y + idx_line * line_h), line, font=title_font, fill=(255, 255, 255, 255))

    return np.array(img)

    return np.array(img)


def get_motion_video_path(title: str, text: str = "", index: int = 0) -> pathlib.Path | None:
    """Find matching HD motion MP4 video file from assets."""
    combined = f"{title} {text}".lower()
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
    title_hash = int(hashlib.md5(title.encode()).hexdigest(), 16)
    filename = videos[(index + title_hash) % len(videos)]

    assets_dir = pathlib.Path(__file__).parent.parent.parent / "assets" / "videos"
    local_path = assets_dir / filename
    if local_path.exists():
        return local_path
    return None

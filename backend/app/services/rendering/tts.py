"""Text-to-speech via edge-tts (Microsoft Neural voices — free, CPU-only).

Returns raw MP3 bytes for each narration string.  Called once per scene so
the video renderer can size each image clip to exactly match its audio.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import io
import logging

log = logging.getLogger(__name__)

# Voices that work well for professional / government communications.
# edge-tts uses Microsoft Azure Neural voices; these are freely available.
VOICES: dict[str, str] = {
    "en": "en-US-AriaNeural",       # clear, neutral American English
    "en-GB": "en-GB-SoniaNeural",
    "hi": "hi-IN-SwaraNeural",
    "mr": "hi-IN-SwaraNeural",      # Marathi: closest available
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "bn": "bn-IN-TanishaaNeural",
}

DEFAULT_VOICE = "en-US-AriaNeural"


def _pick_voice(language: str) -> str:
    """Best available neural voice for the requested language tag."""
    if language in VOICES:
        return VOICES[language]
    prefix = language.split("-")[0]
    return VOICES.get(prefix, DEFAULT_VOICE)


async def synthesize(text: str, language: str = "en") -> bytes:
    """Return MP3 bytes for *text* spoken in *language*.

    Raises RuntimeError when edge-tts is not installed or the network is
    unreachable.
    """
    try:
        import edge_tts  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "edge-tts is not installed. Run: pip install edge-tts"
        ) from exc

    voice = _pick_voice(language)
    log.debug("TTS: voice=%s text_len=%d", voice, len(text))

    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])

    data = buf.getvalue()
    if not data:
        raise RuntimeError(f"edge-tts returned empty audio for: {text[:60]!r}")
    return data


def synthesize_sync(text: str, language: str = "en") -> bytes:
    """Blocking wrapper — safe to call from a thread pool or async handler."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(synthesize(text, language))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(synthesize(text, language))).result()

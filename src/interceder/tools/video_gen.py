"""Video generation tool — wraps Google Veo API."""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("interceder.tools.video_gen")


def generate_video(
    *,
    prompt: str,
    duration_seconds: int = 5,
    api_key: str,
) -> dict[str, Any]:
    """Generate a video from a text prompt. Returns metadata dict.

    Phase 10: stub — returns a placeholder.
    """
    log.info("video generation requested: %s (%ds)", prompt[:50], duration_seconds)

    return {
        "status": "stub",
        "prompt": prompt,
        "duration_seconds": duration_seconds,
        "message": "Video generation is stubbed in Phase 10. Wire the Veo API key to enable.",
    }

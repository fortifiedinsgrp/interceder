"""Image generation tool — wraps Gemini Flash Image / Nano Banana API.

Checks for an MCP server first; falls back to direct API call.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("interceder.tools.image_gen")


def generate_image(
    *,
    prompt: str,
    model: str = "gemini-flash-image",
    api_key: str,
) -> dict[str, Any]:
    """Generate an image from a text prompt. Returns metadata dict.

    Phase 10: stub — returns a placeholder. Real implementation uses
    the Google GenAI API or Nano Banana depending on `model`.
    """
    log.info("image generation requested: %s (model=%s)", prompt[:50], model)

    # Stub response
    return {
        "status": "stub",
        "prompt": prompt,
        "model": model,
        "message": "Image generation is stubbed in Phase 10. Wire the API key to enable.",
    }

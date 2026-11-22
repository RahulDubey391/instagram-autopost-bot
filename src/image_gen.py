"""Gemini image generation using the avatar reference face."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image


def generate_avatar_scene(
    reference_face_path: Path,
    prompt: str,
    output_dir: Path,
    model_name: str | None = None,
    api_key: str | None = None,
) -> Path:
    """Generate a new image preserving the reference face in the given scene prompt."""
    if not reference_face_path.exists():
        raise FileNotFoundError(f"Reference face image not found: {reference_face_path}")

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file or environment.")

    model = model_name or os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    output_dir.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=key)
    ref_image = Image.open(reference_face_path)

    response = client.models.generate_content(
        model=model,
        contents=[ref_image, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes: bytes | None = None
    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break
        if image_bytes:
            break

    if not image_bytes:
        raise RuntimeError("Gemini API did not return an image in the response.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"avatar_post_{timestamp}.jpg"

    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img.save(out_path, format="JPEG", quality=95)
    return out_path

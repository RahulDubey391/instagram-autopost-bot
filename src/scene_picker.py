"""Scene composer and caption generator for the avatar pipeline."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SceneSpec:
    """Structured description of a selected or custom scene."""

    country: str
    region: str
    city: str
    venue: str
    outfit: str
    lighting: str
    pose: str
    prompt: str
    caption: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _load_recent_venues(history_path: Path, limit: int = 5) -> set[str]:
    if not history_path.exists():
        return set()
    try:
        entries = json.loads(history_path.read_text(encoding="utf-8"))
        return {
            entry["scene"]["venue"]
            for entry in entries[-limit:]
            if isinstance(entry, dict) and "scene" in entry and "venue" in entry["scene"]
        }
    except (json.JSONDecodeError, OSError, KeyError):
        return set()


def compose_scene(
    scenes_config_path: Path,
    history_path: Path | None = None,
    environment: str | None = None,
    outfit: str | None = None,
    lighting: str | None = None,
    pose: str | None = None,
    seed: int | None = None,
) -> SceneSpec:
    """Compose a scene using provided inputs or random defaults, preserving Face & Body."""
    rng = random.Random(seed)
    data = json.loads(scenes_config_path.read_text(encoding="utf-8"))

    if environment:
        country = "Custom"
        region = "Custom"
        city = "Custom"
        venue = environment.strip()
        location_line = f"Location & Environment: {venue}."
        caption_header = f"{venue} ✨"
        hashtags = "#Lifestyle #TravelDiaries #OOTD #Editorial"
    else:
        recent_venues = _load_recent_venues(history_path) if history_path else set()
        candidates: list[tuple[dict[str, str], str]] = [
            (loc, v) for loc in data["locations"] for v in loc["venues"]
        ]
        fresh = [pair for pair in candidates if pair[1] not in recent_venues]
        loc, venue = rng.choice(fresh if fresh else candidates)
        country = loc["country"]
        region = loc["region"]
        city = loc["city"]
        location_line = f"Location & Environment: {venue} in {city}, {region}, {country}."
        caption_header = f"Current view: {city}, {country} ✨\nSoaking in the vibes at a {venue}."
        city_tag = city.replace(" ", "")
        country_tag = country.replace(" ", "")
        hashtags = f"#{city_tag} #{country_tag} #TravelDiaries #Lifestyle #Wanderlust #OOTD"

    chosen_outfit = outfit.strip() if outfit else rng.choice(data["outfits"])
    chosen_lighting = lighting.strip() if lighting else rng.choice(data["lighting_and_time"])
    chosen_pose = pose.strip() if pose else rng.choice(data["poses_and_activities"])

    prompt = (
        "Using the exact person from the attached reference portrait, strictly preserve BOTH "
        "her exact facial identity (facial structure, sharp jawline, expressive dark eyes, "
        "eyebrows, clean smooth skin, and soft rosy pink blush on her cheeks) AND her exact "
        "body proportions, physique, height, and natural skin tone. Do not alter her face or body shape.\n\n"
        f"{location_line}\n"
        f"Outfit: {chosen_outfit}.\n"
        f"Pose & Expression: {chosen_pose}.\n"
        f"Lighting & Atmosphere: {chosen_lighting}.\n\n"
        "Photography style: High-resolution photorealistic lifestyle photograph shot on 35mm/50mm DSLR, "
        "crisp focus on her face and full-to-three-quarter figure, realistic skin texture with subtle "
        "rosy pink cheek blush, natural background depth and color grading. No text, watermarks, or borders."
    )

    caption = f"{caption_header}\n\n{hashtags}"

    return SceneSpec(
        country=country,
        region=region,
        city=city,
        venue=venue,
        outfit=chosen_outfit,
        lighting=chosen_lighting,
        pose=chosen_pose,
        prompt=prompt,
        caption=caption,
    )

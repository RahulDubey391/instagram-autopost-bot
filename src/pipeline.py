"""End-to-end automated pipeline: Scene (default or custom input) -> Image -> Google Drive."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.drive_upload import upload_to_drive
from src.image_gen import generate_avatar_scene
from src.instagram_upload import publish_to_instagram, upload_to_imgbb
from src.scene_picker import compose_scene


def _append_history(history_path: Path, record: dict) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    if history_path.exists():
        try:
            entries = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(record)
    history_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Automated Avatar Photo Generation & Drive Pipeline")
    parser.add_argument(
        "--environment",
        "-e",
        type=str,
        default=None,
        help="Custom environment/setting (e.g. 'rooftop cafe in Paris at sunset'). Uses random default if omitted.",
    )
    parser.add_argument("--outfit", type=str, default=None, help="Optional custom outfit description.")
    parser.add_argument("--lighting", type=str, default=None, help="Optional custom lighting/time of day.")
    parser.add_argument("--pose", type=str, default=None, help="Optional custom pose/activity.")
    parser.add_argument("--reference", type=str, default=None, help="Optional path to reference face+body image.")
    parser.add_argument("--count", "-n", type=int, default=1, help="Number of images to generate (default: 1).")
    parser.add_argument("--dry-run", action="store_true", help="Preview scene & prompt only; skip API calls.")
    parser.add_argument("--skip-drive", action="store_true", help="Skip Google Drive upload.")
    parser.add_argument(
        "--publish-instagram",
        action="store_true",
        help="Also publish to Instagram Graph API (disabled by default; photos drop to Google Drive).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducible defaults.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    scenes_path = project_root / "config" / "scenes.json"
    reference_face = Path(args.reference) if args.reference else (
        project_root / os.getenv("REFERENCE_FACE_PATH", "avatar/reference_face.jpg")
    )
    output_dir = project_root / os.getenv("OUTPUT_DIR", "generated_images")
    history_path = output_dir / "history.json"

    enable_ig = args.publish_instagram or (
        os.getenv("ENABLE_INSTAGRAM_UPLOAD", "false").lower() == "true"
    )

    for idx in range(args.count):
        run_seed = (args.seed + idx) if args.seed is not None else None
        scene = compose_scene(
            scenes_config_path=scenes_path,
            history_path=history_path,
            environment=args.environment,
            outfit=args.outfit,
            lighting=args.lighting,
            pose=args.pose,
            seed=run_seed,
        )
        print(f"\n=== Run {idx + 1}/{args.count} ===")
        print(f"[Scene] {scene.city}, {scene.country} — {scene.venue}")
        print(f"[Outfit] {scene.outfit}")
        print(f"[Lighting] {scene.lighting}")

        if args.dry_run:
            print("\n[Dry Run] Prompt:\n" + scene.prompt)
            print("\n[Dry Run] Caption:\n" + scene.caption)
            continue

        # 1. Generate image with Gemini (preserving Face & Body)
        image_path = generate_avatar_scene(
            reference_face_path=reference_face,
            prompt=scene.prompt,
            output_dir=output_dir,
        )
        print(f"[Image] Generated: {image_path}")

        record: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reference_image": str(reference_face),
            "image_path": str(image_path),
            "scene": scene.to_dict(),
            "drive": None,
            "instagram": None,
        }

        # 2. Upload to Google Drive
        drive_result = None
        if not args.skip_drive:
            make_public = enable_ig and (
                os.getenv("DRIVE_PUBLIC_FOR_IG", "true").lower() == "true"
                and not os.getenv("IMGBB_API_KEY")
            )
            drive_result = upload_to_drive(image_path=image_path, make_public=make_public)
            record["drive"] = {
                "file_id": drive_result.file_id,
                "web_view_link": drive_result.web_view_link,
                "direct_download_url": drive_result.direct_download_url,
                "method": drive_result.method,
            }
            print(f"[Drive] Uploaded ({drive_result.method}): {drive_result.web_view_link}")

        # 3. Optional Instagram upload (off by default)
        if enable_ig:
            imgbb_key = os.getenv("IMGBB_API_KEY")
            if imgbb_key:
                public_url = upload_to_imgbb(image_path, imgbb_key)
            elif drive_result and os.getenv("DRIVE_PUBLIC_FOR_IG", "true").lower() == "true":
                public_url = drive_result.direct_download_url
            else:
                raise RuntimeError(
                    "Instagram Graph API requires a public image URL. "
                    "Either enable Drive upload with DRIVE_PUBLIC_FOR_IG=true or set IMGBB_API_KEY."
                )

            ig_result = publish_to_instagram(image_url=public_url, caption=scene.caption)
            record["instagram"] = {
                "creation_id": ig_result.creation_id,
                "media_id": ig_result.media_id,
                "image_url_used": ig_result.image_url_used,
            }
            print(f"[Instagram] Published media_id={ig_result.media_id}")

        _append_history(history_path, record)
        print(f"[History] Logged to {history_path}")


if __name__ == "__main__":
    main()

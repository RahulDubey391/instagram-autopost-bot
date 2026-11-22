"""Official Meta Instagram Graph API uploader."""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class InstagramPublishResult:
    creation_id: str
    media_id: str
    image_url_used: str


def upload_to_imgbb(image_path: Path, api_key: str) -> str:
    """Upload an image to ImgBB to obtain a temporary public URL for Instagram Graph API."""
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": encoded},
        timeout=60,
    )
    resp.raise_for_status()
    payload = resp.json()
    return payload["data"]["url"]


def publish_to_instagram(
    image_url: str,
    caption: str,
    ig_account_id: str | None = None,
    access_token: str | None = None,
    api_version: str | None = None,
) -> InstagramPublishResult:
    """Create and publish an image post to an Instagram Business/Creator account."""
    account_id = ig_account_id or os.getenv("INSTAGRAM_ACCOUNT_ID")
    token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
    version = api_version or os.getenv("GRAPH_API_VERSION", "v21.0")

    if not account_id or not token:
        raise ValueError(
            "INSTAGRAM_ACCOUNT_ID and INSTAGRAM_ACCESS_TOKEN must be set in .env or environment."
        )

    base_url = f"https://graph.facebook.com/{version}/{account_id}"

    # Step 1: Create media container
    create_resp = requests.post(
        f"{base_url}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=60,
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # Step 2: Poll container status until FINISHED
    status_url = f"https://graph.facebook.com/{version}/{creation_id}"
    for _ in range(15):
        status_resp = requests.get(
            status_url,
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        status_resp.raise_for_status()
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise RuntimeError(f"Instagram media container processing failed: {status_resp.json()}")
        time.sleep(2)

    # Step 3: Publish container
    publish_resp = requests.post(
        f"{base_url}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": token,
        },
        timeout=60,
    )
    publish_resp.raise_for_status()
    media_id = publish_resp.json()["id"]

    return InstagramPublishResult(
        creation_id=creation_id,
        media_id=media_id,
        image_url_used=image_url,
    )

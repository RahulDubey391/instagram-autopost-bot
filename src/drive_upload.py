"""Google Drive uploader supporting Antigravity `gdrive` CLI and standalone OAuth."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


@dataclass
class DriveUploadResult:
    file_id: str
    web_view_link: str | None
    direct_download_url: str
    method: str


def _upload_via_antigravity_cli(
    image_path: Path,
    folder_id: str | None,
    make_public: bool,
) -> DriveUploadResult:
    cmd = ["gdrive", "mutate", "upload", str(image_path)]
    if folder_id:
        cmd.extend(["--parent", folder_id])

    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = proc.stdout + "\n" + proc.stderr

    # Parse file ID from `gdrive mutate upload` output
    match = re.search(r"\b([A-Za-z0-9_-]{20,})\b", output)
    if not match:
        raise RuntimeError(f"Could not parse Drive file ID from gdrive output:\n{output}")
    file_id = match.group(1)

    if make_public:
        subprocess.run(
            ["gdrive", "mutate", "share", file_id, "--anyone", "--role", "reader"],
            capture_output=True,
            text=True,
            check=True,
        )

    return DriveUploadResult(
        file_id=file_id,
        web_view_link=f"https://drive.google.com/file/d/{file_id}/view",
        direct_download_url=f"https://drive.google.com/uc?export=download&id={file_id}",
        method="antigravity_gdrive_cli",
    )


def _get_oauth_service(credentials_file: Path, token_file: Path):
    creds: Credentials | None = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"Google OAuth credentials file not found: {credentials_file}. "
                    "Download OAuth Desktop Client JSON from Google Cloud Console, "
                    "or run via Antigravity with USE_ANTIGRAVITY_GDRIVE=true."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


def upload_to_drive(
    image_path: Path,
    folder_id: str | None = None,
    make_public: bool = False,
    use_antigravity_cli: bool | None = None,
) -> DriveUploadResult:
    """Upload an image to Google Drive and return its file ID and URLs."""
    if use_antigravity_cli is None:
        use_antigravity_cli = os.getenv("USE_ANTIGRAVITY_GDRIVE", "false").lower() == "true"

    target_folder = folder_id or os.getenv("GDRIVE_FOLDER_ID") or None

    if use_antigravity_cli:
        return _upload_via_antigravity_cli(image_path, target_folder, make_public)

    credentials_file = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
    token_file = Path(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
    service = _get_oauth_service(credentials_file, token_file)

    file_metadata: dict[str, object] = {"name": image_path.name}
    if target_folder:
        file_metadata["parents"] = [target_folder]

    media = MediaFileUpload(str(image_path), mimetype="image/jpeg", resumable=True)
    created = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    file_id = created["id"]

    if make_public:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

    return DriveUploadResult(
        file_id=file_id,
        web_view_link=created.get("webViewLink"),
        direct_download_url=f"https://drive.google.com/uc?export=download&id={file_id}",
        method="google_oauth_api",
    )

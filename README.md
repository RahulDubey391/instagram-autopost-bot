# Instagram Content Agent

Automated workflow that:
1. Uses your selected avatar portrait (`avatar/reference_face.jpg`) as the **Face & Body** reference.
2. Uses either a **custom environment/outfit/pose** you pass in, or picks a **random default environment** from `config/scenes.json` (avoiding recent repeats).
3. Generates new photorealistic photos with the **Google Gemini API** (`gemini-2.5-flash-image` or `gemini-3-pro-image-preview`) preserving both **face and body proportions**.
4. Drops the generated photos into **Google Drive** so you can review and post them manually from the Instagram App. *(Optional Instagram Graph API auto-posting is paused by default and can be enabled later with `--publish-instagram`.)*

---

## Run on GitHub Actions (Recommended)

The workflow [`.github/workflows/generate-and-upload.yml`](.github/workflows/generate-and-upload.yml) lets you run photo generation on demand from **Actions → Generate Avatar Photos & Upload to Drive → Run workflow**.

### Required GitHub Repository Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Value |
| --- | --- |
| `GEMINI_API_KEY` | Your Google AI Studio Gemini API key |
| `GDRIVE_FOLDER_ID` | `1etPWK9I2JyGGmlxqmI9m-jvfPI8Udx7y` (or your target Drive folder ID) |
| `GOOGLE_CREDENTIALS_JSON` | Full JSON contents of `credentials.json` |
| `GOOGLE_TOKEN_JSON` | Full JSON contents of `token.json` |

### Workflow Inputs
When clicking **Run workflow**, you can leave everything blank to use a random default scene, or override:
- `environment` — custom location/setting (e.g., `rooftop cafe overlooking the Eiffel Tower at sunset`)
- `outfit` — custom outfit
- `lighting` — custom lighting/time of day
- `pose` — custom pose/activity
- `count` — number of photos to generate (default `1`)

Generated photos are uploaded to **Google Drive** and also attached as a downloadable **workflow artifact** for 14 days.

---

## Run Locally

1. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and `GDRIVE_FOLDER_ID`.
2. Ensure `credentials.json` and `token.json` are in the project root.
3. Run:
   ```powershell
   # Random default environment -> Generate -> Drop to Google Drive
   .\.venv\Scripts\python.exe -m src.pipeline

   # Custom environment input (and optional outfit/pose/count)
   .\.venv\Scripts\python.exe -m src.pipeline -e "rooftop cafe overlooking the Eiffel Tower at sunset" --outfit "ivory linen midi dress" --count 2
   ```

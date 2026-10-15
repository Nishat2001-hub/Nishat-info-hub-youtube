# Owner approval and handoff

## What is ready

Bengali script validation and 30 curated fallbacks; optional Gemini scripts;
Edge neural TTS, gTTS and offline Bengali eSpeak fallback; FFmpeg 1080x1920
H.264/AAC video with Bengali subtitles; decoded output validation; daily cloud
render; durable duplicate history; channel-bound resumable private-only uploader.

No generation path calls YouTube. OAuth secrets alone cannot enable uploading.
No public/unlisted publishing command exists. No account settings were changed.

## Exact remaining account-owner steps

1. Approve Google Cloud project/API/OAuth configuration described in OAUTH.md.
   No billing account is needed. Google login and channel consent must be done
   personally. Do not send passwords, client JSON or tokens in chat.
2. Run the trusted-computer OAuth helper from OAUTH.md only after approving
   storage of the four credentials in GitHub Actions Secrets. The connected
   GitHub repository API does not expose these secret values for inspection.
3. Optional: approve storing GEMINI_API_KEY from a free-tier project without
   billing. Without this, curated scripts still work; live AI generation is not
   claimed as validated until an authorized key succeeds.
4. Open Actions -> Bengali Shorts Factory -> Run workflow on main. This only
   generates files. Scheduled generation is already configured for 19:00 Dhaka;
   GitHub can delay it. A completed generation on the same day is skipped.
5. Open a successful run, download nishat-tech-RUN_ID within seven days, and
   review short.mp4, metadata.json, subtitles and report.json. Check the voice,
   factual claims, title and disclosure. Copy approval_sha256 from the report.
6. Only if you approve uploading THAT artifact: Actions -> Upload Approved Video
   Privately -> Run workflow on main. Enter source_run_id and approved_sha256.
   This is explicit approval for one PRIVATE upload to the OAuth-bound channel.
   It downloads the same artifact, verifies its digest, persists upload intent,
   uploads, verifies privacy and records the video ID. Reruns cannot duplicate
   an uploaded or uncertain item. It does not upload the thumbnail separately.
7. Public release remains a separate personal approval in YouTube Studio.
   This repository never makes a video public or unlisted.

If artifacts expire, the uploader fails rather than regenerating a different
video under the old approval. Generate/review a new item on a later day.
If a render is skipped, use the earlier successful run that contains the video.

## Free operation and verified limits

Use standard Linux GitHub-hosted runners in this public repository. No paid
services, billing setup, purchases or account setting changes are automated.
Gemini free-tier quotas/model availability and unofficial TTS availability vary.
An account with billing enabled can incur Gemini charges: the code cannot inspect
billing state, so omit the key to guarantee no AI API billing by this project.
Offline speech is a fallback and may sound less natural. Thirty fallback scripts
are finite; when all have been used, generation stops rather than repeating.
YouTube end-to-end OAuth/upload is untested until the owner authorizes it.

Official references:
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://ai.google.dev/gemini-api/docs/pricing
- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/identity/protocols/oauth2/native-app

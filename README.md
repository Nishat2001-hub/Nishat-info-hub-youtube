# NISHAT TECH — Bengali Shorts Factory

Daily GitHub Actions automation for Bengali technology Shorts. Generates a
1080×1920 H.264/AAC video, neural Bengali narration with fallbacks, original
animated backgrounds, Bengali subtitles, fades, title, description and thumbnail.
YouTube uploads are **always Private**. Public/unlisted publishing is absent.

At 13:00 UTC (19:00 Bangladesh), the factory generates a review artifact only.
Push, scheduled and normal manual runs NEVER upload, even after OAuth setup.
A separate manual workflow accepts the reviewed run ID and its approval_sha256.
It checks the exact MP4 and metadata bytes and permits one private upload only.
Public/unlisted publishing is absent. No external account settings are changed.

## One-time authorization

See [secure Google OAuth setup](docs/OAUTH.md). Every daily generation reports "awaiting_approval". All four YouTube secrets
are required only for the separate approved private upload.
Credentials live in GitHub Secrets and are injected into the execution step.

| Secret | Purpose |
| --- | --- |
| YOUTUBE_CLIENT_ID | Desktop OAuth application |
| YOUTUBE_CLIENT_SECRET | Desktop OAuth application |
| YOUTUBE_REFRESH_TOKEN | Offline user consent |
| YOUTUBE_CHANNEL_ID | Channel binding verified before uploading |
| GEMINI_API_KEY (optional) | Gemini AI Studio free-tier scripting |

The OAuth helper stores secrets directly using GitHub CLI over stdin.
It does not print tokens or write an authorized token file.

## Script and voice providers

Without an AI key, 30 curated evergreen Bengali scripts work without AI network
access. Optional Gemini AI Studio (gemini-2.5-flash) generates new scripts; key,
quota, country and model availability apply. Use an AI Studio project without
billing for free-tier-only operation. This project never provisions Google Cloud
resources, enables billing, or uses Vertex AI. It cannot determine whether a key
you supply belongs to a billed project. Invalid/unavailable AI responses fall
back automatically; AI factual accuracy cannot be guaranteed.

The curated catalog stops when exhausted rather than repeating videos.
An AI key or a larger catalog is needed for continuing unique content.
Scripts are checked for Bengali text, length, exact/near duplicates and structure.

Voice order: bn-BD-NabanitaNeural, bn-BD-PradeepNeural, gTTS Bengali, then
offline eSpeak NG Bengali. Edge TTS and gTTS are unofficial services without an
availability SLA; offline speech is less natural. Reports name the voice actually
used. No silence-only substitute is used in production.

## Operations

Actions → **Bengali Shorts Factory** → Run workflow. All runs render without an upload. Download and review the artifact, then follow
[the exact approval steps](docs/APPROVAL.md) if you want one private upload.
Artifacts contain MP4, JPEG thumbnail, ASS/SRT subtitles, metadata and safe reports.
Failed runs remain failed and produce reports when application execution was
reached. GitHub's normal workflow failure notifications can be used.

Persistent history lives in history.json on the separate factory-state
branch, not an expiring cache. It contains no OAuth credentials or resumable
session URLs. Runs are serialized; GitHub history writes use compare-and-swap.
One completed production run is allowed per Bangladesh calendar day.
Render-only days consume their script, preventing later repeats.
The public repository makes script history and video IDs visible; a video ID
does not grant access to a Private video.

See [recovery and limitations](docs/OPERATIONS.md) for uncertain-upload recovery,
OAuth expiry, thumbnails, quotas and costs.

## Development and verification

Python 3.11+, FFmpeg/ffprobe, Noto Bengali fonts and Pillow with libraqm:

~~~sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.main --smoke
python -m src.main --test-render
~~~

Smoke mode renders a short synthetic-tone video for codec/layout validation.
Test-render mode exercises real Bengali voice without persistent state.
Both modes forbid upload. CI runs deterministic tests, a decoded smoke
video and a separate live-voice render. Unit tests use fake YouTube responses;
only a real authorized private upload can establish end-to-end API success.

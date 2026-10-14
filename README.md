# NISHAT TECH — Free Bengali Shorts Factory

GitHub Actions generates a Bengali vertical MP4, voiceover and metadata. The initial version **does not upload to YouTube**, publish, generate live news, or call ChatGPT. It uses reviewed scripts in data/topics.json and Edge TTS (an unofficial online service).

## Run
Actions → Bengali Shorts Factory → Run workflow. Download the artifact after completion.

## Schedule
Cron 13:00 UTC targets 19:00 Asia/Dhaka; GitHub may delay or skip scheduled jobs. Scheduled runs on the default branch.

## Security and limitations
Never commit OAuth tokens. No YouTube credentials are needed for rendering. Topics repeat every three days until the list is expanded. This starter uses a static image rather than animated scenes or timed subtitles. Validate all factual scripts and licensing before publication. A private repository is recommended.

## Next milestone
Add OAuth bootstrap, upload-only-private integration, reliable persistent duplicate protection, subtitles and animation after successful render tests.

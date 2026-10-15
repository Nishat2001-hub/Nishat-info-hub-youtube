# Reliability, recovery and practical limits

## Upload uncertainty

No distributed uploader can guarantee exactly-once delivery across a crash
between YouTube accepting a video and history being saved. The factory persists
"uploading" before sending bytes and refuses later production runs while an
uploading/uncertain entry exists. This trades availability for preventing
blind duplicate uploads. Transient failures retry the same in-memory
resumable session with bounded exponential backoff.

If a run stops in private_upload or save_upload, inspect YouTube Studio's
Private videos for that script and time. If a matching video exists, update its
entry in factory-state/history.json to "uploaded" with video_id and
privacy set to "private". If you confirm no video was created, set the entry's
status to "abandoned". Keep its title/script/key so the topic is not blindly reused.
Never simply delete history to retry. This exceptional reconciliation requires
account-owner access and is not daily work.

If privacy verification fails after a successful insert, the video ID has
already been checkpointed. Thumbnail rejection is reported without uploading
the video again. YouTube must still finish server-side video processing; an
accepted API response does not guarantee successful processing.

## Permissions and secrets

The daily job needs contents write permission for its dedicated state branch.
Repository or organization rules may prohibit it; a failed checkpoint blocks
upload. Do not store tokens/session URLs in history. Use repository Secrets;
daily generation has no YouTube credentials. A separate workflow requires an
explicit run ID and reviewed video/metadata digest for each private upload.
YouTube credentials are exposed only to the approved upload step.

Refresh tokens may expire/revoke after security changes or Google policy changes.
Repeat the personal OAuth helper if needed. Channel binding prevents uploading
to an accidentally authorized different channel.

## Quotas, free operation and thumbnails

YouTube uses a daily free API quota. Quota exhaustion/permission errors fail the
run; retries do not create a new video insert. Gemini free quotas and regional
access can change; the project cannot inspect your key's billing configuration.

The repository is public, where standard GitHub-hosted Actions usage is currently
free. A private repository has plan-dependent included minutes; changing
visibility may affect costs. No billing setup or purchase is performed here.
Artifacts expire after seven days; history does not.

A generated vertical JPEG is always retained. YouTube custom thumbnails require
channel eligibility and Shorts surfaces may ignore a custom thumbnail or require
selecting a video frame in the mobile app. Automatic thumbnail generation does
not guarantee a thumbnail appears on every Shorts surface.

## Content and schedule

The curated fallback has 30 unique topics. If all are used and AI is unavailable,
the run reports catalog exhaustion and stops. AI output is checked mechanically,
not independently fact-checked; keep uploads Private until you approve them.
There is no code option for public/unlisted uploads.

Cron is 13:00 UTC daily (19:00 Bangladesh). GitHub can delay or skip schedules,
and can disable schedules after inactivity on a public repository. At most one
completed generation is recorded per Bangladesh day. Scheduled runs never upload. CI/testing never
touches production history or uploads videos.

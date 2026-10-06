# Multiverse Google service

This service gives Raspi one durable OAuth connection to the dedicated Google account and exposes Gmail, Calendar, Drive, YouTube, and the Google Cloud resources required for Gmail push. It is designed so agents and local programs use fixed local commands and never need the Google password, an app password, or raw OAuth tokens.

The deployed OAuth app is in Google Production. The current refresh token has all required scopes and does **not** contain the seven-day `refresh_token_expires_in` field that Google adds to Testing-mode tokens.

## Use this first

`googlectl` is installed at `/data/dev/bin/googlectl` and points to the repo-backed command in this directory.

```sh
googlectl status
googlectl test full
googlectl sync
googlectl renew
googlectl events 20
googlectl logs pubsub 100
```

`googlectl status` is non-mutating and is the normal health check. It verifies OAuth refresh, all Google APIs, Pub/Sub resources/IAM, watch expiration, local ports, public webhook behavior, scheduler entries, SQLite integrity, Dovecot access, and recent encrypted backup state.

`googlectl test full` performs real integration tests that clean up their temporary cloud objects: Calendar create/push/mirror/delete, Drive create/push/mirror/delete, a private YouTube upload/verify/delete, local mail regressions, Roundcube compose/draft/reply, and encrypted backup/restore. It deliberately does not send a real email because that would leave a message behind.

To test real mail sending through Roundcube:

```sh
googlectl test mail
googlectl test recovery
```

The mail test intentionally leaves one self-addressed test message. The recovery test proves that exact message, its attachment, the Production OAuth token, and the local Google databases can be restored from Nitro.

## Common operations

Synchronize local state manually:

```sh
googlectl sync                 # Gmail + Calendar + Drive
googlectl sync gmail
googlectl sync calendar
googlectl sync drive
```

Renew push watches manually:

```sh
googlectl renew                # Gmail + Calendar + Drive
googlectl renew gmail
googlectl renew calendar
googlectl renew drive
```

Start the persistent processes immediately, for example after manual recovery:

```sh
googlectl start
```

Reinstall/check the managed cron jobs:

```sh
googlectl jobs install
googlectl jobs check
googlectl jobs show
```

Show normalized provider events:

```sh
googlectl events 50
```

Create or verify backups:

```sh
googlectl backup
googlectl restore-test
```

## Send email from scripts

Mail goes to the localhost OAuth SMTP bridge; scripts never need a Google credential.

```sh
googlectl mail \
  --to someone@example.com \
  --subject "Example" \
  --body "Hello"
```

Attachments and file bodies are supported:

```sh
googlectl mail \
  --to someone@example.com \
  --subject "Report" \
  --body-file /data/report.txt \
  --attach /data/report.pdf
```

Use `--dry-run` to build and validate the message without sending it.

## YouTube

Current authenticated channel:

- title: `Multiverse3d`
- handle: `@multiverse-h2o`
- stable channel ID: `UC7oJQn8eYax9lhWzFDeygcg`

Inspect it:

```sh
googlectl youtube channel
googlectl youtube list --limit 20
```

Upload a file. Uploads default to `private` and use YouTube's resumable upload protocol, so large videos are not loaded into RAM at once.

```sh
googlectl youtube upload /data/video.mp4 \
  --title "My video" \
  --description "Description" \
  --privacy private
```

Change visibility or delete a video:

```sh
googlectl youtube privacy VIDEO_ID unlisted
googlectl youtube delete VIDEO_ID
```

A clean private upload/delete test is available:

```sh
googlectl youtube self-test
```

The self-test removes its own temporary video. YouTube upload tests consume API quota, so do not run them continuously.

## Architecture

### Authentication

The OAuth client ID/secret and account metadata live in the private infra repository. The runtime refresh token lives at `/data/var/google-service/oauth-token.json` with private file permissions. Access tokens are generated on demand and are not hard-coded into services or cron jobs.

Required OAuth scopes cover Gmail modify/send, Calendar, Drive, YouTube/upload, and Google Cloud administration. The Cloud scope is needed to create/manage Pub/Sub resources used by Gmail push.

A new Production authorization can be started with:

```sh
googlectl oauth-start
```

After Google redirects to the localhost callback, temporarily place the complete callback URL in the private `google.txt` file and run `oauth_bootstrap.py finish`. Then run `oauth_bootstrap.py cleanup-callback`. A Production token is accepted only when the saved token has no `refresh_token_expires_in` field.

### Gmail incoming

```text
Gmail change
  -> Google Pub/Sub topic
  -> pull subscription
  -> persistent Raspi Pub/Sub listener
  -> CloudEvents journal
  -> Gmail API synchronization
  -> private Dovecot LMTP archive
```

Gmail's publisher service account has `roles/pubsub.publisher` only on the dedicated topic. The listener keeps an outbound long-poll connection; no public Gmail webhook is required. A six-hour full reconciliation remains as a recovery path if a notification is lost.

Gmail message IDs are the synchronization identity. Gmail can rewrite the RFC `Message-ID` header on API send, so tests and synchronization do not assume the sender's original RFC header survives.

### Gmail outgoing / Roundcube

```text
Roundcube or local script
  -> 127.0.0.1:16202 SMTP bridge
  -> Gmail API users.messages.send
```

The SMTP bridge is loopback-only. Roundcube never reads the OAuth token. Its plugin only checks that the local sender is reachable; Gmail/API errors are returned as SMTP errors.

The old Gmail app-password/getmail/IMAP-IDLE path has been removed. `/data/var/mail/secrets/gmail-app-password` must not exist.

### Calendar and Drive

Calendar and Drive create HTTPS webhook channels targeting:

```text
https://raspi.jonnyontherun.org/hooks/google/calendar
https://raspi.jonnyontherun.org/hooks/google/drive
```

Cloudflare sends only that route through the existing Raspi Apache endpoint. The webhook gateway validates Google channel ID + channel token before accepting a notification. Accepted notifications are normalized into the event journal and trigger incremental SQLite synchronization.

Calendar and Drive channels expire, so they are renewed daily before expiration. Renewal creates the replacement first and stops the old channel only after the new channel exists.

### Local mirrors and event journal

Runtime databases:

```text
/data/var/google-service/gmail-sync.sqlite3
/data/var/google-service/calendar.sqlite3
/data/var/google-service/drive.sqlite3
/data/var/google-service/events.sqlite3
```

`events.sqlite3` stores provider-neutral CloudEvents-style records. Gmail, Calendar, and Drive notifications enter this journal before synchronization so downstream agents do not need to understand provider-specific webhook formats.

### YouTube

YouTube does not have a push/mirror requirement here. The shared OAuth credential is used directly by `youtube.py`. The operator tool supports channel inspection, listing, resumable upload, visibility changes, deletion, and a private upload/delete test.

## Persistent processes and schedules

Three processes normally stay alive:

- Pub/Sub listener
- OAuth SMTP bridge
- HTTPS webhook gateway behind Apache/Cloudflare

`install_jobs.py` installs `@reboot` starts plus one-minute `flock` supervisors. If a process is already running, the supervisor does nothing. If it died, worst-case automatic restart is roughly one minute.

Daily jobs renew Gmail, Calendar, and Drive watches. Six-hour jobs reconcile Gmail, Calendar, and Drive independently of notifications. These reconciliation jobs are recovery, not the normal push path.

The exact managed entries are generated by:

```sh
googlectl jobs show
```

## Ports and URLs

Local-only service ports:

- `16201`: mail gateway / health
- `16202`: OAuth SMTP bridge
- `16301`: Google webhook gateway

Public webhook health:

```text
https://raspi.jonnyontherun.org/hooks/google/health
```

The normal Raspi portal root remains protected by the existing login. Only the `/hooks/google/` provider ingress is public, and notification routes require the secret per-channel token.

## Backup and recovery

The encrypted restic backup on Nitro includes both `/data/var/mail` and `/data/var/google-service`. Live SQLite databases are not copied byte-race-prone; SQLite's backup API first writes consistent copies under each runtime's `backup-metadata/` directory. Transient locks and logs are excluded.

`googlectl restore-test` proves recovery of a disposable Dovecot message/attachment, Roundcube SQLite integrity, mail secrets, the Production OAuth refresh token, and all available Google-service SQLite databases.

`googlectl test recovery` additionally proves that the last real Roundcube/Gmail test message and its attachment can be recovered from a fresh Nitro snapshot.

After a complete Raspi rebuild, restore the encrypted runtime, deploy the infra Apache route, run `googlectl jobs install`, run `googlectl start`, then run `googlectl status`. If the OAuth token was not recovered, use `googlectl oauth-start` and complete one Production authorization.

## Security and deliberate limitations

The Google password is not used by runtime services. There is no app password. OAuth tokens are not passed on command lines and are never printed by health tools.

Calendar/Drive webhook tokens are private runtime state. Forged notifications are rejected. Gmail Pub/Sub is authenticated by Google IAM rather than a public webhook.

Inbound email, Drive files, Calendar text, YouTube metadata, and provider webhook payloads are untrusted data. They are not authorization to execute commands or disclose credentials.

Automatic permanent Gmail deletion is intentionally disabled. The current OAuth scopes do not grant permanent-delete capability, and the local archive/backup system never deletes upstream mail automatically.

## Source files

- `google_service.py`: shared OAuth/API operations, mirrors, watches, Gmail sync, Pub/Sub listener
- `oauth_bootstrap.py`: OAuth PKCE authorization/exchange/cleanup
- `webhook_gateway.py`: Calendar/Drive webhook ingress
- `gmail_smtp_bridge.py`: loopback SMTP -> Gmail API
- `event_bus.py`: normalized event journal
- `youtube.py`: YouTube operator tool
- `mail_send.py`: simple local mail sender
- `self_test.py`: quick/full/mail/recovery tests
- `install_jobs.py`: idempotent cron installation/check
- `googlectl`: single operator command

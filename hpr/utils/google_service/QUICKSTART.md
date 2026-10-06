# Google service quick reference

Use `googlectl` for normal operation. It is installed at `/data/dev/bin/googlectl` and points at the repo-backed implementation.

## The five commands to remember

```sh
googlectl status          # safe, non-mutating health check
googlectl test full       # integration test; temporary cloud objects are cleaned up
googlectl sync            # reconcile Gmail + Calendar + Drive now
googlectl renew           # renew all Google push watches now
googlectl events 20       # newest normalized Gmail/Calendar/Drive events
```

For a deliberately exhaustive test, including a real self-addressed email, Nitro recovery, and killing/restarting the persistent processes:

```sh
googlectl test all
```

`test all` is intentionally disruptive for about one minute during the supervisor test and leaves one real self-addressed mail test message. Temporary Calendar, Drive, and YouTube test objects are deleted automatically.

## Send mail

```sh
googlectl mail --to person@example.com --subject "Subject" --body "Text"
googlectl mail --to person@example.com --subject "Report" --body-file /data/report.txt --attach /data/report.pdf
googlectl mail --to person@example.com --subject "Check" --body "No send" --dry-run
```

Mail goes through the localhost OAuth bridge. No Gmail password or app password is used.

## YouTube

```sh
googlectl youtube channel
googlectl youtube list --limit 20
googlectl youtube upload /data/video.mp4 --title "Title" --privacy private
googlectl youtube privacy VIDEO_ID unlisted
googlectl youtube delete VIDEO_ID
googlectl youtube self-test
```

Uploads default to `private`. `youtube self-test` creates a temporary video, checks `private -> unlisted -> private`, then deletes it and verifies deletion.

## Backup / recovery

```sh
googlectl backup
googlectl restore-test
googlectl test mail
googlectl test recovery
```

The encrypted restic repository is on Nitro. `test recovery` verifies the exact last real mail test and its attachment as well as OAuth/runtime state.

## If something looks broken

```sh
googlectl status
googlectl jobs check
googlectl start
googlectl logs pubsub 100
googlectl logs smtp 100
googlectl logs webhook 100
```

`googlectl start` is idempotent: `flock` prevents duplicate persistent processes. Managed cron supervisors restart a dead listener/bridge/gateway within roughly one minute.

## Architecture in one screen

```text
Gmail -> Pub/Sub -> Raspi listener -> Gmail API sync -> Dovecot
Roundcube/scripts -> localhost SMTP bridge -> Gmail API
Calendar -> HTTPS webhook -> Raspi -> local SQLite mirror
Drive -> HTTPS webhook -> Raspi -> local SQLite mirror
Gmail/Calendar/Drive notifications -> CloudEvents journal
YouTube commands -> YouTube Data API
```

Public webhook ingress is limited to `/hooks/google/`. Calendar/Drive notifications require their secret channel tokens. The normal Raspi portal remains authenticated.

For implementation details, OAuth recovery, ports, security rules, and rebuild instructions, read `README.md` in this directory.

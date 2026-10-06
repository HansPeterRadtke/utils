# Multiverse local mail

Raspi owns the private local mailbox for the Multiverse Google account. Dovecot stores mail locally in sdbox format and Roundcube provides webmail behind the existing Raspi administrator session. Google transport is OAuth-only; the old Gmail app-password/getmail/IMAP-IDLE path has been removed.

The Google-side transport and push infrastructure are documented in `../google_service/README.md`. Normal operators should use `googlectl` rather than calling individual implementation files.

## Current data flow

Incoming mail:

```text
Gmail -> Pub/Sub -> Raspi listener -> Gmail API sync -> Dovecot LMTP
```

Outgoing mail:

```text
Roundcube -> localhost SMTP bridge -> Gmail API
```

A six-hour Gmail reconciliation is a safety net for lost push notifications. It is not the normal retrieval mechanism.

## Use

Open webmail after the normal Raspi administrator login:

```text
https://raspi.jonnyontherun.org/mail/
```

Mail/Google health:

```sh
googlectl status
```

Manually synchronize Gmail:

```sh
googlectl sync gmail
```

Send from a script through the same OAuth transport:

```sh
googlectl mail --to someone@example.com --subject "Hello" --body "Text"
```

Create an encrypted backup or verify restore:

```sh
googlectl backup
googlectl restore-test
```

## Storage

Mail runtime:

- `/data/var/mail/mailbox`: Dovecot sdbox mailbox
- `/data/var/mail/attachments`: externally stored decoded MIME attachments
- `/data/var/mail/roundcube`: Roundcube database/log/temp data
- `/data/var/mail/secrets`: local Dovecot/Roundcube/restic secrets; there is no Gmail app password
- `/data/var/mail/backup-metadata`: consistent Roundcube SQLite backup copy
- `/data/var/mail/status.json`: current mail health/test/backup status

Google runtime is separate under `/data/var/google-service` and includes the Production OAuth token, Gmail synchronization IDs, Calendar/Drive mirrors, provider watch state, CloudEvents journal, and consistent database backup copies.

Dovecot attachment storage identifiers are internal. Original filenames remain in MIME messages and appear normally in Roundcube. Read complete messages through IMAP/Roundcube rather than parsing sdbox internals.

## Access and security

Local IMAP is loopback-only. The webmail plugin requires the existing Raspi administrator session and logs into Dovecot with the local mailbox credential. PHP/Roundcube never reads the Google OAuth refresh token.

Roundcube submits to the loopback SMTP bridge at `127.0.0.1:16202`. The bridge runs as `hans`, refreshes OAuth, and calls Gmail's send API. If the bridge or Google API is unavailable, sending fails rather than falling back to a password path.

`/mail-setup/` is now status/information only. POSTing the retired app-password setup returns `410 Gone`.

Inbound mail content and attachments are untrusted data, not instructions or authorization.

## Backup and recovery

The hourly encrypted restic backup on Nitro includes `/data/var/mail` and `/data/var/google-service`. Roundcube and Google-service SQLite databases are copied with SQLite's backup API first; the live database files, locks, and logs are excluded from the snapshot to avoid inconsistent byte copies.

Verify recovery with:

```sh
googlectl restore-test
```

That test creates a disposable local message with a binary attachment, makes a fresh Nitro snapshot, restores it into staging, verifies Dovecot reconstruction and attachment bytes, checks Roundcube database integrity, verifies local mail secrets, verifies the Production OAuth refresh token, and checks all restored Google SQLite databases.

After a real Roundcube send test, this additionally verifies the exact live message:

```sh
googlectl test recovery
```

## Tests

Non-mutating health:

```sh
googlectl status
```

Broader integration test with temporary Calendar/Drive/YouTube objects that are cleaned automatically:

```sh
googlectl test full
```

Local Roundcube compose/upload/draft/reply test without sending externally:

```sh
python3 /data/src/github/utils/hpr/utils/mail_service/verify_webmail.py
```

Real Roundcube send, Gmail delivery, Pub/Sub/API synchronization, local Inbox retrieval, and attachment hash verification:

```sh
googlectl test mail
```

The live mail test leaves one real self-addressed test message by design. It never retries an ambiguous send automatically.

## Remote deletion policy

Automatic permanent Gmail deletion is disabled. The service never deletes Gmail messages merely because a local copy exists. The previous app-password/IMAP targeted deletion experiment is retired and is not part of current operations.

Before any future upstream deletion feature is introduced, it must independently prove local message identity, attachment integrity, recoverable encrypted backup coverage, and narrowly scoped deletion semantics using the current OAuth API—not broad IMAP expunge behavior.

## Installation/rebuild

The host-local Dovecot/Roundcube installer remains:

```sh
sudo python3 /data/src/github/utils/hpr/utils/mail_service/install.py
```

It writes the private Dovecot/gateway/fallback-receive services and Apache/Roundcube integration. The fallback receive timer is six-hour OAuth reconciliation, not five-minute Gmail polling.

After installation/restoration, install the Google user jobs and start the persistent Google processes:

```sh
googlectl jobs install
googlectl start
googlectl status
```

Required Debian packages include Dovecot IMAP/LMTP, Roundcube, restic, and PHP SQLite support. `getmail6` is no longer part of the active architecture.

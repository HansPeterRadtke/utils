#!/usr/bin/env python3
"""Send mail through the localhost OAuth SMTP bridge."""
import argparse
from email.message import EmailMessage
import json
import mimetypes
from pathlib import Path
import smtplib

CONFIG = Path('/data/var/mail/config.json')


def build_message(args):
    cfg = json.loads(CONFIG.read_text())
    msg = EmailMessage()
    msg['From'] = cfg['account']
    msg['To'] = ', '.join(args.to)
    if args.cc:
        msg['Cc'] = ', '.join(args.cc)
    msg['Subject'] = args.subject
    if args.body_file:
        body = Path(args.body_file).read_text()
    else:
        body = args.body or ''
    msg.set_content(body)
    for value in args.attach:
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(path)
        guessed = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        maintype, subtype = guessed.split('/', 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def main():
    parser = argparse.ArgumentParser(description='Send email through the local Gmail OAuth bridge')
    parser.add_argument('--to', action='append', required=True, help='Recipient; repeat for multiple recipients')
    parser.add_argument('--cc', action='append', default=[], help='CC recipient; repeat as needed')
    parser.add_argument('--subject', required=True)
    body = parser.add_mutually_exclusive_group()
    body.add_argument('--body', default='')
    body.add_argument('--body-file')
    parser.add_argument('--attach', action='append', default=[], help='Attachment path; repeat as needed')
    parser.add_argument('--dry-run', action='store_true', help='Build and validate the message without sending')
    args = parser.parse_args()
    msg = build_message(args)
    if args.dry_run:
        print('dry_run=OK')
        print('bytes=' + str(len(msg.as_bytes())))
        print('attachments=' + str(len(args.attach)))
        return 0
    recipients = args.to + args.cc
    with smtplib.SMTP('127.0.0.1', 16202, timeout=30) as smtp:
        failures = smtp.send_message(msg, to_addrs=recipients)
    if failures:
        raise RuntimeError('SMTP bridge rejected recipients: ' + ','.join(sorted(failures)))
    print('send=OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

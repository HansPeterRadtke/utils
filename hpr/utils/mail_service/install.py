#!/usr/bin/env python3
"""Install the Debian mail integration. Run with sudo after registering infra ports."""
import grp
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import sqlite3
import subprocess

SOURCE = Path(__file__).resolve().parent
ROOT = Path("/data/var/mail")
INFRA = Path("/data/infra")
USER = pwd.getpwnam("hans")
WEB = grp.getgrnam("www-data").gr_gid

def write(path, content, mode=0o644, uid=0, gid=0):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.chown(path, uid, gid)
    path.chmod(mode)

def directory(path, mode=0o700, uid=USER.pw_uid, gid=USER.pw_gid):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.chown(path, uid, gid)
    path.chmod(mode)

def secret(name, length=48, shared=False):
    path = ROOT / "secrets" / name
    if not path.exists():
        write(path, secrets.token_urlsafe(length)[:length] + "\n",
              0o640 if shared else 0o600, USER.pw_uid, WEB if shared else USER.pw_gid)
    return path.read_text().strip()

def main():
    if os.geteuid():
        raise SystemExit("Run with sudo.")
    ports = json.loads((INFRA / "etc/ports.json").read_text())["services"]
    imap_port = ports["local_mail_imap"]["base"]
    gateway_port = ports["mail_gateway"]["base"]
    directory(ROOT, 0o750, gid=WEB)
    for name in ["home", "mailbox", "attachments", "backup-metadata", "dovecot-state"]:
        directory(ROOT / name)
    directory(ROOT / "run", 0o750, gid=WEB)
    directory(ROOT / "secrets", 0o2750, gid=WEB)
    directory(ROOT / "roundcube", 0o770, gid=WEB)
    for name in ["temp", "logs"]:
        directory(ROOT / "roundcube" / name, 0o770, gid=WEB)
    configuration = {
        "account": "multiverse3dhpr@gmail.com", "display_name": "Multiverse",
        "imap_port": imap_port, "gateway_port": gateway_port,
        "portal_host": "raspi", "portal_helper": "/data/infra/services/common",
        "portal_secret": "/data/var/web_portal/session_secret",
        "public_origin": "https://raspi.jonnyontherun.org",
        "backup_repository": "sftp:nitro:/data/var/backups/raspi-mail",
        "remote_deletion": False
    }
    config_path = ROOT / "config.json"
    if config_path.exists():
        configuration.update(json.loads(config_path.read_text()))
    configuration.update(imap_port=imap_port, gateway_port=gateway_port)
    write(config_path, json.dumps(configuration, indent=2) + "\n", 0o640, USER.pw_uid, WEB)
    password = secret("local-password", shared=True)
    secret("roundcube-key", 24, shared=True)
    secret("backup-password")
    # Password travels on stdin, never in argv, shell history, or logs.
    hashed = subprocess.run(["openssl", "passwd", "-6", "-stdin"], input=password + "\n",
                            capture_output=True, text=True, check=True).stdout.strip()
    write("/etc/local-mail/passwd", configuration["account"] + ":{SHA512-CRYPT}" + hashed + "\n",
          0o640, 0, grp.getgrnam("dovecot").gr_gid)
    dovecot = f"""base_dir = /run/local-mail-dovecot
state_dir = {ROOT}/dovecot-state
protocols = imap lmtp
listen = 127.0.0.1
ssl = no
disable_plaintext_auth = no
auth_mechanisms = plain login
auth_username_format = %Lu
mail_uid = {USER.pw_uid}
mail_gid = {USER.pw_gid}
first_valid_uid = {USER.pw_uid}
mail_home = {ROOT}/home
mail_location = sdbox:{ROOT}/mailbox
mail_attachment_dir = {ROOT}/attachments
mail_attachment_fs = posix
mail_attachment_min_size = 1
mail_fsync = always
recipient_delimiter = +
lmtp_save_to_detail_mailbox = yes
passdb {{
  driver = passwd-file
  args = /etc/local-mail/passwd
}}
userdb {{
  driver = static
  args = uid={USER.pw_uid} gid={USER.pw_gid} home={ROOT}/home
}}
service imap-login {{
  inet_listener imap {{
    address = 127.0.0.1
    port = {imap_port}
  }}
  inet_listener imaps {{
    port = 0
  }}
}}
service lmtp {{
  unix_listener {ROOT}/run/lmtp {{
    mode = 0600
    user = hans
    group = hans
  }}
}}
service auth {{
  unix_listener auth-userdb {{
    mode = 0600
    user = hans
    group = hans
  }}
}}
namespace inbox {{
  inbox = yes
  separator = /
  mailbox Drafts {{
    auto = subscribe
    special_use = \\Drafts
  }}
  mailbox Sent {{
    auto = subscribe
    special_use = \\Sent
  }}
  mailbox Junk {{
    auto = subscribe
    special_use = \\Junk
  }}
  mailbox Trash {{
    auto = subscribe
    special_use = \\Trash
  }}
  mailbox Archive {{
    auto = subscribe
    special_use = \\Archive
  }}
}}
log_path = /dev/stderr
info_log_path = /dev/stderr
"""
    write("/etc/local-mail/dovecot.conf", dovecot)
    write("/etc/systemd/system/local-mail-dovecot.service", """[Unit]
Description=Private local mail storage
After=network.target
RequiresMountsFor=/data
[Service]
Type=simple
ExecStart=/usr/sbin/dovecot -F -c /etc/local-mail/dovecot.conf
Restart=on-failure
RuntimeDirectory=local-mail-dovecot
RuntimeDirectoryMode=0755
[Install]
WantedBy=multi-user.target
""")
    shared_unit = f"""[Unit]
RequiresMountsFor=/data
After=network-online.target local-mail-dovecot.service
Wants=network-online.target
[Service]
User=hans
Group=www-data
SupplementaryGroups=hans
UMask=0077
WorkingDirectory={SOURCE}
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
"""
    write("/etc/systemd/system/local-mail-gateway.service", shared_unit + f"""Type=simple
ExecStart=/usr/bin/python3 {SOURCE}/mail_service.py serve
Restart=on-failure
[Install]
WantedBy=multi-user.target
""")
    write("/etc/systemd/system/local-mail-receive.service", shared_unit + f"""Type=oneshot
ExecStart=/usr/bin/python3 {SOURCE}/mail_service.py receive
TimeoutStartSec=3h
""")
    write("/etc/systemd/system/local-mail-receive.timer", """[Unit]
Description=Fallback Gmail OAuth reconciliation
[Timer]
OnBootSec=5min
OnUnitInactiveSec=6h
RandomizedDelaySec=5min
Persistent=true
[Install]
WantedBy=timers.target
""")
    write("/etc/systemd/system/local-mail-backup.service", shared_unit + f"""Type=oneshot
ExecStart=/usr/bin/python3 {SOURCE}/mail_service.py backup
TimeoutStartSec=1h
""")
    write("/etc/systemd/system/local-mail-backup.timer", """[Unit]
Description=Back up local mail including unsent drafts
[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=1min
[Install]
WantedBy=timers.target
""")
    plugin = Path("/var/lib/roundcube/plugins/portal_mail")
    plugin.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / "portal_mail.php", plugin / "portal_mail.php")
    (plugin / "portal_mail.php").chmod(0o644)
    rc_cfg = Path("/etc/roundcube/config.inc.php")
    include = f"require '{SOURCE}/roundcube.inc.php';"
    existing = rc_cfg.read_text()
    if include not in existing:
        backup_path = Path("/data/var/backups/mail-setup-preflight/roundcube-config.inc.php")
        if not backup_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rc_cfg, backup_path)
            backup_path.chmod(0o600)
        with rc_cfg.open("a") as out:
            out.write("\n// Local archive deployment from utils.\n" + include + "\n")
    database = ROOT / "roundcube/roundcube.db"
    if not database.exists():
        with sqlite3.connect(database) as conn:
            conn.executescript(Path("/usr/share/roundcube/SQL/sqlite.initial.sql").read_text())
    os.chown(database, USER.pw_uid, WEB)
    database.chmod(0o660)
    apache = f"""# Multiverse Mail: integrated with the existing administrator portal session.
RedirectMatch 302 ^/mail$ /mail/
RedirectMatch 302 ^/mail-setup$ /mail-setup/
ProxyPass /mail-setup/ http://127.0.0.1:{gateway_port}/mail-setup/ retry=0 timeout=65
ProxyPassReverse /mail-setup/ http://127.0.0.1:{gateway_port}/mail-setup/
Alias /mail/ /var/lib/roundcube/public_html/
<Directory /var/lib/roundcube/public_html/>
    Options -Indexes +FollowSymLinks
    AllowOverride All
    Require all granted
    php_admin_value upload_max_filesize 25M
    php_admin_value post_max_size 30M
    php_admin_flag session.cookie_httponly On
    php_admin_flag session.cookie_secure On
    php_admin_value session.cookie_samesite Lax
</Directory>
"""
    write("/etc/apache2/conf-available/local-mail-vhost.inc", apache)
    host = json.loads((INFRA / "hosts/raspi/config.json").read_text())
    vhost = Path(host["web_portal"]["apache_site"])
    include = "  IncludeOptional /etc/apache2/conf-available/local-mail-vhost.inc"
    content = vhost.read_text()
    if include not in content:
        backup_path = Path("/data/var/backups/mail-setup-preflight/apache-000-default.conf")
        if not backup_path.exists():
            shutil.copy2(vhost, backup_path)
        vhost.write_text(content.replace("</VirtualHost>", include + "\n</VirtualHost>", 1))
    subprocess.run(["doveconf", "-c", "/etc/local-mail/dovecot.conf", "-n"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["apache2ctl", "configtest"], check=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", "local-mail-dovecot.service", "local-mail-gateway.service"], check=True)
    subprocess.run(["systemctl", "restart", "local-mail-dovecot.service", "local-mail-gateway.service"], check=True)
    subprocess.run(["systemctl", "reload", "apache2"], check=True)
    print("Local services installed. Initialize and verify the Nitro backup before enabling timers.")

if __name__ == "__main__":
    main()

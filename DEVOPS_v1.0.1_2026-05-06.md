# sltp-tg-bot — DevOps Deployment & Operations Guide

**Guide version:** 1.0.1 · *Last updated: 2026-05-06*
**Applies to:** `sltp-tg-bot` v1.0.0 (Python) + `BulkSLTPUpdater` EA v1.3.0 (MQL5)
**Target audience:** Senior Ubuntu sysadmin / DevOps engineer deploying the bot for the first time.
**Project maintainer:** Thanh Nguyen · [thanhglobalist@gmail.com](mailto:thanhglobalist@gmail.com) · [t.me/thanhglobalist](https://t.me/thanhglobalist)

> This guide is **self-contained**. Hand-off requires nothing outside this file, the `sltp-tg-bot/` project tree, and a DigitalOcean account.

---

## Changelog

### [1.0.1] — 2026-05-06

- **Added Appendix E — Free DDNS as a domain alternative** (DuckDNS / No-IP). Lets operators deploy without buying a domain while still getting Let's Encrypt-issued, browser-trusted TLS certificates. Raw-IP deployment remains explicitly out of scope (no TLS path).
- Prerequisites table now lists three valid hostname options (owned domain · subdomain of an owned domain · free DDNS subdomain) and cross-references Appendix E.
- §5.3 (Obtain TLS cert) now points DDNS users to the Appendix E variant of the certbot command.
- Troubleshooting matrix gains a row for DDNS-specific cert failures.

### [1.0.0] — 2026-05-05

- Initial release of the DevOps guide.
- Covers native deployment (primary path) and Docker Compose (Appendix B).
- DigitalOcean Spaces backup flow, including bucket creation, IAM keys, GPG encryption, and 7/4/12 retention.
- Security hardening checklist and a matrix-style troubleshooting reference.
- 10 operational runbooks with copy-paste commands.
- Zero-downtime upgrade / rollback procedures.
- Disaster-recovery scenarios A–D.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [System hardening](#3-system-hardening)
4. [Native deployment](#4-native-deployment)
5. [Reverse proxy & TLS](#5-reverse-proxy--tls)
6. [Operational runbooks](#6-operational-runbooks)
7. [Monitoring](#7-monitoring)
8. [Backup strategy](#8-backup-strategy)
9. [Disaster recovery scenarios](#9-disaster-recovery-scenarios)
10. [Security checklist (pre-launch)](#10-security-checklist-pre-launch)
11. [Troubleshooting matrix](#11-troubleshooting-matrix)
12. [Upgrade procedure (zero-downtime where possible)](#12-upgrade-procedure-zero-downtime-where-possible)
13. [Appendix A — Native config reference](#13-appendix-a--native-config-reference)
14. [Appendix B — Docker Compose deployment](#14-appendix-b--docker-compose-deployment)
15. [Appendix C — DigitalOcean specifics](#15-appendix-c--digitalocean-specifics)
16. [Appendix D — Audit log spec](#16-appendix-d--audit-log-spec)
17. [Appendix E — Free DDNS as a domain alternative](#17-appendix-e--free-ddns-as-a-domain-alternative)

---

## 1. Overview

`sltp-tg-bot` is a small Python service that sits between a trader's Telegram and one-or-more MT5 terminals running the Bulk SL/TP Updater EA (v1.3.0). It:

- Accepts commands from authorized Telegram users (`/status`, `/closeall`, `/sl <price>`, …).
- Exposes an HTTP/JSON **bridge API** that MT5 EAs long-poll for jobs (`/api/v1/jobs/next`) and use to post heartbeats, trade results, and alerts.
- Persists all state (accounts, tokens, team members, roles, jobs, audit log) in a single SQLite database (`/var/lib/sltp-tg-bot/sltp.db`).
- Supports three end-user languages: **English, Japanese, Vietnamese** — handled entirely in code, no DevOps action required.

### Network diagram & trust boundaries

```
               ┌──────────────────┐                     ┌───────────────────┐
               │  Telegram users  │─────TLS (tg API)────│   Telegram API    │
               │  (phones, PCs)   │◀────────────────────│     (Telegram)    │
               └──────────────────┘                     └────────┬──────────┘
                                                                 │ long-poll
                                                                 ▼
                             ┌───────────────────────────────────────────────┐
                             │  Ubuntu droplet (DigitalOcean) — trust zone A │
                             │   - nginx  (443 public, 80→443 redirect)      │
                             │   - sltp-tg-bot.service (127.0.0.1:8080)      │
                             │   - SQLite DB in /var/lib/sltp-tg-bot/        │
                             │   - UFW, fail2ban, unattended-upgrades        │
                             └──────┬────────────────────────────────────────┘
                                    │  HTTPS + Bearer token
                                    │  (443 inbound from Windows VPSes only)
                                    ▼
                      ┌───────────────────────────────┐
                      │  Windows VPSes — trust zone B │
                      │  MT5 terminal + EA fleet      │
                      │  (outbound-only)              │
                      └───────────────────────────────┘
```

**Trust zones:**

- **Zone A (droplet)** is the only node reachable from the public internet. It holds the bot token (from BotFather), all EA tokens, and the team directory.
- **Zone B (Windows VPSes)** are outbound-only. Each EA holds exactly one Bearer token scoped to one MT5 login; compromise of one VPS does not grant access to others.
- The SQLite DB is the only persistent state. Everything else (sessions, job queue) is in-memory.

---

## 2. Prerequisites

| Item                              | Requirement                                                                            |
|-----------------------------------|----------------------------------------------------------------------------------------|
| OS                                | Ubuntu 22.04 LTS (tested) or 24.04 LTS (supported).                                    |
| Droplet size (DO)                 | **Minimum 2 GB RAM** (1 vCPU, s-1vcpu-2gb). **Recommended 4 GB** for > 10 accounts (see Appendix C). |
| Hostname (any of three)           | **(a)** owned domain (e.g. `bot.yourdomain.com`) — preferred for production.<br>**(b)** subdomain of an existing owned domain — same TLS path as (a).<br>**(c)** free DDNS subdomain (e.g. `bot-thanh.duckdns.org`) — full TLS via Let's Encrypt; see **Appendix E**.<br>Raw IPs are **not** supported (no Let's Encrypt path; EA token would traverse plaintext). |
| SSH access                        | Key-based login as a sudoer (password auth will be disabled in §3).                    |
| Outbound 443                      | Required — always open on DO by default.                                               |
| Inbound 80 / 443                  | Opened via UFW in §3. Everything else stays closed.                                    |
| Telegram bot token                | Generated by talking to `@BotFather` on Telegram (see §4).                             |
| Trader's Telegram numeric user ID | Admin user. The trader sends `/getmyid` to any Telegram ID bot; you need this number.   |
| DigitalOcean Spaces (optional)    | For off-host encrypted backups (§8). Bucket + access key + secret.                      |

---

## 3. System hardening

Do this on a **fresh** droplet before anything else. Run as root or with `sudo`.

```bash
# (1) Update package lists and apply current security patches.
apt update && apt upgrade -y

# (2) Automate future security patches.
apt install -y unattended-upgrades apt-listchanges
dpkg-reconfigure --priority=low unattended-upgrades   # Enable: Yes

# (3) Firewall. Deny by default, allow SSH + 80 + 443.
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

# (4) SSH: disable password auth, key-only. Edit /etc/ssh/sshd_config so:
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/'   /etc/ssh/sshd_config
sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/'  /etc/ssh/sshd_config
systemctl restart ssh

# (5) Brute-force protection on SSH.
apt install -y fail2ban
cat >/etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled  = true
port     = ssh
backend  = systemd
maxretry = 5
bantime  = 1h
findtime = 10m
EOF
systemctl enable --now fail2ban
fail2ban-client status sshd
```

Verify afterward:

```bash
ufw status                          # expect: 22/tcp, 80/tcp, 443/tcp ALLOW
fail2ban-client status              # expect: 'sshd' listed
sshd -T | grep -E 'passwordauth|permitrootlogin'   # both 'no'/'prohibit-password'
```

---

## 4. Native deployment

This is the **primary** path. Docker is in Appendix B.

### 4.1 Install Python 3.11

```bash
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev build-essential \
               sqlite3 git curl
python3.11 --version    # verify 3.11.x
```

### 4.2 Create an unprivileged service user

```bash
useradd --system --home-dir /opt/sltp-tg-bot --shell /usr/sbin/nologin \
        --comment 'sltp-tg-bot service' sltpbot
id sltpbot
```

### 4.3 Create directories

```bash
install -d -o sltpbot -g sltpbot -m 0750 /opt/sltp-tg-bot
install -d -o sltpbot -g sltpbot -m 0750 /var/lib/sltp-tg-bot
install -d -o sltpbot -g sltpbot -m 0750 /var/log/sltp-tg-bot
install -d -o root    -g root    -m 0750 /etc/sltp-tg-bot
install -d -o root    -g root    -m 0750 /var/backups/sltp-tg-bot
```

Path summary (copy-able reference):

| Path                          | Purpose                    | Owner       | Mode  |
|-------------------------------|----------------------------|-------------|-------|
| `/opt/sltp-tg-bot`            | Code + virtualenv          | `sltpbot`   | 0750  |
| `/var/lib/sltp-tg-bot`        | SQLite DB (`sltp.db`)      | `sltpbot`   | 0750  |
| `/var/log/sltp-tg-bot`        | Ad-hoc logs (backup, etc.) | `sltpbot`   | 0750  |
| `/etc/sltp-tg-bot`            | `.env`, backup creds       | `root`      | 0750  |
| `/var/backups/sltp-tg-bot`    | Local nightly snapshots    | `root`      | 0750  |

### 4.4 Fetch the project & install

```bash
# Clone (or rsync from your CI). Replace with your git URL.
sudo -u sltpbot git clone https://github.com/YOURORG/sltp-tg-bot.git /opt/sltp-tg-bot

# Alternatively, if you received a tarball:
#   tar xzf sltp-tg-bot-1.0.0.tar.gz -C /opt/
#   chown -R sltpbot:sltpbot /opt/sltp-tg-bot

cd /opt/sltp-tg-bot
sudo -u sltpbot python3.11 -m venv venv
sudo -u sltpbot ./venv/bin/pip install --upgrade pip
sudo -u sltpbot ./venv/bin/pip install -e .
```

### 4.5 Configure the environment file

```bash
install -o root -g sltpbot -m 0640 /dev/null /etc/sltp-tg-bot/sltp-tg-bot.env
cp /opt/sltp-tg-bot/.env.example /etc/sltp-tg-bot/sltp-tg-bot.env
$EDITOR /etc/sltp-tg-bot/sltp-tg-bot.env
```

Minimum fields to fill:

| Key                        | Value                                                              |
|----------------------------|--------------------------------------------------------------------|
| `BOT_TOKEN`                | Telegram token from `@BotFather` (format `123456789:ABC-...`)      |
| `ADMIN_USER_ID`            | Trader's Telegram numeric ID (e.g. `123456789`)                    |
| `BRIDGE_PUBLIC_URL`        | `https://bot.yourdomain.com` — must match the nginx server_name    |
| `DB_PATH`                  | `/var/lib/sltp-tg-bot/sltp.db` (keep default)                      |
| `LISTEN_HOST`              | `127.0.0.1` (nginx fronts TLS — do NOT listen on 0.0.0.0)          |
| `LISTEN_PORT`              | `8080` (keep default)                                              |
| `LOG_LEVEL`                | `INFO` for prod, `DEBUG` for troubleshooting                       |
| `JOB_TIMEOUT_SECONDS`      | `30` (keep default)                                                |
| `HEARTBEAT_TIMEOUT_SECONDS`| `15` (keep default)                                                |

Verify permissions:

```bash
stat -c '%U %G %a' /etc/sltp-tg-bot/sltp-tg-bot.env   # expect: root sltpbot 640
```

### 4.6 Initialize the database

```bash
cd /opt/sltp-tg-bot
sudo -u sltpbot ./venv/bin/python -m sltp_tg_bot.scripts.init_db
```

This creates `sltp.db`, applies schema, and seeds the admin row from `ADMIN_USER_ID`. Re-running is safe (idempotent).

### 4.7 Install the systemd unit

The project ships a ready-to-use unit at `/opt/sltp-tg-bot/systemd/sltp-tg-bot.service`.

```bash
install -o root -g root -m 0644 \
  /opt/sltp-tg-bot/systemd/sltp-tg-bot.service \
  /etc/systemd/system/sltp-tg-bot.service
systemctl daemon-reload
systemctl enable --now sltp-tg-bot.service
systemctl status sltp-tg-bot.service
```

Expected final line: `Active: active (running)`.

### 4.8 Smoke test

```bash
# Internal health check (nginx not up yet).
curl -fsS http://127.0.0.1:8080/healthz && echo OK
# Expect: 200 and {"status":"ok","db":true,"telegram":true}
```

Next, bring up nginx + TLS.

---

## 5. Reverse proxy & TLS

### 5.1 Install nginx + certbot

```bash
apt install -y nginx
# Certbot via snap is the current DO-recommended path on Ubuntu 22.04.
apt install -y snapd
snap install core; snap refresh core
snap install --classic certbot
ln -sf /snap/bin/certbot /usr/bin/certbot
```

### 5.2 Deploy the site config

```bash
install -o root -g root -m 0644 \
  /opt/sltp-tg-bot/nginx/sltp-tg-bot.conf \
  /etc/nginx/sites-available/sltp-tg-bot.conf

# IMPORTANT: replace 'bot.example.com' with your real hostname in both
# server_name lines and both ssl_certificate paths.
sed -i 's/bot\.example\.com/bot.yourdomain.com/g' \
       /etc/nginx/sites-available/sltp-tg-bot.conf

ln -sf /etc/nginx/sites-available/sltp-tg-bot.conf \
       /etc/nginx/sites-enabled/sltp-tg-bot.conf

# Drop the default site so :443 on other hostnames 444s out.
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
```

### 5.3 Obtain TLS cert & wire it in

> **DDNS users:** if your hostname is a DuckDNS / No-IP subdomain, use the **HTTP-01 webroot** flow documented in **§17.3** instead of the `--nginx` plugin shown here — same end result, but it sidesteps a couple of edge cases with hostname-validation on free DDNS providers.

```bash
certbot --nginx -d bot.yourdomain.com \
        --non-interactive --agree-tos -m ops@yourdomain.com \
        --redirect --hsts --staple-ocsp
nginx -t && systemctl reload nginx

# Verify the renewal timer is scheduled.
systemctl list-timers | grep certbot
#   expect: 'snap.certbot.renew.timer' or 'certbot.timer' loaded and next-run set

# Dry-run renewal end-to-end.
certbot renew --dry-run
```

### 5.4 Verify security headers

```bash
curl -sI https://bot.yourdomain.com/healthz | grep -iE 'strict-transport|x-frame|x-content-type'
```

Expect `Strict-Transport-Security`, `X-Frame-Options: DENY`, and `X-Content-Type-Options: nosniff` — all set by the packaged nginx config.

---

## 6. Operational runbooks

Ten copy-paste procedures every on-call engineer should be able to run.

### 6.1 Start / stop / restart / status

```bash
systemctl start   sltp-tg-bot
systemctl stop    sltp-tg-bot
systemctl restart sltp-tg-bot
systemctl status  sltp-tg-bot
```

### 6.2 View live logs

```bash
# Service journal, follow mode.
journalctl -u sltp-tg-bot -f

# Last 15 minutes only.
journalctl -u sltp-tg-bot --since '15 min ago'

# Backup / cron logs.
tail -F /var/log/sltp-tg-bot/backup.log
```

### 6.3 View nginx logs

```bash
tail -F /var/log/nginx/access.log /var/log/nginx/error.log

# Count per-status codes for the last 10k requests.
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn
```

### 6.4 Rotate an EA token

The project ships `scripts/rotate_token.py` (CLI admin tool). Use this if an EA token is suspected compromised.

```bash
sudo -u sltpbot /opt/sltp-tg-bot/venv/bin/python \
     /opt/sltp-tg-bot/scripts/rotate_token.py \
     --login 12345678
# Prints the NEW token on stdout exactly once — hand it to the EA operator
# (the trader pastes it into InpBridgeAccountToken and reloads the EA).
```

Old token is invalidated atomically; any in-flight request continues to its result then stops.

### 6.5 Add a new MT5 account (CLI fallback)

Normally the trader does this from Telegram (Settings → Accounts → Add Account). If Telegram is unreachable:

```bash
sudo -u sltpbot /opt/sltp-tg-bot/venv/bin/python \
     /opt/sltp-tg-bot/scripts/rotate_token.py \
     --create --login 12345678 --server 'IS6FX-Live' --label 'VPS-1'
# Prints newly-issued token; insert into EA.
```

### 6.6 Pause / unpause a team member

```bash
sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db <<'SQL'
UPDATE team_members SET paused = 1 WHERE user_id = 987654321;
SQL
# Unpause:
sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
  "UPDATE team_members SET paused = 0 WHERE user_id = 987654321;"
```

Paused members are rejected at the handler layer with a localized "account paused" reply.

### 6.7 Take an ad-hoc backup

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
    ".backup /var/backups/sltp-tg-bot/sltp-$STAMP.db"
chmod 0640 /var/backups/sltp-tg-bot/sltp-$STAMP.db
ls -lh /var/backups/sltp-tg-bot/ | tail
```

`.backup` is online-safe — it does not block writers.

### 6.8 Restore from backup

```bash
systemctl stop sltp-tg-bot
cp /var/lib/sltp-tg-bot/sltp.db /var/lib/sltp-tg-bot/sltp.db.pre-restore
cp /var/backups/sltp-tg-bot/sltp-20260505T021500Z.db \
   /var/lib/sltp-tg-bot/sltp.db
chown sltpbot:sltpbot /var/lib/sltp-tg-bot/sltp.db
chmod 0640 /var/lib/sltp-tg-bot/sltp.db
systemctl start sltp-tg-bot
journalctl -u sltp-tg-bot -n 20
```

### 6.9 Upgrade procedure (with ~30s downtime)

See §12 for zero-downtime variant with in-flight job draining.

### 6.10 Rollback procedure

```bash
# Assuming you kept the previous checkout at /opt/sltp-tg-bot.prev:
systemctl stop sltp-tg-bot
mv /opt/sltp-tg-bot       /opt/sltp-tg-bot.broken-$(date +%s)
mv /opt/sltp-tg-bot.prev  /opt/sltp-tg-bot
# Restore DB if migrations changed schema (use the pre-upgrade backup).
cp /var/backups/sltp-tg-bot/sltp-preupgrade.db /var/lib/sltp-tg-bot/sltp.db
chown sltpbot:sltpbot /var/lib/sltp-tg-bot/sltp.db
systemctl start sltp-tg-bot
journalctl -u sltp-tg-bot -n 50
```

---

## 7. Monitoring

### 7.1 systemd watchdog

The shipped unit uses `Restart=on-failure` with `RestartSec=5s`. To page on repeated restarts, drop this override in:

```bash
cat >/etc/systemd/system/sltp-tg-bot.service.d/onfailure.conf <<'EOF'
[Unit]
OnFailure=sltp-tg-bot-onfailure.service

[Service]
StartLimitIntervalSec=300
StartLimitBurst=3
EOF
cat >/etc/systemd/system/sltp-tg-bot-onfailure.service <<'EOF'
[Unit]
Description=Email on sltp-tg-bot repeated failures

[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/bin/mailx -s "[sltp-tg-bot] repeated failure on %H" ops@yourdomain.com </dev/null'
EOF
systemctl daemon-reload
```

Requires `mailx` (`apt install -y bsd-mailx`) and a working MTA or relay.

### 7.2 Journal-based alerts (cheap)

```bash
# Watch for ERROR lines and page via a webhook.
journalctl -u sltp-tg-bot -o cat -f | \
  grep --line-buffered -E 'ERROR|CRITICAL' | \
  while read line; do
    curl -fsS -X POST -d "text=[sltp-tg-bot] $line" https://hooks.slack.com/... ;
  done &
```

Run under a tiny systemd unit if you want it managed.

### 7.3 Health check endpoint

```bash
curl -fsS https://bot.yourdomain.com/healthz
# 200  {"status":"ok","db":true,"telegram":true,"uptime_s":1234}
```

External monitoring (UptimeRobot / DO monitor / StatusCake) should poll this URL every 60 s. It returns non-200 when the DB is unreachable or the Telegram long-poll session has died.

### 7.4 Optional: Prometheus exporter (v1.1 roadmap — NOT in v1.0.0)

Planned spec for a future release; no DevOps action needed today.

- Port: `127.0.0.1:9108` (loopback; nginx does NOT expose).
- Metrics: `sltp_bot_up`, `sltp_jobs_total{action,outcome}`, `sltp_jobs_in_flight`, `sltp_heartbeat_age_seconds{login}`, `sltp_webrequest_latency_seconds_bucket{endpoint}`, `sltp_telegram_updates_total`.

---

## 8. Backup strategy

Recommended layering: **Layer 1 (local daily) + Layer 3 (off-site encrypted weekly+monthly rollups)**. Optionally add Layer 2 (DO droplet snapshots) for whole-VM recovery.

### 8.1 Layer 1 — Local daily SQLite snapshots (7-day retention)

```bash
cat >/etc/cron.d/sltp-tg-bot-local-backup <<'EOF'
# m h dom mon dow user command
15 2 * * * sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
    ".backup /var/backups/sltp-tg-bot/sltp-$(date -u +\%Y\%m\%d).db" \
    && find /var/backups/sltp-tg-bot -name 'sltp-*.db' -mtime +7 -delete
EOF
chown root:root /etc/cron.d/sltp-tg-bot-local-backup
chmod 0644     /etc/cron.d/sltp-tg-bot-local-backup
```

Verify tomorrow:

```bash
ls -lh /var/backups/sltp-tg-bot/
grep -i sltp-tg-bot /var/log/syslog | tail
```

### 8.2 Layer 3 — DigitalOcean Spaces nightly upload (encrypted, 7/4/12 retention)

The project ships `/opt/sltp-tg-bot/scripts/backup_to_spaces.sh`. Before you schedule it:

#### 8.2.1 Create a DO Spaces bucket

DO dashboard → Spaces → **Create Spaces Bucket**:
- Region: nearest to your droplet (e.g. `sgp1` for Singapore).
- Name: `sltp-tg-bot-backups` (must be globally unique — prefix with your org if taken).
- Restrict file listing: **Yes** (private).

#### 8.2.2 Create access keys

DO dashboard → API → **Spaces Keys** → Generate → copy **Access Key** + **Secret Key**. These are write-only in effect because the bucket is private.

#### 8.2.3 Install `s3cmd` + GPG + configure

```bash
apt install -y s3cmd gnupg
install -o root -g root -m 0640 /dev/null /etc/sltp-tg-bot/s3cfg
# Adapt this minimal config (region, endpoint, keys):
cat >/etc/sltp-tg-bot/s3cfg <<'EOF'
[default]
host_base          = sgp1.digitaloceanspaces.com
host_bucket        = %(bucket)s.sgp1.digitaloceanspaces.com
access_key         = DO-ACCESS-KEY-REPLACEME
secret_key         = DO-SECRET-KEY-REPLACEME
use_https          = True
signature_v2       = False
EOF
```

#### 8.2.4 Create the GPG encryption passphrase

```bash
umask 077
openssl rand -base64 48 > /etc/sltp-tg-bot/backup.key
chown root:root /etc/sltp-tg-bot/backup.key
chmod 0400      /etc/sltp-tg-bot/backup.key

# STORE A COPY OUT-OF-BAND (1Password, encrypted USB, printed in a safe).
# If this key is lost, backups are unrecoverable.
```

#### 8.2.5 Schedule the upload

```bash
cat >/etc/cron.d/sltp-tg-bot-spaces-backup <<'EOF'
# Daily off-site encrypted backup to DO Spaces.
# Rotation: 7 daily / 4 weekly / 12 monthly (handled inside the script).
30 2 * * * root /opt/sltp-tg-bot/scripts/backup_to_spaces.sh
EOF
chmod 0644 /etc/cron.d/sltp-tg-bot-spaces-backup
```

First run (manual, to prove the path works):

```bash
/opt/sltp-tg-bot/scripts/backup_to_spaces.sh
tail -40 /var/log/sltp-tg-bot/backup.log
s3cmd -c /etc/sltp-tg-bot/s3cfg ls s3://sltp-tg-bot-backups/
```

Retention classes (as implemented in the script):

| Class   | Window        | Trigger                    | Example file             |
|---------|---------------|----------------------------|--------------------------|
| daily   | last 7 days   | every night                | `daily/sltp-20260505.db.gpg` |
| weekly  | last 4 weeks  | Sundays (DOW 7)            | `weekly/sltp-20260505.db.gpg` |
| monthly | last 12 months| first day of month (DOM 01)| `monthly/sltp-20260501.db.gpg` |

### 8.3 Layer 2 (optional) — DO droplet backups

DO dashboard → your droplet → **Backups** → **Enable**. Weekly snapshots, kept 4 weeks, costs ~20% of droplet price. Covers hardware loss but **not** application-level corruption (use Layer 1/3 for that).

### 8.4 Restore from Spaces

```bash
s3cmd -c /etc/sltp-tg-bot/s3cfg get \
      s3://sltp-tg-bot-backups/daily/sltp-20260505.db.gpg /tmp/
gpg --batch --passphrase-file /etc/sltp-tg-bot/backup.key \
    -d /tmp/sltp-20260505.db.gpg > /tmp/sltp-20260505.db
# Then follow §6.8 to swap it in.
```

---

## 9. Disaster recovery scenarios

### Scenario A — DB corruption

**Symptoms:** service keeps restarting; journal shows `sqlite3.DatabaseError: database disk image is malformed`.

```bash
systemctl stop sltp-tg-bot
cp /var/lib/sltp-tg-bot/sltp.db /var/lib/sltp-tg-bot/sltp.db.corrupt
LATEST=$(ls -t /var/backups/sltp-tg-bot/*.db | head -1)
cp "$LATEST" /var/lib/sltp-tg-bot/sltp.db
chown sltpbot:sltpbot /var/lib/sltp-tg-bot/sltp.db
chmod 0640            /var/lib/sltp-tg-bot/sltp.db
systemctl start sltp-tg-bot
journalctl -u sltp-tg-bot -n 50
```

Notify the trader: any EA job or team action issued in the window between the backup and the corruption is lost. Audit log (Appendix D) will show the gap.

### Scenario B — Droplet lost (hardware / region outage)

1. Spin up a new droplet in a **different** region (DO dashboard).
2. Complete §3 + §4.1–§4.5 (hardening + Python + user + dirs + env).
3. Pull the newest Spaces backup:

   ```bash
   apt install -y s3cmd gnupg
   mkdir -p /tmp/restore
   s3cmd -c /etc/sltp-tg-bot/s3cfg ls s3://sltp-tg-bot-backups/daily/
   s3cmd -c /etc/sltp-tg-bot/s3cfg get \
       s3://sltp-tg-bot-backups/daily/sltp-<newest>.db.gpg /tmp/restore/
   gpg --batch --passphrase-file /etc/sltp-tg-bot/backup.key \
       -d /tmp/restore/*.gpg > /var/lib/sltp-tg-bot/sltp.db
   chown sltpbot:sltpbot /var/lib/sltp-tg-bot/sltp.db
   ```

4. Finish §4.7–§4.8 and §5.
5. Update DNS: point `bot.yourdomain.com` at the new IP. TTL-bounded delay.
6. EAs will reconnect automatically on the next heartbeat (within `InpBridgeHeartbeatSec`, default 30 s).

### Scenario C — EA token compromise

```bash
# Rotate the suspect token.
sudo -u sltpbot /opt/sltp-tg-bot/venv/bin/python \
     /opt/sltp-tg-bot/scripts/rotate_token.py --login 12345678
# Notify the EA operator (Thanh) via Telegram and have them paste the new
# token into InpBridgeAccountToken and redeploy the EA.
```

Past jobs with the old token stay in the audit log; any request still in flight gets 401.

### Scenario D — Bot token compromise (the BotFather one)

1. In Telegram, DM `@BotFather`: `/revoke` → pick the bot → confirm.
2. `/token` on the same bot to mint a new one.
3. Update `/etc/sltp-tg-bot/sltp-tg-bot.env` → `BOT_TOKEN=<new>`.
4. `systemctl restart sltp-tg-bot`.
5. All active Telegram chat sessions keep working (the chat IDs are unchanged); nothing on the EA side needs touching.

---

## 10. Security checklist (pre-launch)

Run this list the day before letting real trades through the bot.

- [ ] UFW enabled with `default deny incoming` and ONLY `22/80/443` allowed.
- [ ] `PasswordAuthentication no` in `/etc/ssh/sshd_config` (key-only).
- [ ] `fail2ban` active with `sshd` jail.
- [ ] `certbot` renewal timer scheduled (`systemctl list-timers | grep certbot`).
- [ ] HSTS + `X-Frame-Options: DENY` + `X-Content-Type-Options: nosniff` present in response headers.
- [ ] `/etc/sltp-tg-bot/sltp-tg-bot.env` is `0640 root:sltpbot`; no other file in `/etc/sltp-tg-bot/` world-readable.
- [ ] `/var/lib/sltp-tg-bot/sltp.db` is `0640 sltpbot:sltpbot`.
- [ ] `systemctl show sltp-tg-bot | grep -E 'User=|NoNewPrivileges='` → `User=sltpbot` and `NoNewPrivileges=yes`.
- [ ] Local + off-site backup tested by **restoring** to a disposable droplet and verifying `/healthz` returns 200.
- [ ] `ADMIN_USER_ID` in `.env` matches the trader's real Telegram ID (not a typo).
- [ ] BotFather token regenerated AFTER initial setup so no earlier test copy remains valid.
- [ ] Per-IP AND per-token nginx rate limits active (`limit_req zone=...` in `sltp-tg-bot.conf`).

---

## 11. Troubleshooting matrix

| Symptom                                        | Check                                                        | Fix                                                                         |
|-----------------------------------------------|--------------------------------------------------------------|-----------------------------------------------------------------------------|
| Service won't start                            | `journalctl -u sltp-tg-bot -n 80`                            | Missing/bad `.env`, DB perms, port 8080 in use. `ss -lntp \| grep 8080`.    |
| `sqlite3.OperationalError: attempt to write a readonly database` | DB file ownership                                    | `chown sltpbot:sltpbot /var/lib/sltp-tg-bot/sltp.db; chmod 0640 …`          |
| EA can't connect (401)                         | `tail -F /var/log/nginx/access.log` for `401`                | Token revoked or pasted wrong. Rotate (§6.4), paste again.                  |
| EA can't connect (network)                     | `curl -fsS https://bot.yourdomain.com/healthz` from VPS      | MT5 allowlist missing the URL (err 4006). Add via Tools→Options→EA.          |
| TLS handshake fails                            | `openssl s_client -connect bot.yourdomain.com:443`           | Cert path in nginx conf wrong, or certbot renewal failed. `certbot renew`.  |
| Cert renewal failed                            | `tail /var/log/letsencrypt/letsencrypt.log`                  | Port 80 blocked or DNS wrong. UFW allow 80; check A record.                  |
| Cert issuance failed on DDNS hostname          | `tail /var/log/letsencrypt/letsencrypt.log` — look for `unauthorized` or `dns problem` | DDNS update didn't propagate yet (`dig +short <host>` from the droplet); free DDNS provider rate-limited; or duckdns.org token wrong. Retry after 5 min, or switch to webroot flow per §17.3.                  |
| DB locked (rare, under heavy load)             | `sqlite3 sltp.db 'pragma busy_timeout=0; select 1;'`         | Kill long-running queries. `pragma wal_checkpoint(truncate);`                |
| Queue stuck (jobs never complete)              | `sqlite3 sltp.db 'SELECT id, action, state, created_at FROM jobs WHERE state="claimed" ORDER BY created_at;'` | `UPDATE jobs SET state="expired" WHERE state="claimed" AND created_at < datetime("now","-5 minutes");` |
| Heartbeats missing                             | `journalctl -u sltp-tg-bot -f \| grep heartbeat`             | EA side: check MT5 is running, URL allowlisted, token correct.               |
| High CPU                                       | `htop` → process tree                                        | Usually Telegram long-poll in retry loop — check network outbound.           |
| Out of disk (logs)                             | `df -h /var`                                                 | `journalctl --vacuum-size=200M`. Add `/etc/systemd/journald.conf` retention. |

---

## 12. Upgrade procedure (zero-downtime where possible)

Inbound HTTP will experience a **pause of ~5–30 seconds** while the service restarts. EAs auto-retry (long-poll reconnect), so users typically see no impact. To fully avoid mid-flight job loss:

```bash
# 1. Flip maintenance flag (rejects NEW jobs; existing ones finish).
sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
     "INSERT OR REPLACE INTO settings (key, value) VALUES ('maintenance','1');"

# 2. Wait for in-flight jobs to drain (typical: < 1 minute).
watch -n 2 "sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
     'SELECT COUNT(*) FROM jobs WHERE state=\"claimed\";'"
# When the count hits 0, proceed.

# 3. Pre-upgrade backup.
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
     ".backup /var/backups/sltp-tg-bot/sltp-preupgrade-$STAMP.db"

# 4. Keep the current code for rollback, deploy new.
mv /opt/sltp-tg-bot /opt/sltp-tg-bot.prev
sudo -u sltpbot git clone https://github.com/YOURORG/sltp-tg-bot.git /opt/sltp-tg-bot
cd /opt/sltp-tg-bot
sudo -u sltpbot git checkout v1.1.0          # new version tag
sudo -u sltpbot python3.11 -m venv venv
sudo -u sltpbot ./venv/bin/pip install --upgrade pip
sudo -u sltpbot ./venv/bin/pip install -e .

# 5. Apply DB migrations (if the release has them).
sudo -u sltpbot ./venv/bin/python -m sltp_tg_bot.scripts.migrate

# 6. Restart.
systemctl restart sltp-tg-bot
journalctl -u sltp-tg-bot -n 30

# 7. Clear maintenance flag.
sudo -u sltpbot sqlite3 /var/lib/sltp-tg-bot/sltp.db \
     "DELETE FROM settings WHERE key='maintenance';"

# 8. Verify EAs reconnect (heartbeats arriving).
journalctl -u sltp-tg-bot -f | grep heartbeat
```

Rollback: see §6.10.

---

## 13. Appendix A — Native config reference

### 13.1 File paths

| Path                                         | What it is                                    |
|----------------------------------------------|-----------------------------------------------|
| `/opt/sltp-tg-bot/`                          | Code checkout + `venv/`                       |
| `/opt/sltp-tg-bot/systemd/sltp-tg-bot.service` | Ships the systemd unit (copy into `/etc/systemd/system/`) |
| `/opt/sltp-tg-bot/nginx/sltp-tg-bot.conf`    | Ships the nginx config (copy into `sites-available`) |
| `/opt/sltp-tg-bot/scripts/backup_to_spaces.sh` | Nightly off-site backup script              |
| `/opt/sltp-tg-bot/scripts/init_db.py`        | One-shot DB initializer                       |
| `/opt/sltp-tg-bot/scripts/rotate_token.py`   | Token rotation CLI                            |
| `/etc/sltp-tg-bot/sltp-tg-bot.env`           | Runtime `.env` (systemd `EnvironmentFile`)    |
| `/etc/sltp-tg-bot/s3cfg`                     | `s3cmd` config for DO Spaces                  |
| `/etc/sltp-tg-bot/backup.key`                | GPG passphrase (0400 root)                    |
| `/var/lib/sltp-tg-bot/sltp.db`               | SQLite DB                                     |
| `/var/log/sltp-tg-bot/`                      | Ad-hoc log dir (backup script writes here)    |
| `/var/backups/sltp-tg-bot/`                  | Local daily snapshots                         |
| `/etc/systemd/system/sltp-tg-bot.service`    | Installed systemd unit                        |
| `/etc/nginx/sites-available/sltp-tg-bot.conf`| nginx site config                             |

### 13.2 systemd unit (annotated)

```ini
[Unit]
Description=SLTP Telegram Bot (sltp-tg-bot)
Documentation=https://t.me/thanhglobalist
After=network-online.target
Wants=network-online.target

[Service]
Type=simple                                              # main process IS the service
User=sltpbot                                             # drop privileges
Group=sltpbot
WorkingDirectory=/opt/sltp-tg-bot
EnvironmentFile=/etc/sltp-tg-bot/sltp-tg-bot.env         # BOT_TOKEN etc.
ExecStart=/opt/sltp-tg-bot/venv/bin/python -m sltp_tg_bot.main
Restart=on-failure
RestartSec=5s

# ---- Hardening (standard systemd sandboxing; tune to your threat model) ----
NoNewPrivileges=true
ProtectSystem=strict          # /usr, /boot, /etc are read-only
ProtectHome=true              # /home, /root, /run/user hidden
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true

# Writable paths the service actually needs.
ReadWritePaths=/var/lib/sltp-tg-bot /var/log/sltp-tg-bot

[Install]
WantedBy=multi-user.target
```

### 13.3 nginx config (key points)

See `/opt/sltp-tg-bot/nginx/sltp-tg-bot.conf` for the full file. Key snippets:

```nginx
# Per-IP rate limit (60 req/min).
limit_req_zone $binary_remote_addr zone=sltp_per_ip:10m rate=60r/m;

# Per-token rate limit (hash the Authorization header).
map $http_authorization $sltp_token_key {
    default "";
    "~*^Bearer\s+(.+)$" $1;
}
limit_req_zone $sltp_token_key zone=sltp_per_token:10m rate=60r/m;

server {
    listen 443 ssl http2;
    server_name bot.yourdomain.com;
    # Let's Encrypt paths (certbot --nginx writes these).
    ssl_certificate     /etc/letsencrypt/live/bot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    location / {
        limit_req zone=sltp_per_ip    burst=30 nodelay;
        limit_req zone=sltp_per_token burst=30 nodelay;

        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;

        # Long-poll window on /jobs/next is 25s; give nginx a safe 35s.
        proxy_read_timeout 35s;
        proxy_send_timeout 35s;
    }
}
```

### 13.4 `.env` reference

See `.env.example` (copied verbatim earlier in §4.5). Every key has an inline comment explaining it.

### 13.5 Port map

| Port | Bind      | Protocol | Role                                             |
|------|-----------|----------|--------------------------------------------------|
| 22   | 0.0.0.0   | TCP      | SSH (UFW-allowed, fail2ban-protected)            |
| 80   | 0.0.0.0   | TCP      | HTTP → 301 redirect to HTTPS (and ACME challenge)|
| 443  | 0.0.0.0   | TCP      | HTTPS (nginx, proxies to 127.0.0.1:8080)         |
| 8080 | 127.0.0.1 | TCP      | sltp-tg-bot internal (loopback only)             |

---

## 14. Appendix B — Docker Compose deployment

Alternative to §4 for shops with a CI/CD pipeline that already builds images.

### 14.1 Trade-offs

| When to use native (§4)                       | When to use Docker (this appendix)           |
|-----------------------------------------------|----------------------------------------------|
| Small ops shop, one droplet, copy-paste runbooks. | You already ship other services via Docker. |
| Want `journalctl`, `systemctl` ergonomics.    | CI pipeline pushes tagged images to a registry. |
| Fewest moving parts, easiest rollback.        | You prefer ephemeral nodes + immutable images. |

### 14.2 Dockerfile

Ships at `/opt/sltp-tg-bot/docker/Dockerfile`. Builds a slim Python 3.11 image:

```bash
cd /opt/sltp-tg-bot
docker build -f docker/Dockerfile -t sltp-tg-bot:1.0.0 .
```

### 14.3 docker-compose.yml

Ships at `/opt/sltp-tg-bot/docker/docker-compose.yml`. Minimal shape:

```yaml
services:
  bot:
    image: sltp-tg-bot:1.0.0
    restart: unless-stopped
    env_file: /etc/sltp-tg-bot/sltp-tg-bot.env
    ports:
      - "127.0.0.1:8080:8080"        # loopback only; host nginx fronts TLS
    volumes:
      - /var/lib/sltp-tg-bot:/var/lib/sltp-tg-bot
      - /var/log/sltp-tg-bot:/var/log/sltp-tg-bot
    read_only: true
    tmpfs:
      - /tmp
    cap_drop: [ALL]
    security_opt:
      - no-new-privileges:true
```

### 14.4 Bring it up

```bash
cd /opt/sltp-tg-bot/docker
docker compose up -d
docker compose logs -f bot
```

### 14.5 Reverse-proxy decision

- **Recommended:** keep §5's host nginx; Docker only runs the bot. One fewer moving piece and you reuse the same certbot + UFW path.
- **Alternative:** Traefik as a second container, handling TLS itself. Only sensible if you already run Traefik for other workloads.

### 14.6 Backups under Docker

The SQLite DB lives on the host (bind-mount `/var/lib/sltp-tg-bot`), so §8's cron jobs work unchanged — they don't care that the writer is inside a container.

---

## 15. Appendix C — DigitalOcean specifics

### 15.1 Droplet sizing

| Accounts (MT5 logins) | Team members | Droplet size   | RAM | vCPU | Notes                                                 |
|----------------------:|-------------:|----------------|----:|-----:|-------------------------------------------------------|
|                  1–3 |         1–2 | s-1vcpu-1gb    | 1GB |    1 | Works but SQLite checkpoint can spike memory. NOT recommended for production. |
|                 4–10 |         2–4 | **s-1vcpu-2gb**| 2GB |    1 | Minimum recommended. Matches v1.0.0 profiling.        |
|                11–25 |         4–8 | **s-2vcpu-4gb**| 4GB |    2 | Recommended headroom for peak events.                 |
|                26–75 |        8–16 | s-2vcpu-8gb    | 8GB |    2 | Comfortable; approaching SQLite ceiling.              |
|                 75+  |         16+ | s-4vcpu-8gb+   | 8GB+|    4 | Consider a migration to Postgres (v1.x roadmap).      |

### 15.2 DO Cloud Firewall (alternative to UFW)

If you prefer managed firewall over UFW:

DO dashboard → Networking → Firewalls → **Create Firewall**:

- Inbound: `SSH (22)` from your admin IP only, `HTTP (80)` from any, `HTTPS (443)` from any.
- Outbound: all (required for Telegram + Let's Encrypt + apt).
- Apply to: the sltp-tg-bot droplet.

You can run BOTH UFW and DO firewall; traffic must pass both. Belt-and-braces is fine.

### 15.3 DO Spaces bucket creation

Covered inline in §8.2.1.

### 15.4 DO managed monitoring agent

```bash
curl -sSL https://repos.insights.digitalocean.com/install.sh | bash
systemctl status do-agent
```

Gives you CPU / disk / memory / bandwidth graphs in the DO dashboard and lets you set **DO Alerts** (free) on thresholds.

### 15.5 DNS setup

DO Networking → Domains → **Add Domain** `yourdomain.com` → create an **A record** `bot` → point at the droplet's public IPv4. TTL 3600 is fine. Propagation is usually < 60 s on DO's own DNS.

---

## 16. Appendix D — Audit log spec

### 16.1 Schema

```sql
CREATE TABLE audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_type   TEXT NOT NULL,       -- 'user' | 'ea' | 'system'
    actor_id     TEXT,                 -- tg user_id / ea login / NULL
    account_id   INTEGER,              -- FK accounts.id (nullable)
    action       TEXT NOT NULL,        -- 'close_all' | 'sl' | 'team_add' | ...
    args         TEXT,                 -- JSON blob (normalized)
    result       TEXT,                 -- 'ok' | 'fail' | 'reject'
    ip           TEXT,                 -- source IP (bot requests only)
    lang         TEXT,                 -- caller's language (en/ja/vi)
    notes        TEXT
);
CREATE INDEX idx_audit_ts       ON audit_log(ts);
CREATE INDEX idx_audit_actor    ON audit_log(actor_type, actor_id);
CREATE INDEX idx_audit_account  ON audit_log(account_id);
CREATE INDEX idx_audit_action   ON audit_log(action);
```

### 16.2 Example queries

```sql
-- Everything the trader did in the last 24 hours.
SELECT ts, action, args, result
  FROM audit_log
 WHERE actor_type='user' AND actor_id='123456789'
   AND ts >= datetime('now','-1 day')
 ORDER BY ts DESC;

-- Who sent /panic in the last 30 days?
SELECT ts, actor_id, account_id, ip
  FROM audit_log
 WHERE action='panic'
   AND ts >= datetime('now','-30 days');

-- Daily close-all volume.
SELECT date(ts) AS day, COUNT(*) AS n
  FROM audit_log
 WHERE action='close_all'
 GROUP BY day ORDER BY day DESC
 LIMIT 30;

-- Failures in the last hour (pager candidate).
SELECT ts, action, actor_type, actor_id, notes
  FROM audit_log
 WHERE result='fail' AND ts >= datetime('now','-1 hour');
```

### 16.3 Retention policy

- **Keep:** last **12 months** online, in the same SQLite DB. Size budget: ~10–50 MB/year for a 5-account desk.
- **Archive:** rows older than 12 months are exported nightly to `s3://sltp-tg-bot-backups/audit/YYYY-MM.csv.gpg` by a companion cron (ships in v1.1.0) and then deleted. Suggested cron:

  ```bash
  cat >/etc/cron.d/sltp-tg-bot-audit-archive <<'EOF'
  # Runs 03:00 UTC on the 1st of each month. Requires the v1.1.0 helper.
  0 3 1 * * sltpbot /opt/sltp-tg-bot/venv/bin/python \
      /opt/sltp-tg-bot/scripts/archive_audit.py --older-than-months 12
  EOF
  ```

- **Tamper-evidence:** each row carries an append-only `id` + `ts`; rows are never UPDATEd in place. For stronger guarantees, apply WORM-style replication to an immutable DO Spaces object lock (post-v1.0.0 roadmap).

---

## 17. Appendix E — Free DDNS as a domain alternative

If the operator does not own a domain (or does not want to dedicate one to the bot), a **free dynamic-DNS subdomain** is a fully supported alternative. The result is functionally equivalent to a paid domain for our purposes:

- ✅ Stable hostname (e.g. `bot-thanh.duckdns.org`) that survives droplet IP changes.
- ✅ Let's Encrypt issues real, browser-trusted TLS certs against DDNS subdomains — same 90-day auto-renew flow.
- ✅ No procurement, no annual renewal, no payment information on file.
- ⚠️ Trust shifts to the DDNS provider; if they go down or revoke your hostname, your bot is unreachable until you switch.
- ⚠️ Less professional-looking if the bot ever becomes client-facing — not a concern for an internal trading desk.

**Use Appendix E in place of, not in addition to, the standard `bot.yourdomain.com` setup.** Anywhere this guide says `bot.yourdomain.com`, substitute your DDNS hostname.

### 17.1 Provider choice

We explicitly support two providers, both battle-tested for 10+ years:

| Provider | Free tier | Hostname pattern | Refresh requirement | Notes |
|---|---|---|---|---|
| **DuckDNS** | 5 subdomains, no expiry, no ads | `<name>.duckdns.org` | Update IP every ≤ 60 days (any GET to their endpoint counts) | Recommended. Token-based, scriptable in 3 lines. |
| **No-IP Free** | 1 subdomain, must confirm every 30 days via web link | `<name>.ddns.net` (and others) | Manual confirmation monthly | Acceptable, but the monthly click is operationally annoying — prefer DuckDNS unless you already have an account. |

The rest of this appendix uses **DuckDNS** as the working example. No-IP differs only in the update mechanism (§17.4).

### 17.2 Set up the DDNS hostname (DuckDNS)

1. Open `https://www.duckdns.org` in a browser.
2. Sign in (Google / GitHub / Twitter / Reddit — no email signup needed).
3. On the dashboard, type a hostname into the *subdomain* box (e.g. `bot-thanh`) and click **add domain**. The full hostname is now `bot-thanh.duckdns.org`.
4. Copy the **token** shown at the top of the page (a UUID-like string). Treat it like a password — anyone with it can repoint your hostname.
5. In the *current ip* field for your hostname, paste the droplet's public IPv4 and click **update ip**. (Step 17.4 will then automate this.)

Verify resolution from the droplet itself:

```bash
dig +short bot-thanh.duckdns.org
#   expect: <your droplet's public IPv4>
```

If `dig` returns empty or the wrong IP, **wait 60 seconds and retry** — DuckDNS propagation is fast but not instant.

### 17.3 Issue a Let's Encrypt cert (HTTP-01 webroot flow)

The standard `certbot --nginx -d bot.yourdomain.com` flow from §5.3 *usually* works for DDNS too, but the more reliable variant is the **webroot challenge**: certbot writes a challenge file under nginx's docroot, Let's Encrypt fetches it over HTTP, validates, then issues. This avoids `--nginx`'s automatic config rewriting, which occasionally trips on hostnames it doesn't recognize as a registered TLD.

First, open port 80 if not already open (UFW):

```bash
ufw status | grep '80/tcp' || ufw allow 80/tcp
```

Make sure the bot's nginx site block has a plain HTTP `server` listening on port 80 with a `webroot` location. Add this **above** the HTTPS server block in `/etc/nginx/sites-available/sltp-tg-bot.conf`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name bot-thanh.duckdns.org;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Anything else → force HTTPS once the cert is in place.
    location / { return 301 https://$host$request_uri; }
}
```

Create the webroot and reload nginx:

```bash
mkdir -p /var/www/certbot
chown www-data:www-data /var/www/certbot
nginx -t && systemctl reload nginx
```

Issue the cert:

```bash
certbot certonly --webroot -w /var/www/certbot \
        -d bot-thanh.duckdns.org \
        --non-interactive --agree-tos -m ops@example.com
```

Wire the cert into the HTTPS server block (paths are deterministic):

```nginx
ssl_certificate     /etc/letsencrypt/live/bot-thanh.duckdns.org/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/bot-thanh.duckdns.org/privkey.pem;
```

Reload nginx, verify TLS:

```bash
nginx -t && systemctl reload nginx
curl -fsS https://bot-thanh.duckdns.org/healthz
#   expect: {"status":"ok"}
```

The certbot `snap.certbot.renew.timer` (or `certbot.timer`) will renew automatically every 60 days using the same webroot path. Verify with `certbot renew --dry-run`.

### 17.4 Keep the DDNS record pointing at the right IP

DigitalOcean droplet IPs are usually stable, but **resize / restore-from-snapshot / region-migrate operations can change them**. Run a small cron job that pings DuckDNS every 5 minutes to refresh the record (also satisfies their 60-day dormancy rule):

```bash
DUCKDNS_TOKEN='paste-your-token-here'
DUCKDNS_HOST='bot-thanh'   # the bare subdomain, no .duckdns.org suffix

install -m 700 -o root -g root -d /opt/sltp-tg-bot/ddns
cat >/opt/sltp-tg-bot/ddns/duckdns-update.sh <<EOF
#!/usr/bin/env bash
set -euo pipefail
TOKEN='${DUCKDNS_TOKEN}'
HOST='${DUCKDNS_HOST}'
LOG=/var/log/sltp-tg-bot/ddns.log
mkdir -p "\$(dirname "\$LOG")"
resp=\$(curl -fsS "https://www.duckdns.org/update?domains=\${HOST}&token=\${TOKEN}&ip=")
echo "\$(date -Is) \${resp}" >> "\$LOG"
[[ "\$resp" == "OK" ]]
EOF
chmod 700 /opt/sltp-tg-bot/ddns/duckdns-update.sh

cat >/etc/cron.d/sltp-tg-bot-ddns <<'EOF'
# Refresh DuckDNS every 5 minutes. Logs to /var/log/sltp-tg-bot/ddns.log.
*/5 * * * * root /opt/sltp-tg-bot/ddns/duckdns-update.sh
EOF
chmod 644 /etc/cron.d/sltp-tg-bot-ddns
```

Verify within 10 minutes:

```bash
tail /var/log/sltp-tg-bot/ddns.log
#   expect lines ending in: OK
```

### 17.5 No-IP variant (if you must)

No-IP requires a different update mechanism and a **monthly host-confirmation click** in their web UI. Their official `noip-duc` daemon handles updates:

```bash
apt install -y noip2
noip2 -C        # interactive: enter username, password, choose host
systemctl enable --now noip2
```

Cert issuance follows the same webroot flow as §17.3, just with the No-IP hostname instead. **Set a calendar reminder** for the 30-day confirmation — the host disappears if you miss it, and the cert silently fails renewal at the 90-day mark.

### 17.6 Operator notes on DDNS in production

- **EA WebRequest allowlist:** add the DDNS hostname (with `https://` prefix) to MT5 → Tools → Options → Expert Advisors. The hostname — not the IP — is what's allowlisted, so droplet IP changes don't break it.
- **Bridge URL in the bot's `.env`:** set `BRIDGE_PUBLIC_URL=https://bot-thanh.duckdns.org` so all links the bot generates (e.g. EA token rotation messages) point to the correct hostname.
- **Monitoring:** add a daily check that the DDNS hostname still resolves to the droplet's current IP. Cheap version:

  ```bash
  cat >/etc/cron.daily/sltp-tg-bot-ddns-check <<'EOF'
  #!/usr/bin/env bash
  expected=$(curl -fsS https://ipv4.icanhazip.com)
  actual=$(dig +short bot-thanh.duckdns.org | tail -1)
  if [[ "$expected" != "$actual" ]]; then
      logger -t sltp-tg-bot-ddns "DDNS mismatch: expected=$expected actual=$actual"
      exit 1
  fi
  EOF
  chmod 755 /etc/cron.daily/sltp-tg-bot-ddns-check
  ```

- **Migrating from DDNS to a real domain later:** issue a fresh cert for the new domain (§5.3), update `BRIDGE_PUBLIC_URL`, change `server_name` in nginx, allowlist the new URL in every EA, then retire the DDNS record. No data migration needed — the bot is hostname-agnostic internally.

### 17.7 Why raw IPs are still not supported

For reference, here's why the prerequisites table forbids `http://203.0.113.45` style URLs even though the EA's `WebRequest` would technically accept them:

1. **No TLS path:** Let's Encrypt does not issue certs for IPs. ZeroSSL / Buypass have paid IP-cert tiers, but they're not browser-trusted by all clients out of the box. Self-signed certs get rejected by MT5's `WebRequest` (err 4015 / 4060).
2. **Plaintext token:** without TLS, every `Authorization: Bearer <token>` header crosses the public internet readable. A passive observer at any ISP hop can hijack the EA token and issue arbitrary trading commands.
3. **Operationally fragile:** any droplet operation that changes the IP requires touching every Windows VPS to update both the EA inputs *and* the WebRequest allowlist. This does not scale beyond 2–3 accounts.

If you need a deployment for **local testing only** (e.g. on a LAN where you trust the network), raw IP + plain HTTP works — set `InpBridgeUrl=http://<ip>:8080` and skip nginx. Never do this with a real broker account.

---

*End of DevOps Guide v1.0.1. For the trader-facing doc, see `BulkSLTPUpdater_EA/README_v1.3.0_2026-05-05.md`.*

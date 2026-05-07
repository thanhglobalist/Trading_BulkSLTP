#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# sltp-tg-bot — daily SQLite snapshot, encrypt, upload to DigitalOcean Spaces.
# Author: Thanh Nguyen <thanhglobalist@gmail.com>
#
# Cron example (run as root):
#   15 2 * * * /opt/sltp-tg-bot/scripts/backup_to_spaces.sh
#
# Required tools: sqlite3, gpg, s3cmd
# Required files:
#   /etc/sltp-tg-bot/backup.key      — passphrase for symmetric encryption
#   /etc/sltp-tg-bot/s3cfg           — s3cmd config pointing at DO Spaces
#
# Retention: 7 daily, 4 weekly, 12 monthly.
# Logs to /var/log/sltp-tg-bot/backup.log
# ----------------------------------------------------------------------------
set -euo pipefail

DB_PATH="${DB_PATH:-/var/lib/sltp-tg-bot/sltp.db}"
BUCKET="${BACKUP_BUCKET:-s3://sltp-tg-bot-backups}"
KEY_FILE="${BACKUP_KEY:-/etc/sltp-tg-bot/backup.key}"
S3CFG="${S3CFG:-/etc/sltp-tg-bot/s3cfg}"
LOG="/var/log/sltp-tg-bot/backup.log"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "[$(date -Iseconds)] backup starting"

if [[ ! -r "$DB_PATH" ]]; then
  echo "ERROR: cannot read $DB_PATH"; exit 1
fi
if [[ ! -r "$KEY_FILE" ]]; then
  echo "ERROR: cannot read $KEY_FILE"; exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DOW="$(date -u +%u)"   # 1..7
DOM="$(date -u +%d)"

SNAP="$WORK/sltp-${STAMP}.db"
ENC="$WORK/sltp-${STAMP}.db.gpg"

# 1. Atomic snapshot
sqlite3 "$DB_PATH" ".backup '$SNAP'"
echo "snapshot taken: $(stat -c%s "$SNAP") bytes"

# 2. Encrypt (symmetric, AES-256)
gpg --batch --yes \
    --passphrase-file "$KEY_FILE" \
    --cipher-algo AES256 \
    --symmetric \
    --output "$ENC" "$SNAP"

# 3. Upload daily
s3cmd --config="$S3CFG" put "$ENC" "$BUCKET/daily/sltp-${STAMP}.db.gpg"
echo "uploaded daily"

# 4. Promote on Sundays → weekly
if [[ "$DOW" == "7" ]]; then
  s3cmd --config="$S3CFG" cp \
    "$BUCKET/daily/sltp-${STAMP}.db.gpg" \
    "$BUCKET/weekly/sltp-${STAMP}.db.gpg"
  echo "promoted to weekly"
fi

# 5. Promote on the 1st of the month → monthly
if [[ "$DOM" == "01" ]]; then
  s3cmd --config="$S3CFG" cp \
    "$BUCKET/daily/sltp-${STAMP}.db.gpg" \
    "$BUCKET/monthly/sltp-${STAMP}.db.gpg"
  echo "promoted to monthly"
fi

# 6. Retention prune (using `s3cmd ls` + age check)
prune() {
  local prefix="$1" keep_days="$2"
  s3cmd --config="$S3CFG" ls "$BUCKET/$prefix/" | while read -r line; do
    file_date=$(awk '{print $1}' <<< "$line")
    file_url=$(awk '{print $4}' <<< "$line")
    [[ -z "$file_url" ]] && continue
    if [[ -n "$file_date" ]]; then
      age=$(( ( $(date -u +%s) - $(date -d "$file_date" +%s) ) / 86400 ))
      if (( age > keep_days )); then
        echo "pruning $file_url (age=${age}d)"
        s3cmd --config="$S3CFG" rm "$file_url"
      fi
    fi
  done
}

prune "daily"   7
prune "weekly"  28
prune "monthly" 365

echo "[$(date -Iseconds)] backup done"

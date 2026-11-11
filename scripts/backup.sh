#!/bin/sh
# Runs inside the `backup` compose service: one compressed dump per day, 14 days kept.
# Restore: gunzip -c backups/aaroh-YYYY-MM-DD-HHMM.sql.gz | docker compose exec -T db psql -U aaroh aaroh
set -eu
KEEP_DAYS="${KEEP_DAYS:-14}"
while true; do
  STAMP=$(date +%F-%H%M)
  pg_dump -h db -U aaroh aaroh | gzip > "/backups/aaroh-${STAMP}.sql.gz"
  echo "backup written: aaroh-${STAMP}.sql.gz"
  find /backups -maxdepth 1 -name 'aaroh-*.sql.gz' -mtime +"${KEEP_DAYS}" -exec rm -f {} \;
  sleep 86400
done

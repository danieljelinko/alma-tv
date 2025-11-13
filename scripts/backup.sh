#!/bin/bash
# Backup script for Alma TV database and configuration

set -euo pipefail

BACKUP_DIR="/var/backups/alma"
DB_PATH="/var/lib/alma/alma.db"
CONFIG_DIR="/opt/alma-tv"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="alma_backup_${TIMESTAMP}"

echo "=== Alma TV Backup Script ==="
echo "Starting backup at $(date)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup subdirectory
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "$BACKUP_PATH"

# Backup database
if [ -f "$DB_PATH" ]; then
    echo "Backing up database..."
    sqlite3 "$DB_PATH" ".backup '${BACKUP_PATH}/alma.db'"
    sqlite3 "$DB_PATH" ".dump" > "${BACKUP_PATH}/alma_dump.sql"
    echo "Database backed up"
else
    echo "WARNING: Database not found at $DB_PATH"
fi

# Backup configuration
if [ -f "${CONFIG_DIR}/.env" ]; then
    echo "Backing up configuration..."
    cp "${CONFIG_DIR}/.env" "${BACKUP_PATH}/.env"
    echo "Configuration backed up"
fi

# Compress backup
echo "Compressing backup..."
tar -czf "${BACKUP_PATH}.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
rm -rf "$BACKUP_PATH"

# Validate backup
if tar -tzf "${BACKUP_PATH}.tar.gz" > /dev/null; then
    echo "Backup validated successfully"
else
    echo "ERROR: Backup validation failed"
    exit 1
fi

# Clean up old backups (keep last 30 days)
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "alma_backup_*.tar.gz" -mtime +30 -delete

BACKUP_SIZE=$(du -h "${BACKUP_PATH}.tar.gz" | cut -f1)
echo "Backup completed: ${BACKUP_PATH}.tar.gz (${BACKUP_SIZE})"
echo "Backup count: $(ls -1 ${BACKUP_DIR}/alma_backup_*.tar.gz | wc -l)"

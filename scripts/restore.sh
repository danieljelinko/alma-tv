#!/bin/bash
# Restore script for Alma TV database and configuration

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /var/backups/alma/alma_backup_*.tar.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
DB_PATH="/var/lib/alma/alma.db"
CONFIG_DIR="/opt/alma-tv"

echo "=== Alma TV Restore Script ==="
echo "Restoring from: $BACKUP_FILE"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Extract backup
TEMP_DIR=$(mktemp -d)
echo "Extracting backup to $TEMP_DIR..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
EXTRACTED_PATH="${TEMP_DIR}/${BACKUP_NAME}"

# Stop services
echo "Stopping Alma TV services..."
sudo systemctl stop alma-playback.service alma-clock.service alma-feedback.service 2>/dev/null || true

# Backup current database (just in case)
if [ -f "$DB_PATH" ]; then
    echo "Backing up current database..."
    cp "$DB_PATH" "${DB_PATH}.pre-restore"
fi

# Restore database
if [ -f "${EXTRACTED_PATH}/alma.db" ]; then
    echo "Restoring database..."
    cp "${EXTRACTED_PATH}/alma.db" "$DB_PATH"

    # Validate database
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
        echo "Database restored and validated"
    else
        echo "ERROR: Database validation failed"
        # Restore pre-restore backup
        if [ -f "${DB_PATH}.pre-restore" ]; then
            mv "${DB_PATH}.pre-restore" "$DB_PATH"
        fi
        rm -rf "$TEMP_DIR"
        exit 1
    fi
else
    echo "WARNING: No database found in backup"
fi

# Restore configuration
if [ -f "${EXTRACTED_PATH}/.env" ]; then
    echo "Restoring configuration..."
    cp "${EXTRACTED_PATH}/.env" "${CONFIG_DIR}/.env"
    echo "Configuration restored"
fi

# Cleanup
rm -rf "$TEMP_DIR"
rm -f "${DB_PATH}.pre-restore"

# Restart services
echo "Starting Alma TV services..."
sudo systemctl start alma-playback.service alma-clock.service alma-feedback.service

echo "Restore completed successfully"

# Alma TV Installation Guide

This guide covers installing and configuring Alma TV on a Raspberry Pi or Linux system.

## Prerequisites

- Raspberry Pi 4 (4GB+ recommended) or Linux system
- Raspberry Pi OS (64-bit) or Ubuntu 20.04+
- Python 3.11 or higher
- FFmpeg
- 500MB+ free disk space (plus space for media library)

## Installation Steps

### 1. System Setup

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y python3.11 python3.11-venv python3-pip ffmpeg vlc git sqlite3

# Create alma user (optional but recommended)
sudo useradd -r -m -d /opt/alma-tv -s /bin/bash alma
sudo usermod -aG video,audio alma
```

### 2. Install Alma TV

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/your-org/alma-tv.git
sudo chown -R alma:alma alma-tv
cd alma-tv

# Switch to alma user
sudo -u alma bash

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install package
pip install --upgrade pip
pip install -e .
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Key settings to configure:

- `ALMA_MEDIA_ROOT` - Path to your media library
- `ALMA_INTRO_PATH` - Path to intro video
- `ALMA_OUTRO_PATH` - Path to outro video
- `ALMA_START_TIME` - Daily start time (default: 19:00)
- `ALMA_DATABASE_URL` - Database path (default: sqlite:///var/lib/alma/alma.db)

### 4. Create Required Directories

```bash
# Create data directories
sudo mkdir -p /var/lib/alma /var/log/alma /var/cache/alma /var/backups/alma
sudo chown -R alma:alma /var/lib/alma /var/log/alma /var/cache/alma /var/backups/alma
```

### 5. Initialize Database

```bash
# Activate environment
source /opt/alma-tv/.venv/bin/activate

# Initialize database
alma config show

# Scan media library
alma library scan /path/to/your/media
```

### 6. Install Systemd Services

```bash
# Copy service files
sudo cp /opt/alma-tv/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable alma-playback.service
sudo systemctl enable alma-clock.service
sudo systemctl enable alma-feedback.service

# Start services
sudo systemctl start alma-playback.service
sudo systemctl start alma-clock.service
sudo systemctl start alma-feedback.service

# Check status
sudo systemctl status alma-playback.service
sudo systemctl status alma-clock.service
sudo systemctl status alma-feedback.service
```

### 7. Configure Log Rotation

```bash
# Install logrotate configuration
sudo cp /opt/alma-tv/scripts/logrotate.conf /etc/logrotate.d/alma
```

### 8. Set Up Automated Backups

```bash
# Add cron job for daily backups
sudo crontab -e

# Add this line (runs backup at 2 AM daily)
0 2 * * * /opt/alma-tv/scripts/backup.sh >> /var/log/alma/backup.log 2>&1
```

## Verification

### Test Configuration

```bash
# Show configuration
alma config show

# List media library
alma library list

# Generate test schedule
alma schedule generate $(date +%Y-%m-%d)
alma schedule show

# Test clock rendering
alma clock test
```

### Test Playback (Dry Run)

```bash
# Set dry run mode in .env
echo "ALMA_DRY_RUN=true" >> /opt/alma-tv/.env

# Test playback
alma playback run
```

### Test Feedback UI

```bash
# Start feedback UI
alma feedback ui

# Open in browser
# http://raspberry-pi-ip:8080
```

## Troubleshooting

### Check Service Logs

```bash
# Playback logs
sudo journalctl -u alma-playback.service -f

# Clock logs
sudo journalctl -u alma-clock.service -f

# Feedback logs
sudo journalctl -u alma-feedback.service -f

# Application logs
tail -f /var/log/alma/alma.log
```

### Common Issues

**No media found:**
- Check `ALMA_MEDIA_ROOT` path in `.env`
- Verify file permissions
- Run `alma library scan` to force rescan

**Playback not starting:**
- Verify `ALMA_START_TIME` in `.env`
- Check playback service status
- Review logs for errors

**Clock not displaying:**
- Ensure X11 is running
- Check `ALMA_DISPLAY` setting
- Verify clock service status

**Database errors:**
- Check database path permissions
- Run backup and restore to validate database

## Backup and Restore

### Manual Backup

```bash
sudo /opt/alma-tv/scripts/backup.sh
```

### Manual Restore

```bash
# List available backups
ls -lh /var/backups/alma/

# Restore from backup
sudo /opt/alma-tv/scripts/restore.sh /var/backups/alma/alma_backup_YYYYMMDD_HHMMSS.tar.gz
```

## Uninstallation

```bash
# Stop and disable services
sudo systemctl stop alma-playback.service alma-clock.service alma-feedback.service
sudo systemctl disable alma-playback.service alma-clock.service alma-feedback.service

# Remove service files
sudo rm /etc/systemd/system/alma-*.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/alma-tv

# Remove data (optional)
sudo rm -rf /var/lib/alma /var/log/alma /var/cache/alma /var/backups/alma

# Remove user (optional)
sudo userdel alma
```

## Upgrading

```bash
# Stop services
sudo systemctl stop alma-playback.service alma-clock.service alma-feedback.service

# Backup database
sudo /opt/alma-tv/scripts/backup.sh

# Pull latest code
cd /opt/alma-tv
sudo -u alma git pull

# Update dependencies
sudo -u alma bash -c "source .venv/bin/activate && pip install -e . --upgrade"

# Restart services
sudo systemctl start alma-playback.service alma-clock.service alma-feedback.service
```

## Support

For issues and questions:
- Check logs in `/var/log/alma/`
- Review service status with `systemctl status`
- Consult `README.md` and `plan.md` for architecture details

#!/bin/bash
# Setup cron job for scheduled updates

# Ensure the script is executable
chmod +x /app/run_scheduled_update.py

# Create the cron job entry (daily at 03:00 UTC)
echo "0 3 * * * cd /app && python /app/run_scheduled_update.py >> /var/log/cron.log 2>&1" > /etc/cron.d/ainalyst-update

# Apply correct permissions to the crontab file
chmod 0644 /etc/cron.d/ainalyst-update

# Create the cron log file
touch /var/log/cron.log

# Apply correct permissions to the cron log file
chmod 0666 /var/log/cron.log

# Inform the user
echo "Cron job for daily updates at 03:00 UTC has been setup."
echo "Logs will be written to /var/log/cron.log"
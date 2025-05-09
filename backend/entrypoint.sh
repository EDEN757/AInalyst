#!/bin/bash
# Entrypoint script for the backend container

# Setup cron job
/app/setup_cron.sh

# Start cron service
service cron start

# Run the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
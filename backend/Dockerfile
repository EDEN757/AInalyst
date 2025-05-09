FROM python:3.10-slim

WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y cron && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x /app/run_scheduled_update.py
RUN chmod +x /app/setup_cron.sh

# Expose port
EXPOSE 8000

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Use entrypoint script to start services
ENTRYPOINT ["/app/entrypoint.sh"]
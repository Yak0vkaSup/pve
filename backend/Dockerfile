FROM python:3.10

# Install required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pve

# Copy and install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --upgrade eventlet websocket-client websockets

# Copy the entrypoint script
COPY backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create logs directory
RUN mkdir -p /pve/backend/logs

EXPOSE 5001
EXPOSE 5432

ENV WEBSOCKET_ALLOW_ALL=True

# Use our entrypoint script
ENTRYPOINT ["docker-entrypoint.sh"] 
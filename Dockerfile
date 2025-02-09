FROM python:3.10
WORKDIR /pve

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --upgrade eventlet websocket-client websockets
RUN apt-get update && apt-get install -y --no-install-recommends libssl-dev

EXPOSE 5001
EXPOSE 5432

ENV WEBSOCKET_ALLOW_ALL=True

# Flask Backend for Fetching Candle Data

This project is a Flask-based backend that fetches financial candlestick data from a PostgreSQL database and provides it as a JSON API for a frontend application.

## Requirements

- Python 3.10
- PostgreSQL database with candlestick data
- Docker for PostgreSQL setup

## Setup

### 1. Clone the repository:

```bash
git clone https://github.com/Yak0vkaSup/platform_gui
cd platform_gui/backend
```

### 2. Create a virtual environment:

```bash
conda create -n my_env python=3.10
```

### 3. Activate the virtual environment:

- On **Windows**:

  ```bash
  conda activate my_env
  ```

### 4. Install dependencies:

```bash
pip install -r requirements.txt
```

### 5. Run the Flask server:

```bash
python DEPRECATED_main.py
```

### 6. Deactivate the virtual environment (when done):

```bash
deactivate
```

---

## Database Configuration

### 1. Install Docker:

Download and install Docker Desktop from the official [Docker website](https://www.docker.com/products/docker-desktop).

### 2. Download the Docker image for the database:

Run the following command to pull the database image:

```bash
docker pull timescale/timescaledb:latest-pg16
```

### 3. Start the PostgreSQL container:

Run this command to start the container:

```bash
docker run -d --name maindb \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=postgres \
  -e POSTGRES_MAX_CONNECTIONS=5000 \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg16
```

This command will start the container in detached mode with the name `timescaledb`, and the database will be available on port `5432`. Use the following credentials to connect:

- **Username**: `postgres`
- **Password**: `postgres`
- **Database**: `postgres`

### 4. Connect to the database and use db_init_query.SQL:

You can use `pgAdmin` or any PostgreSQL client to connect to the database. Use the following connection details:

- **Host**: `localhost`
- **Port**: `5432`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `postgres`

### 5. Update data in the database:

Configure your data manager or use the basic settings. You can run the manager using:

```bash
python data/manager.py
```
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list

sudo apt-get update
sudo apt-get install redis

Lastly, start the Redis server like so:

sudo service redis-server start

Connect to Redis

Once Redis is running, you can test it by running redis-cli:

redis-cli

Test the connection with the ping command:

127.0.0.1:6379> ping
PONG
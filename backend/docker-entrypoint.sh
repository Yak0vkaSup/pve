#!/bin/bash
set -e

# PVE Platform Docker Entrypoint Script
# This script ensures proper initialization on first startup

echo "🚀 Starting PVE Platform..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
while ! pg_isready -h ${DB_HOST:-postgresql} -p ${DB_PORT:-5432} -U ${DB_USER:-postgres}; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
while ! redis-cli -h redis ping > /dev/null 2>&1; do
    echo "Redis is unavailable - sleeping"
    sleep 2
done
echo "✅ Redis is ready!"

# Check if this is the first run by checking if users table exists
echo "🔍 Checking database initialization status..."
DB_INITIALIZED=$(PGPASSWORD=${DB_PASSWORD:-postgres} psql -h ${DB_HOST:-postgresql} -U ${DB_USER:-postgres} -d ${DB_NAME:-postgres} -tAc "SELECT to_regclass('public.users');")

if [ "$DB_INITIALIZED" = "" ]; then
    echo "🏗️  First-time setup detected. Initializing database..."
    echo "📋 Database schema will be automatically applied from db_init_query.SQL"
else
    echo "✅ Database already initialized"
fi

# Create logs directory if it doesn't exist
mkdir -p /pve/backend/logs

echo "🎯 Starting application..."

# Execute the original command
exec "$@" 
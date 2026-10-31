#!/bin/bash
set -e

echo "Running control-plane migrations..."
cd /app/control-plane && alembic upgrade head

echo "Running processing migrations..."
cd /app/processing && alembic upgrade head

echo "All migrations complete."

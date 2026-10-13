#!/usr/bin/env bash
# Render Build Script for Weather Truck Routing API
set -o errexit

echo "==> Upgrading pip and installing production dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Collecting static assets for WhiteNoise..."
python manage.py collectstatic --no-input

echo "==> Build complete!"

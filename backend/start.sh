#!/bin/bash
set -e
echo "Running migrations..."
python manage.py migrate --noinput
echo "Seeding database..."
python seed.py || echo "Seed already done, skipping"
echo "Starting Celery..."
celery -A config worker --beat --loglevel=info &
echo "Starting Gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
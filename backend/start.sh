#!/bin/bash
echo "=== Running migrations ==="
python manage.py migrate --noinput
echo "=== Seeding ==="
python seed.py || true
echo "=== Starting Celery ==="
celery -A config worker --beat --loglevel=info &
echo "=== Starting Gunicorn ==="
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
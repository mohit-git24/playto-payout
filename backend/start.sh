#!/bin/bash
echo "Running migrations..."
python manage.py migrate --noinput
if [ $? -ne 0 ]; then
    echo "Migrations failed! Exiting."
    exit 1
fi
echo "Migrations done."
echo "Seeding database..."
python seed.py
echo "Starting Celery in background..."
celery -A config worker --beat --loglevel=info &
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
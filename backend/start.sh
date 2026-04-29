#!/bin/bash
python manage.py migrate
python seed.py
celery -A config worker --beat --loglevel=info &
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
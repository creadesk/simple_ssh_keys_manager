#!/usr/bin/env bash
set -euo pipefail

trap 'kill 0' SIGTERM SIGINT EXIT

: "${DJANGO_SETTINGS_MODULE:=core.settings}"
: "${DJANGO_SECRET_KEY:='dev-secret-key'}"
: "${DJANGO_ALLOWED_HOSTS:=*}"

echo "Running migrations..."
python manage.py migrate --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "Preparing to create superuser: ${DJANGO_SUPERUSER_USERNAME}"

    USER_EXISTS=$(python manage.py check_superuser)

    if [ "$USER_EXISTS" = "False" ]; then
        echo "Superuser does not exist – creating..."
        python manage.py createsuperuser \
            --noinput \
            --username "${DJANGO_SUPERUSER_USERNAME}" \
            --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
    else
        echo "Superuser ${DJANGO_SUPERUSER_USERNAME} already exists – skipping creation."
    fi
else
    echo "DJANGO_SUPERUSER_USERNAME and/or DJANGO_SUPERUSER_PASSWORD not set – skipping superuser creation."
fi

echo "Starte Gunicorn"
gunicorn core.wsgi:application \
    --access-logfile "-" \
    --error-logfile "-" \
    --timeout 550 \
    --bind 0.0.0.0:8000 \
    --workers 2 &

wait -n

kill 0
wait
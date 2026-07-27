#!/usr/bin/env bash
set -euo pipefail

echo "Running database migrations..."
python manage.py migrate --noinput

case "${BOOTSTRAP_BUNDLED_CATALOGS_ON_START:-true}" in
  1|true|TRUE|yes|YES)
    echo "Importing bundled scheme, requirement, funding, and loan catalogs..."
    python manage.py bootstrap_catalogs
    ;;
esac

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

#!/usr/bin/env sh
set -eu

# Keep API availability independent from optional catalog imports. Database
# migrations remain a hard requirement, but bundled data is initialized by the
# separate catalog_init service after the health endpoint is available.
python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec python manage.py runserver 0.0.0.0:8000

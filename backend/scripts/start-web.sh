#!/usr/bin/env sh
set -eu

sleep 5
python manage.py migrate --noinput

case "${BOOTSTRAP_BUNDLED_CATALOGS_ON_START:-true}" in
  1|true|TRUE|yes|YES)
    echo "Importing bundled scheme, requirement, funding, and loan catalogs..."
    python manage.py bootstrap_catalogs
    ;;
esac

python manage.py collectstatic --noinput
exec python manage.py runserver 0.0.0.0:8000

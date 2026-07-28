#!/usr/bin/env sh
set -eu

python manage.py check
python manage.py migrate --noinput

case "${BOOTSTRAP_BUNDLED_CATALOGS_ON_START:-true}" in
  1|true|TRUE|yes|YES)
    echo "Importing verified schemes, external schemes, requirements, funding, and loan catalogs..."
    python manage.py bootstrap_catalogs
    python manage.py platform_doctor --strict
    ;;
esac

python manage.py collectstatic --noinput
exec python manage.py runserver 0.0.0.0:8000

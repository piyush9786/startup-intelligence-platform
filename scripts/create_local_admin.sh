#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/laptop_common.sh"

ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

if [[ -z "${ADMIN_PASSWORD}" ]]; then
  ADMIN_PASSWORD="$(random_secret | cut -c1-20)"
  GENERATED_PASSWORD=true
else
  GENERATED_PASSWORD=false
fi

compose exec -T \
  -e ADMIN_USERNAME="${ADMIN_USERNAME}" \
  -e ADMIN_EMAIL="${ADMIN_EMAIL}" \
  -e ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  backend python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ['ADMIN_USERNAME']
email = os.environ['ADMIN_EMAIL']
password = os.environ['ADMIN_PASSWORD']
user, _ = User.objects.get_or_create(
    username=username,
    defaults={'email': email},
)
user.email = email
user.is_active = True
user.is_staff = True
user.is_superuser = True
if hasattr(user, 'role'):
    user.role = 'admin'
user.set_password(password)
user.save()
print(f'Admin account ready: {username} ({email})')
PY

if [[ "${GENERATED_PASSWORD}" == "true" ]]; then
  printf '\nGenerated local password: %s\n' "${ADMIN_PASSWORD}"
  printf 'Save it now; it is not written to the project files.\n'
fi

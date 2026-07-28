import os

from django.core.wsgi import get_wsgi_application

# Deployable entrypoints fail closed. Local development selects the development
# module explicitly through manage.py or docker-compose.yml.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_wsgi_application()

from django.conf import settings
from django.db import connection
from redis import Redis
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            database_ok = cursor.fetchone()[0] == 1
        return Response({"status": "ok", "database": database_ok})


class PlatformStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        redis_ok = False
        try:
            redis_ok = bool(Redis.from_url(settings.CELERY_BROKER_URL).ping())
        except Exception:
            redis_ok = False
        return Response(
            {
                "api": True,
                "postgres": True,
                "redis": redis_ok,
                "qdrant_url": settings.QDRANT_URL,
                "neo4j_uri": settings.NEO4J_URI,
            }
        )

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SchemeViewSet

router = DefaultRouter()
router.register(r"schemes", SchemeViewSet, basename="scheme")

urlpatterns = [
    path("", include(router.urls)),
]

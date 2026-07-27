from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompanyDataSourceViewSet, CompanyViewSet, RawCompanyDatasetViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register(
    "company-data-sources",
    CompanyDataSourceViewSet,
    basename="company-data-source",
)
router.register(
    "company-datasets",
    RawCompanyDatasetViewSet,
    basename="company-dataset",
)

urlpatterns = [path("", include(router.urls))]

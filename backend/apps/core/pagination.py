from rest_framework.pagination import PageNumberPagination


class PlatformPageNumberPagination(PageNumberPagination):
    """Bounded page-size override for catalog-heavy founder workspaces."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 250

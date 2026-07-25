# Modular Routing, Settings Package & Default-Deny Security (v1)

## Overview

This document describes the backend architecture refactoring implemented to enforce strict API security, separate environment configurations, and decompose the root URL configuration into modular domain routers.

---

## 1. 🛡️ Default-Deny Permission Policy

The Django REST Framework global configuration (`config/settings/base.py`) enforces an **explicit Default-Deny security posture**:

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    ...
}
```

Any new API view automatically denies unauthenticated access unless explicitly marked with `@permission_classes([AllowAny])` or `permission_classes = [AllowAny]`. Publicly whitelisted endpoints:
- `HealthView` (`/api/v1/health/`)
- `PlatformStatusView` (`/api/v1/status/`)
- `FounderRegistrationView` (`/api/v1/auth/register/`)
- `TokenObtainPairView` & `TokenRefreshView` (`/api/v1/auth/token/`)

---

## 2. ⚙️ Structured Settings Package

Settings are organized under `backend/config/settings/`:

- `base.py`: Core Django config, installed apps, DRF defaults, DB definitions, Celery settings.
- `development.py`: Development overrides (CORS, debug logging, local cache settings).
- `production.py`: Production security rules (HTTPS enforcement, secure cookies, strict CORS/CSRF).
- `__init__.py`: Package initialization.

To maintain backward compatibility with legacy tooling and pytest, `config/settings.py` re-exports development settings as a entrypoint fallback.

---

## 3. 🌐 Modular Application URL Routers

The monolithic `config/urls.py` file has been decomposed into individual, application-scoped `urls.py` modules:

| Django App | URL Module | Endpoints Covered |
|---|---|---|
| `accounts` | `apps.accounts.urls` | Registration, JWT token obtain/refresh, current user identity |
| `assistant` | `apps.assistant.urls` | AI Concierge, site-wide chatbot, copilot context |
| `core` | `apps.core.urls` | Health checks, platform status monitors |
| `discovery` | `apps.discovery.urls` | Web crawler, crawl frontier, URL assessments |
| `documents` | `apps.documents.urls` | Document extraction, chunking & processing |
| `recommendations` | `apps.recommendations.urls` | Scheme eligibility, SVM ranking, verification queues, application tracker |
| `schemes` | `apps.schemes.urls` | Scheme catalog ViewSets & details |
| `sources` | `apps.sources.urls` | Data source registry & crawl runs |
| `startups` | `apps.startups.urls` | Startup profiles, advisor briefings, readiness plans, capital planner, builder |

The root `config/urls.py` includes these modules cleanly under `/api/v1/`:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/assistant/", include("apps.assistant.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.discovery.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/knowledge/", include("apps.knowledge.urls")),
    path("api/v1/", include("apps.recommendations.urls")),
    path("api/v1/", include("apps.schemes.urls")),
    path("api/v1/", include("apps.sources.urls")),
    path("api/v1/", include("apps.startups.urls")),
]
```

---

## 🧪 Verification

- **Django System Check**: `python manage.py check` passes with 0 issues.
- **Pytest Suite**: All 561 backend tests pass 100%.

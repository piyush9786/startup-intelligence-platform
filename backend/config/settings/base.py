import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    x.strip() for x in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",") if x.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "apps.core",
    "apps.accounts",
    "apps.assistant",
    "apps.sources",
    "apps.companies",
    "apps.documents",
    "apps.discovery",
    "apps.knowledge",
    "apps.schemes",
    "apps.startups",
    "apps.recommendations",
    "apps.ml_engine",
    "apps.research",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "startup_intelligence"),
        "USER": os.environ.get("POSTGRES_USER", "startup"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "startup"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    x.strip()
    for x in os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if x.strip()
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    x.strip()
    for x in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:5173"),
    ).split(",")
    if x.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": os.getenv("AUTH_LOGIN_RATE", "10/minute"),
        "auth_refresh": os.getenv("AUTH_REFRESH_RATE", "30/minute"),
        "auth_logout": os.getenv("AUTH_LOGOUT_RATE", "30/minute"),
        "auth_register": os.getenv("AUTH_REGISTER_RATE", "5/hour"),
        "research_hourly": os.getenv("RESEARCH_HOURLY_RATE", "5/hour"),
        "research_daily": os.getenv("RESEARCH_DAILY_RATE", "20/day"),
        "assistant_chat_turn": os.getenv(
            "ASSISTANT_CHATBOT_TURN_RATE",
            "20/hour",
        ),
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        "TIMEOUT": 300,
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Startup Intelligence Platform API",
    "DESCRIPTION": "Verified schemes, registrations, loans, eligibility and recommendations.",
    "VERSION": "1.0.0",
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

RESEARCH_TASK_SOFT_TIME_LIMIT_SECONDS = int(
    os.environ.get("RESEARCH_TASK_SOFT_TIME_LIMIT_SECONDS", "540")
)
RESEARCH_TASK_TIME_LIMIT_SECONDS = int(
    os.environ.get("RESEARCH_TASK_TIME_LIMIT_SECONDS", "600")
)
RESEARCH_JOB_QUEUE_TIMEOUT_SECONDS = int(
    os.environ.get("RESEARCH_JOB_QUEUE_TIMEOUT_SECONDS", "900")
)
RESEARCH_JOB_RUNNING_TIMEOUT_SECONDS = int(
    os.environ.get("RESEARCH_JOB_RUNNING_TIMEOUT_SECONDS", "660")
)
RESEARCH_STALE_RECOVERY_BATCH_SIZE = int(
    os.environ.get("RESEARCH_STALE_RECOVERY_BATCH_SIZE", "100")
)

CELERY_BEAT_SCHEDULE = {
    "ml-nightly-feature-extraction": {
        "task": "ml_engine.nightly_feature_extraction",
        "schedule": 86400,  # every 24 hours
    },
    "ml-nightly-anomaly-and-cohort": {
        "task": "ml_engine.nightly_anomaly_and_cohort",
        "schedule": 86400,
    },
    "ml-weekly-model-retraining": {
        "task": "ml_engine.weekly_model_retraining",
        "schedule": 604800,  # every 7 days
    },
}

CELERY_BEAT_SCHEDULE["research-recover-stale-jobs"] = {
    "task": "research.recover_stale_requests",
    "schedule": 300,
}

# ML Engine configuration
ML_MODELS_DIR = os.environ.get("ML_MODELS_DIR", str(BASE_DIR / "ml_models"))

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "mailpit")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@startup.local")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
STARTUP_ADVISOR_RAG_ENABLED = (
    os.environ.get("STARTUP_ADVISOR_RAG_ENABLED", "false").lower() == "true"
)
STARTUP_ADVISOR_QDRANT_COLLECTION = os.environ.get(
    "STARTUP_ADVISOR_QDRANT_COLLECTION",
    "startup_document_chunks_v1",
)
STARTUP_ADVISOR_QDRANT_TIMEOUT_SECONDS = float(
    os.environ.get(
        "STARTUP_ADVISOR_QDRANT_TIMEOUT_SECONDS",
        "30",
    )
)
STARTUP_ADVISOR_EMBEDDING_MODEL = os.environ.get(
    "STARTUP_ADVISOR_EMBEDDING_MODEL",
    "embeddinggemma",
)
STARTUP_ADVISOR_EMBEDDING_VERSION = os.environ.get(
    "STARTUP_ADVISOR_EMBEDDING_VERSION",
    "ollama-embedding-v1",
)
STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS = float(
    os.environ.get(
        "STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS",
        "120",
    )
)
STARTUP_ADVISOR_EMBEDDING_BATCH_SIZE = int(
    os.environ.get(
        "STARTUP_ADVISOR_EMBEDDING_BATCH_SIZE",
        "32",
    )
)
STARTUP_ADVISOR_EMBEDDING_KEEP_ALIVE = os.environ.get(
    "STARTUP_ADVISOR_EMBEDDING_KEEP_ALIVE",
    "5m",
)
STARTUP_ADVISOR_RAG_TOP_K = int(os.environ.get("STARTUP_ADVISOR_RAG_TOP_K", "6"))
STARTUP_ADVISOR_RAG_MIN_SCORE = float(os.environ.get("STARTUP_ADVISOR_RAG_MIN_SCORE", "0.35"))
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET_RAW = os.environ.get("MINIO_BUCKET_RAW", "startup-raw-documents")
MINIO_BUCKET_STARTUP_EVIDENCE = os.environ.get(
    "MINIO_BUCKET_STARTUP_EVIDENCE",
    "startup-eligibility-evidence",
)
ELIGIBILITY_EVIDENCE_MAX_BYTES = int(
    os.environ.get("ELIGIBILITY_EVIDENCE_MAX_BYTES", str(10 * 1024 * 1024))
)
COMPANY_IMPORT_MAX_BYTES = int(
    os.environ.get("COMPANY_IMPORT_MAX_BYTES", str(100 * 1024 * 1024))
)
COMPANY_IMPORT_MAX_ROWS = int(os.environ.get("COMPANY_IMPORT_MAX_ROWS", "250000"))
COLLECTOR_USER_AGENT = os.environ.get(
    "COLLECTOR_USER_AGENT",
    "StartupIntelligenceCollector/0.1 (+http://localhost:5173)",
)
COLLECTOR_MAX_REDIRECTS = int(os.environ.get("COLLECTOR_MAX_REDIRECTS", "5"))
DOCUMENT_EXTRACTOR_VERSION = os.environ.get(
    "DOCUMENT_EXTRACTOR_VERSION",
    "v2",
)
DOCUMENT_CHUNK_MAX_CHARS = int(os.environ.get("DOCUMENT_CHUNK_MAX_CHARS", "1800"))
DOCUMENT_CHUNK_OVERLAP_CHARS = int(os.environ.get("DOCUMENT_CHUNK_OVERLAP_CHARS", "250"))
DOCUMENT_MAX_CHUNKS = int(os.environ.get("DOCUMENT_MAX_CHUNKS", "2000"))
MINIO_BUCKET_PROCESSED = os.environ.get(
    "MINIO_BUCKET_PROCESSED",
    "startup-processed-documents",
)
DISCOVERY_ASSESSOR_VERSION = os.environ.get(
    "DISCOVERY_ASSESSOR_VERSION",
    "v1",
)
DISCOVERY_MAX_DEPTH = int(os.environ.get("DISCOVERY_MAX_DEPTH", "3"))
DISCOVERY_MAX_LINKS_PER_DOCUMENT = int(os.environ.get("DISCOVERY_MAX_LINKS_PER_DOCUMENT", "500"))
DISCOVERY_MAX_PAGES_PER_SOURCE = int(os.environ.get("DISCOVERY_MAX_PAGES_PER_SOURCE", "250"))
DISCOVERY_REQUEST_DELAY_SECONDS = float(os.environ.get("DISCOVERY_REQUEST_DELAY_SECONDS", "1.5"))
DISCOVERY_MIN_RAG_SCORE = float(os.environ.get("DISCOVERY_MIN_RAG_SCORE", "45"))
DISCOVERY_MIN_STRUCTURED_SCORE = float(os.environ.get("DISCOVERY_MIN_STRUCTURED_SCORE", "60"))

KNOWLEDGE_EXTRACTOR_VERSION = os.environ.get(
    "KNOWLEDGE_EXTRACTOR_VERSION",
    "v1",
)
KNOWLEDGE_MIN_CANDIDATE_SCORE = int(os.environ.get("KNOWLEDGE_MIN_CANDIDATE_SCORE", "4"))
KNOWLEDGE_MAX_BLOCK_CHARS = int(os.environ.get("KNOWLEDGE_MAX_BLOCK_CHARS", "30000"))

STARTUP_ADVISOR_LLM_PROVIDER = os.environ.get(
    "STARTUP_ADVISOR_LLM_PROVIDER",
    "ollama",
)
OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL",
    "http://ollama:11434",
)
OLLAMA_CONTEXT_LENGTH = max(
    1024,
    int(
        os.environ.get(
            "OLLAMA_CONTEXT_LENGTH",
            "4096",
        )
    ),
)
STARTUP_ADVISOR_LLM_MODEL = os.environ.get(
    "STARTUP_ADVISOR_LLM_MODEL",
    "qwen3:4b",
)
STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS = float(
    os.environ.get(
        "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS",
        "480",
    )
)
STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS = int(
    os.environ.get(
        "STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS",
        "900",
    )
)
STARTUP_ADVISOR_TASK_SOFT_TIME_LIMIT_SECONDS = int(
    os.environ.get(
        "STARTUP_ADVISOR_TASK_SOFT_TIME_LIMIT_SECONDS",
        "960",
    )
)
STARTUP_ADVISOR_TASK_TIME_LIMIT_SECONDS = int(
    os.environ.get(
        "STARTUP_ADVISOR_TASK_TIME_LIMIT_SECONDS",
        "1020",
    )
)
STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS = int(
    os.environ.get(
        "STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS",
        "1200",
    )
)
STARTUP_ADVISOR_LLM_TEMPERATURE = float(
    os.environ.get(
        "STARTUP_ADVISOR_LLM_TEMPERATURE",
        "0",
    )
)
STARTUP_ADVISOR_LLM_SEED = int(
    os.environ.get(
        "STARTUP_ADVISOR_LLM_SEED",
        "7",
    )
)
STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS = max(
    256,
    int(
        os.environ.get(
            "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS",
            "1024",
        )
    ),
)
STARTUP_ADVISOR_LLM_KEEP_ALIVE = os.environ.get(
    "STARTUP_ADVISOR_LLM_KEEP_ALIVE",
    "5m",
)

CHATBOT_LLM_ENABLED = os.environ.get(
    "CHATBOT_LLM_ENABLED",
    "true",
).lower() in ("1", "true", "yes")

CHATBOT_LLM_MODEL = os.environ.get(
    "CHATBOT_LLM_MODEL",
    STARTUP_ADVISOR_LLM_MODEL,
)

CHATBOT_LLM_TIMEOUT_SECONDS = float(
    os.environ.get(
        "CHATBOT_LLM_TIMEOUT_SECONDS",
        "180",
    )
)

CHATBOT_LLM_MAX_OUTPUT_TOKENS = max(
    64,
    int(
        os.environ.get(
            "CHATBOT_LLM_MAX_OUTPUT_TOKENS",
            "512",
        )
    ),
)

CHATBOT_LLM_HISTORY_TURNS = max(
    0,
    int(
        os.environ.get(
            "CHATBOT_LLM_HISTORY_TURNS",
            "6",
        )
    ),
)

CHATBOT_LLM_KEEP_ALIVE = os.environ.get(
    "CHATBOT_LLM_KEEP_ALIVE",
    STARTUP_ADVISOR_LLM_KEEP_ALIVE,
)

WEB_SEARCH_ENABLED = (
    os.environ.get("WEB_SEARCH_ENABLED", "true").lower()
    in {"1", "true", "yes"}
)

WEB_SEARCH_PROVIDER = os.environ.get(
    "WEB_SEARCH_PROVIDER",
    "tavily",
)

TAVILY_API_KEY = os.environ.get(
    "TAVILY_API_KEY",
    "",
)

BRAVE_API_KEY = os.environ.get(
    "BRAVE_API_KEY",
    "",
)

WEB_SEARCH_MAX_RESULTS = int(
    os.environ.get("WEB_SEARCH_MAX_RESULTS", "8")
)

WEB_SEARCH_TIMEOUT_SECONDS = float(
    os.environ.get("WEB_SEARCH_TIMEOUT_SECONDS", "30")
)

WEB_SEARCH_CACHE_SECONDS = int(
    os.environ.get("WEB_SEARCH_CACHE_SECONDS", "21600")
)

WEB_SEARCH_DEPTH = os.environ.get("WEB_SEARCH_DEPTH", "basic")
WEB_SEARCH_TIME_RANGE = os.environ.get("WEB_SEARCH_TIME_RANGE", "year")
WEB_SEARCH_START_DATE = os.environ.get("WEB_SEARCH_START_DATE", "")
WEB_SEARCH_END_DATE = os.environ.get("WEB_SEARCH_END_DATE", "")

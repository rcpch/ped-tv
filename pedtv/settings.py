import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django_tasks",
    "django_tasks_db",
    "providers",
    "content",
    "playlists",
    "manage_site",
    "public",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pedtv.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pedtv.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "pedtv"),
        "USER": os.environ.get("DB_USER", "pedtv"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "pedtv"),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/manage/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# File storage
# ---------------------------------------------------------------------------
_storage_backend = os.environ.get("STORAGE_BACKEND", "s3")

if _storage_backend == "azure":
    _default_storage = {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "account_name": os.environ["AZURE_ACCOUNT_NAME"],
            "account_key": os.environ.get("AZURE_ACCOUNT_KEY"),
            "azure_container": os.environ.get("AZURE_CONTAINER", "pedtv-media"),
        },
    }
else:
    # S3-compatible — MinIO in dev, swappable for Garage
    #
    # endpoint_url  — used for API calls inside Docker (minio:9000)
    # custom_domain — used when building public URLs seen by the browser
    #                 format: <host>/<bucket>  e.g. localhost:9000/pedtv-media
    _s3_bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "pedtv-media")
    _s3_public_host = os.environ.get("AWS_S3_PUBLIC_HOST", "localhost:9000")
    _default_storage = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"),
            "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin"),
            "bucket_name": _s3_bucket,
            "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL", "http://minio:9000"),
            "region_name": os.environ.get("AWS_S3_REGION_NAME", "us-east-1"),
            "file_overwrite": False,
            "default_acl": "public-read",
            # Disable signed URLs — files are public-read so no auth needed
            "querystring_auth": False,
            # Rewrite generated URLs to use the browser-visible host
            "custom_domain": f"{_s3_public_host}/{_s3_bucket}",
            "url_protocol": os.environ.get("AWS_S3_URL_PROTOCOL", "http:"),
        },
    }

STORAGES = {
    "default": _default_storage,
    "staticfiles": {
        # In production (DEBUG=False) use content-hashed filenames via
        # CompressedManifestStaticFilesStorage (requires collectstatic).
        # In dev/test use plain StaticFilesStorage so tests don't need a manifest.
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

# ---------------------------------------------------------------------------
# Background tasks (django-tasks + django-tasks-db)
# ---------------------------------------------------------------------------
TASKS = {
    "default": {
        "BACKEND": "django_tasks_db.backend.DatabaseBackend",
    }
}

# ---------------------------------------------------------------------------
# Debug toolbar (dev only)
# ---------------------------------------------------------------------------
if DEBUG:
    try:
        import debug_toolbar  # noqa: F401
        INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
        MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
        INTERNAL_IPS = ["127.0.0.1"]
    except ImportError:
        pass

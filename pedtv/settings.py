import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load the env file if present (provided by docker compose in dev, volume-mounted
# into the container in Azure). Environment variables already set take precedence,
# and a missing file is silently ignored.
load_dotenv(BASE_DIR / "envs" / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1").split(",")]

# Trust the reverse proxy's X-Forwarded-Proto header to detect HTTPS. Enable
# in production where TLS is terminated upstream (e.g. Fastly/nginx in front
# of the container) so password reset links etc. use https://. Leave unset in
# dev where there is no proxy.
if os.environ.get("SECURE_PROXY_SSL_HEADER", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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

database_config: dict = {
    # Custom backend (subclasses the stock PostgreSQL backend) that can inject a
    # fresh Azure Entra ID token as the password on each new connection.
    "ENGINE": "pedtv.db_backend",
    "NAME": os.environ.get("DB_NAME", "pedtv"),
    "USER": os.environ.get("DB_USER", "pedtv"),
    "HOST": os.environ.get("DB_HOST", "postgres"),
    "PORT": os.environ.get("DB_PORT", "5432"),
}

if os.environ.get("DB_USE_AAD_TOKEN", "false").lower() == "true":
    # Authenticate with a managed identity token acquired per connection by the
    # custom backend; no static password is needed.
    database_config["USE_AAD_TOKEN"] = True
else:
    database_config["PASSWORD"] = os.environ.get("DB_PASSWORD", "pedtv")

DATABASES = {"default": database_config}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Used for password reset emails. Dev has no SMTP relay, so the default
# "console" backend just prints emails to the container logs. Production sets
# EMAIL_BACKEND=smtp plus the SMTP_* settings below in the env file.
_email_backend = os.environ.get("EMAIL_BACKEND", "console")

if _email_backend == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
    EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() == "true"
    # Don't let a hung SMTP server hang the request forever.
    EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
else:
    # "console" — write emails to stdout (visible in docker compose logs).
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost")

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Django's default logging only writes to the console when DEBUG is True, which
# makes production 500s invisible in container logs. Log unhandled request
# errors (with tracebacks) to stderr regardless of DEBUG.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

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
            # Public host for media URLs. django-storages swaps this in for
            # <account>.blob.core.windows.net but keeps the container in the
            # path, so e.g. "pedtv.rcpch.tech" serves media from
            # https://pedtv.rcpch.tech/<container>/<key> — point Fastly at the
            # blob account for that path prefix and no URL rewriting is needed.
            "custom_domain": os.environ.get("AZURE_CUSTOM_DOMAIN"),
        },
    }
else:
    # S3-compatible — Garage in dev (single node), Azure Blob in production
    #
    # endpoint_url  — used for API calls inside Docker (garage:9000)
    # custom_domain — public URLs seen by the browser, served unsigned by
    #                 Garage's website endpoint (anonymous reads):
    #                 format: <bucket>.<public-host>
    #                 e.g. http://pedtv-media.web.garage.localhost:3902/<key>
    _s3_bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "pedtv-media")
    _s3_public_host = os.environ.get("AWS_S3_PUBLIC_HOST", "web.garage.localhost:3902")
    _default_storage = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"),
            # Garage requires secrets >= 16 chars; this is the matching dev default
            "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadminminioadmin"),
            "bucket_name": _s3_bucket,
            "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL", "http://garage:9000"),
            "region_name": os.environ.get("AWS_S3_REGION_NAME", "us-east-1"),
            "file_overwrite": False,
            # Garage implements neither ACLs nor bucket policies; public reads
            # are served anonymously by its website endpoint instead (enabled
            # in s/bootstrap), so no ACL headers and no signed URLs.
            "querystring_auth": False,
            # Rewrite generated URLs to the browser-visible website endpoint host
            "custom_domain": f"{_s3_bucket}.{_s3_public_host}",
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

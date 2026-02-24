from pathlib import Path
from datetime import timedelta
import os
import dotenv

# ------------------------------------------------------------------------------
# ENV
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

dotenv.load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-change-this-in-production"
)

ALLOWED_HOSTS = ['*']

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ------------------------------------------------------------------------------
# Environment Variables
# ------------------------------------------------------------------------------
GOALSERVE_API_KEY = os.getenv("GOALSERVE_API_KEY", "fallback_api__key")



# ------------------------------------------------------------------------------
# APPLICATIONS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",

    "dj_rest_auth",
    "dj_rest_auth.registration",

    "django_otp",
    "django_otp.plugins.otp_email",

    "corsheaders",
    "storages",
    "channels",
]

LOCAL_APPS = [
    "apps.games",
    "apps.leaderboard",
    "apps.private_leagues",
    "apps.public_leagues",
    "apps.notifications",
    "apps.payments",
    "apps.players",
    "apps.scoring",
    "apps.teams",
    "apps.users",
    "apps.admin_panel",
    "apps.matches",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

SITE_ID = 1

# ------------------------------------------------------------------------------
# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",         # Allows or blocks cross-origin requests (CORS) from other domains
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",   # Adds account-related data (login, signup, user session) to each request
    "django_otp.middleware.OTPMiddleware",            # Enables OTP (one-time password) verification for two-factor authentication
]

# ------------------------------------------------------------------------------
# URL / ASGI / WSGI
# ------------------------------------------------------------------------------
ROOT_URLCONF = "core.urls"

ASGI_APPLICATION = "core.asgi.application"
WSGI_APPLICATION = "core.wsgi.application"

# ------------------------------------------------------------------------------
# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ------------------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------------------
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

# ------------------------------------------------------------------------------
# PASSWORD VALIDATION
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------------------
# INTERNATIONALIZATION
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------------------
# AWS S3 (STATIC + MEDIA)
# ------------------------------------------------------------------------------
if DEBUG:
    # -------- LOCAL FILE SYSTEM --------
    STATIC_URL = "/static/"
    STATIC_ROOT = BASE_DIR / "staticfiles"
    STATICFILES_DIRS = [BASE_DIR / "static"]

    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

else:
    # -------- AWS S3 --------
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")

    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_VERIFY = True

    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

    STATIC_LOCATION = "static"
    MEDIA_LOCATION = "media"

    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/"

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {"location": MEDIA_LOCATION},
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {"location": STATIC_LOCATION},
        },
    }
    
# ------------------------------------------------------------------------------
# REDIS (CACHE + CHANNELS)
# ------------------------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
    }
}

# ------------------------------------------------------------------------------
# CELERY
# ------------------------------------------------------------------------------
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    "fetch-nba-schedule-every-hour": {
        "task": "apps.games.tasks.fetch_nba_schedule_task",
        "schedule": 3600.0,  # 1 hour
    },
    "fetch-today-players-every-hour": {
        "task": "apps.players.tasks.fetch_today_players_task",
        "schedule": 3600.0,  # 1 hour
    },
    "fetch-live-scores-every-5-mins": {
        "task": "apps.scoring.tasks.fetch_live_scores_task",
        "schedule": 300.0,  # 5 minutes
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    }
}

# ------------------------------------------------------------------------------
# DJANGO REST FRAMEWORK & JWT
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    'DATETIME_FORMAT': "%d-%m-%Y %H:%M:%S",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=31),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=31),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ------------------------------------------------------------------------------
# AUTH / ALLAUTH
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
LOGIN_REDIRECT_URL = "/"

# ------------------------------------------------------------------------------
# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ------------------------------------------------------------------------------
# Google OAuth credentials 
# ------------------------------------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("SOCIAL_AUTH_GOOGLE_CLIENT_ID"),  
            "secret": os.getenv("SOCIAL_AUTH_GOOGLE_SECRET"), 
        },
    },
}

SOCIALACCOUNT_LOGIN_ON_GET = True

LOGIN_REDIRECT_URL = "/" 
SOCIAL_AUTH_GOOGLE_OAUTH2_CALLBACK_URL = (
    "http://127.0.0.1:8000/accounts/google/login/callback/"
)

SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["openid", "profile", "email"]


# ------------------------------------------------------------------------------
# SWAGGER
# ------------------------------------------------------------------------------
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    },
    "USE_SESSION_AUTH": False,
}

# ------------------------------------------------------------------------------
# DEFAULT PRIMARY KEY
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------
# CORS Settings
# -------------------------------
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    "https://api.mon5majeur.com",
    "http://api.mon5majeur.com",
    "https://mon5majeur.com",
    "http://mon5majeur.com",
    "https://13.51.217.30",
    "http://13.51.217.30",
]

# -------------------------------
# Sentry Settings
# -------------------------------
if not DEBUG:
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    if SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            send_default_pii=True,
            traces_sample_rate=0.2,
            integrations=[DjangoIntegration()],
            environment='production',
        )
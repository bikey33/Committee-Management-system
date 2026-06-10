
# config/settings.py
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

SECRET_KEY = config('SECRET_KEY', default='django-insecure-fallback-key-for-coolify-boot')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,172.16.49.6',
    cast=Csv()
)
# Ensure health checks on localhost/127.0.0.1 always work
if 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('localhost')
if '127.0.0.1' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('127.0.0.1')

if DEBUG:
    ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'users',
    'committee',
    'procurement',
    'core',
    'django_filters',
    'drf_yasg',
]

AUTHENTICATION_BACKENDS = [
    'users.authentication.CustomAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'users.CustomUser'
X_FRAME_OPTIONS = 'DENY'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Allow all origins for development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]

CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://derivational-calista-phytogeographic.ngrok-free.dev",
    "https://*.lovableproject.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://172.16.49.6:8080",
    "http://172.16.49.238:5173",
    "http://172.16.49.238:8080",
    "https://hoping-javascript-briefs-blast.trycloudflare.com",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'USER_ID_FIELD': 'employee_id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer <token>"',
        }
    },
    'USE_SESSION_AUTH': True,  # Enable session authentication for Swagger UI
    'LOGIN_URL': '/admin/login/',  # Django admin login URL
    'LOGOUT_URL': '/admin/logout/',  # Django admin logout URL
    'PERSIST_AUTH': True,  # Persist authentication across page reloads
}

APPEND_SLASH = True

ROOT_URLCONF = 'cms_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cms_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # Celery emits noisy DEBUG output (e.g. dumps a generated def-stub for
        # every task via head_from_fun) that floods the console under the root
        # DEBUG logger. Keep Celery at INFO so task start/success still shows.
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# AWS S3 Configuration - Always load AWS variables
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default=None)
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default=None)
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default=None)
AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_ADDRESSING_STYLE = config('AWS_S3_ADDRESSING_STYLE', default='auto')
AWS_S3_VERIFY = config('AWS_S3_VERIFY', default=True, cast=bool)
AWS_S3_USE_SSL = config('AWS_S3_USE_SSL', default=True, cast=bool)
AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default=None)
AWS_QUERYSTRING_AUTH = config('AWS_QUERYSTRING_AUTH', default=False, cast=bool)
AWS_S3_FILE_OVERWRITE = config('AWS_S3_FILE_OVERWRITE', default=False, cast=bool)
AWS_DEFAULT_ACL = config('AWS_DEFAULT_ACL', default=None)

# Use S3 if credentials are available, otherwise use local storage
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Set S3 URL for media files
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    else:
        MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}{AWS_STORAGE_BUCKET_NAME}/' if AWS_S3_ENDPOINT_URL else f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/'
else:
    # Fall back to local storage
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Email Configuration
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # For development
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # For production
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@procurement.com')

# Password Reset Settings
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour in seconds

# Cache configuration
# A SHARED cache is required in production: signup OTP sessions (seq_no) and
# signup/OTP rate limits are read across requests and must be consistent across
# all gunicorn/uvicorn workers. Point CACHE_URL at Redis (uses a separate DB
# index from the Celery broker on /0). In production it defaults to Redis;
# in dev it falls back to in-process LocMemCache so the app runs without Redis.
CACHE_URL = config('CACHE_URL', default='' if DEBUG else 'redis://localhost:6379/1')
if CACHE_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': CACHE_URL,
            'KEY_PREFIX': 'pms',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'pms-locmem',
        }
    }

# Celery configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# In development there is usually no broker/worker running, so run Celery tasks
# inline (synchronously, in-process) instead of dispatching them. This lets SMS
# and email tasks fire during a normal request without Redis. Defaults to DEBUG;
# set CELERY_TASK_ALWAYS_EAGER=False to force real dispatch even in dev.
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=DEBUG, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = False

# SMS delivery
# 'console' prints the message to the server terminal/log instead of calling the
# gateway — useful for local dev where the internal NTC SMS host is unreachable.
# 'gateway' performs the real HTTP call. Defaults to console in DEBUG.
SMS_BACKEND = config('SMS_BACKEND', default='console' if DEBUG else 'gateway')
SMS_API_URL = config(
    'SMS_API_URL',
    default='http://10.26.192.122:42399/updatedsmssender-1.0-SNAPSHOT/updatedsmssender/',
)
SMS_USERNAME = config('SMS_USERNAME', default='NtcSmsSender')
SMS_PASSWORD = config('SMS_PASSWORD', default='')
SMS_SYSTEM_ID = config('SMS_SYSTEM_ID', default='1')

# Email gateway (NTC email API). Read from .env; the email sender POSTs here.
EMAIL_API_URL = config(
    'EMAIL_API_URL',
    default='http://10.26.192.122:42399/updatedsmssender-1.0-SNAPSHOT/emailsender',
)

# NTC OTP service (used for login OTP and signup phone verification).
# Read from .env so the deployed host is honored instead of a hardcoded default.
NTC_OTP_BASE_URL = config('NTC_OTP_BASE_URL', default='http://10.26.192.122:8083')
NTC_OTP_TIMEOUT = config('NTC_OTP_TIMEOUT', default=10, cast=int)

# Scheduled tasks (requires `celery -A cms_backend beat` running alongside the worker)
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'sync-erp-employees-nightly': {
        'task': 'users.tasks.sync_erp_employees_task',
        # Run daily at 02:00 to refresh the EmployeeDetail directory from the ERP table.
        'schedule': crontab(hour=2, minute=0),
    },
}

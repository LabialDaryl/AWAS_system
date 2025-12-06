"""
Django settings for awas_project project.
"""

from pathlib import Path
from decouple import config, Csv
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'django_filters',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'billing.apps.BillingConfig',
    'payments.apps.PaymentsConfig',
    'complaints.apps.ComplaintsConfig',
    'core.apps.CoreConfig',
    
    # Notifications
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'awas_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'awas_project.wsgi.application'

# Database
# SQLite database for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# Static and Media Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

if DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:landing'

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Payment Gateway Settings
GCASH_API_KEY = config('GCASH_API_KEY', default='')
GCASH_API_SECRET = config('GCASH_API_SECRET', default='')
GCASH_MERCHANT_ID = config('GCASH_MERCHANT_ID', default='')
GCASH_SANDBOX = config('GCASH_SANDBOX', default=True, cast=bool)

PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE = config('PAYPAL_MODE', default='sandbox')

PAYMAYA_PUBLIC_KEY = config('PAYMAYA_PUBLIC_KEY', default='')
PAYMAYA_SECRET_KEY = config('PAYMAYA_SECRET_KEY', default='')
PAYMAYA_ENVIRONMENT = config('PAYMAYA_ENVIRONMENT', default='sandbox')

# Water Billing Settings
PUROK_CHOICES = [(i, f'Purok {i}') for i in range(1, 9)]
CONNECTION_TYPE_CHOICES = [
    ('residential', 'Residential'),
    ('commercial', 'Commercial'),
]

MINIMUM_CUBIC_METERS = config('MINIMUM_CUBIC_METERS', default=10, cast=int)
RATE_PER_CUBIC_METER = config('RATE_PER_CUBIC_METER', default=15.00, cast=float)
MINIMUM_CHARGE = config('MINIMUM_CHARGE', default=150.00, cast=float)
LATE_PAYMENT_PENALTY = config('LATE_PAYMENT_PENALTY', default=50.00, cast=float)
RECONNECTION_FEE = config('RECONNECTION_FEE', default=500.00, cast=float)

# Notifications settings
NOTIFICATIONS_USE_JSONFIELD = False  # We're using jsonfield instead of django-jsonfield
NOTIFICATIONS_SOFT_DELETE = True
NOTIFICATIONS_USE_ICONS = True

# Notification settings for the UI
NOTIFICATION_DAYS_BEFORE_DUE = config('NOTIFICATION_DAYS_BEFORE_DUE', default=5, cast=int)
NOTIFICATION_DAYS_BEFORE_DISCONNECTION = config('NOTIFICATION_DAYS_BEFORE_DISCONNECTION', default=1, cast=int)

# Celery Configuration (for background tasks)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Messages Framework
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Jazzmin Admin Theme Settings
JAZZMIN_SETTINGS = {
    "site_title": "AWAS Admin",
    "site_header": "AWAS Admin",
    "welcome_sign": "Welcome to AWAS Admin Panel",

    # Base (light) theme – keep using light as default
    "theme": "flatly",

    # UI/UX
    "navigation_expanded": True,

    # Load our custom assets for theme toggle and dark mode
    # For this Jazzmin version, these must be strings (not lists)
    "custom_css": "css/admin-theme.css",
    "custom_js": "js/admin-theme-toggle.js",
}

# Jazzmin UI Tweaks (colors and layout)
JAZZMIN_UI_TWEAKS = {
    # Light theme baseline
    "theme": "light",

    # Top bar (navbar) – light with info/blue tone
    "navbar": "navbar-white navbar-light",

    # Sidebar – light with info accent (blue-ish)
    "sidebar": "sidebar-light-info",
    "sidebar_fixed": True,
    "sidebar_unfold_hover": True,
    "sidebar_nav_child_indent": True,

    # Accent color (closest to aqua using Bootstrap's info)
    "accent": "info",

    # Typography
    "body_small_text": False,
    "footer_small_text": False,

    # Sticky action bar in change forms
    "actions_sticky_top": True,
}

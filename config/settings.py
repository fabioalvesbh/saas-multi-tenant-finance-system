"""
Configurações Django para o projeto de comunicação SaaS multi-tenant.

Gerado com Django 5.2.12 e adaptado para uso com django-tenants.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# Configurações básicas

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]


# Application definition (multi-tenant)

SHARED_APPS = [
    "django_tenants",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "tenant_management",
]

TENANT_APPS = [
    "core",
    "usuarios",
    "chat",
    "chamados",
]

INSTALLED_APPS = SHARED_APPS + TENANT_APPS

TENANT_MODEL = "tenant_management.Client"
TENANT_DOMAIN_MODEL = "tenant_management.Domain"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_tenants.middleware.TenantMainMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "usuarios.middleware.LastSeenMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Banco de dados (PostgreSQL com django-tenants)

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django_tenants.postgresql_backend"),
        "NAME": os.getenv("DJANGO_DB_NAME", "app_db"),
        "USER": os.getenv("DJANGO_DB_USER", "app_user"),
        "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", "app_password"),
        "HOST": os.getenv("DJANGO_DB_HOST", "db"),
        "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
    }
}

# Roteador de banco exigido pelo django-tenants
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)


# Validação de senha

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internacionalização

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Arquivos estáticos e mídia

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [
    BASE_DIR / "config" / "stick",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# E-mail

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.example.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "no-reply@example.com")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)


LOGIN_REDIRECT_URL = "chat:home"

# Base URL usada para gerar links de reunião (Jitsi/Meet/etc.)
MEETING_BASE_URL = os.getenv("MEETING_BASE_URL", "https://meet.example.com")


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


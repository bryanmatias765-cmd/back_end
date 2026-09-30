"""
Configuración del proyecto TIENDA HARDWARE (E-commerce de componentes PC).
EVA-2 Desarrollo Backend - Django REST Framework + PostgreSQL + JWT.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Variables de entorno: se leen desde el archivo .env (que NO se sube a GitHub)
# para no exponer contraseñas ni la SECRET_KEY en el repositorio.
# ---------------------------------------------------------------------------
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "clave-insegura-solo-para-desarrollo")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# ---------------------------------------------------------------------------
# Datos del alumno: se muestran en el footer de las vistas HTML base
# (inicio, navegador de la API de DRF y descripción de Swagger).
# ---------------------------------------------------------------------------
ALUMNO_NOMBRE = "Bryan Sandoval Morales"
ALUMNO_SECCION = os.environ.get("ALUMNO_SECCION", "Ingenieria en ciberseguridad")
ALUMNO_ANIO = "2026"

# ---------------------------------------------------------------------------
# Aplicaciones instaladas
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # permite invalidar el refresh en el logout
    "django_filters",
    "drf_spectacular",
    # Aplicación propia
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tienda_hardware.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # aquí sobrescribimos la plantilla de DRF (footer)
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "api.context_processors.datos_alumno",  # inyecta nombre/sección/año en los templates
            ],
        },
    },
]

WSGI_APPLICATION = "tienda_hardware.wsgi.application"

# ---------------------------------------------------------------------------
# Base de datos: PostgreSQL (NO SQLite), exigido por la evaluación.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "tienda_hardware"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
#  - Autenticación por JWT (Bearer token).
#  - Permiso por defecto: solo lectura para anónimos; cada vista define el suyo.
#  - django-filter + búsqueda + ordenamiento disponibles globalmente.
#  - drf-spectacular genera el esquema OpenAPI (Swagger).
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

# ---------------------------------------------------------------------------
# JWT: access de vida corta y refresh de vida larga. El "rol" se agrega como
# claim personalizado en api/serializers.py (RolTokenObtainPairSerializer).
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Swagger / OpenAPI (drf-spectacular) -> disponible en /api/docs/
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "API Tienda de Hardware y Componentes PC",
    "DESCRIPTION": (
        "API REST para un e-commerce de componentes informáticos "
        "(catálogo, carro persistente, checkout, control de stock).\n\n"
        f"**Alumno:** {ALUMNO_NOMBRE} | **Sección:** {ALUMNO_SECCION} | **Año:** {ALUMNO_ANIO}"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

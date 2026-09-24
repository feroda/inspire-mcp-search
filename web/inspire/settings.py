"""Django settings for the INSPIRE semantic search PoC."""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# set default values and casting
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "dev-only-insecure-key"),
    ALLOWED_HOSTS=(list, ["*"]),
    DB_HOST=(str, "db"),
    POSTGRES_PORT=(int, 5432),
    OLLAMA_URL=(str, "http://ollama:11434"),
    OLLAMA_EMBEDDING_MODEL=(str, "nomic-embed-text"),
    EMBEDDING_DIMENSIONS=(int, 768),
    INSPIRE_API_URL=(str, "https://inspirehep.net/api/literature"),
)
environ.Env.read_env()  # reading .env file

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django_extensions',
    'rest_framework',
    'papers',
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

ROOT_URLCONF = 'inspire.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'inspire.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env("POSTGRES_DB"),
        'USER': env("POSTGRES_USER"),
        'PASSWORD': env("POSTGRES_PASSWORD"),
        'HOST': env("DB_HOST"),
        'PORT': env("POSTGRES_PORT"),
    }
}

# The search endpoint is read-only and public: this is a demo over public
# INSPIRE-HEP metadata, so there is nothing to authenticate.
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'STATIC'

# == Retrieval settings ==

OLLAMA_URL = env("OLLAMA_URL")
OLLAMA_EMBEDDING_MODEL = env("OLLAMA_EMBEDDING_MODEL")

# Dimension is dictated by the embedding model; changing the model means a
# migration on the vector column plus a full re-embed of every row.
EMBEDDING_DIMENSIONS = env("EMBEDDING_DIMENSIONS")

# nomic-embed-text is trained asymmetrically: documents and queries must be
# prefixed differently or relevance degrades silently.
EMBEDDING_DOCUMENT_PREFIX = "search_document: "
EMBEDDING_QUERY_PREFIX = "search_query: "

INSPIRE_API_URL = env("INSPIRE_API_URL")
INSPIRE_RAW_CACHE = BASE_DIR / "data" / "inspire_raw.json"

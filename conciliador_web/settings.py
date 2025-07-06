import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 Seguridad y entorno
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '.onrender.com').split(',')

# 📦 Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# 🧩 Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 🌐 URL principal
ROOT_URLCONF = 'conciliador_web.urls'

# 🎨 Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'procesador', 'templates')],
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

# 🚀 WSGI
WSGI_APPLICATION = 'conciliador_web.wsgi.application'

# 🗄 Base de datos (SQLite por defecto)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 🔑 Validaciones de contraseña
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 🌎 Internacionalización
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 🧭 Archivos estáticos
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'procesador', 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 🆔 PK automático por defecto
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
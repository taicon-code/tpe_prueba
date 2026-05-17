"""
Entorno TEST.

BD sqlite en memoria. Axes deshabilitado (bloqueo en tests es ruido).
simple_history pasivo. Hashers rapidos. Logging mudo.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# BD en memoria (rapida + aislada por proceso)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Saltar migraciones en tests: crear tablas directamente desde el estado
# actual de los modelos. Necesario porque SQLite no soporta el _remake_table
# requerido por algunas migraciones historicas (0011_restructura_tsp).
# Los tests deben verificar el comportamiento ACTUAL, no la historia migracional.
class _SkipMigrations:
    def __contains__(self, item): return True
    def __getitem__(self, item): return None
MIGRATION_MODULES = _SkipMigrations()

# Hasher rapido para tests (NO usar en prod, es debil deliberadamente)
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Desactivar axes y simple_history en tests
INSTALLED_APPS = [a for a in INSTALLED_APPS if a not in ('axes', 'simple_history')]  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if 'axes' not in m]  # noqa: F405
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

# Cookies sin secure (no hay HTTPS en tests)
USE_SECURE_COOKIES = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging silencioso: solo console, nivel WARNING+
LOGGING['loggers'] = {  # noqa: F405
    'tpe_app': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    'tpe_app.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
}

# MEDIA en /tmp para que los tests no toquen OneDrive
import tempfile
MEDIA_ROOT = tempfile.mkdtemp(prefix='tpe_test_media_')

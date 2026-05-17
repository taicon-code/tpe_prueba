"""
Entorno DESARROLLO.

DEBUG=True. Cookies sin secure por default (LAN/HTTP). HSTS desactivado.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
USE_SECURE_COOKIES = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# StaticFilesStorage simple en dev (sin manifest hash)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Logger tpe_app a DEBUG en dev
LOGGING['loggers']['tpe_app']['level'] = 'DEBUG'  # noqa: F405

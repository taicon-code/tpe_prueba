"""
Entorno PRODUCCION.

DEBUG=False forzado. HSTS, SSL redirect y cookies secure activados.
Valida que SECRET_KEY no sea trivial y que ALLOWED_HOSTS este definido.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Sanity checks: si el usuario olvido configurar el .env, abortamos antes de
# levantar el servidor en lugar de arrancar con valores inseguros.
if not SECRET_KEY or SECRET_KEY.startswith('django-insecure-'):  # noqa: F405
    raise RuntimeError(
        'SECRET_KEY no esta configurada o es la generada por startproject. '
        'Genere una nueva y agreguela al .env de produccion.'
    )

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['127.0.0.1', 'localhost']:  # noqa: F405
    raise RuntimeError(
        'ALLOWED_HOSTS debe contener al menos un hostname real de produccion. '
        'Defina ALLOWED_HOSTS en .env (ej: tpe.ejercito.bo,intranet.tpe.bo).'
    )

# HTTPS obligatorio en prod
USE_SECURE_COOKIES = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)  # noqa: F405
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)  # noqa: F405

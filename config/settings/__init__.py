"""
Selector de entorno para settings.

Compatibilidad con codigo legacy: DJANGO_SETTINGS_MODULE=config.settings
sigue funcionando y carga el modulo correcto segun la variable DJANGO_ENV.

DJANGO_ENV puede ser:
  - 'dev'  (default)  -> config.settings.dev
  - 'prod'            -> config.settings.prod
  - 'test'            -> config.settings.test

Para evitar la indireccion se puede tambien apuntar directamente:
  DJANGO_SETTINGS_MODULE=config.settings.prod

Aviso: si DJANGO_ENV='prod' y el .env no tiene SECRET_KEY/ALLOWED_HOSTS
configurados, prod.py aborta con RuntimeError antes de levantar el servidor.
"""
import os

_env = os.environ.get('DJANGO_ENV', 'dev').lower()

if _env == 'prod':
    from .prod import *  # noqa: F401, F403
elif _env == 'test':
    from .test import *  # noqa: F401, F403
else:
    from .dev import *  # noqa: F401, F403

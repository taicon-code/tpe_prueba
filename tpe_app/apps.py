from django.apps import AppConfig


class TpeAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tpe_app'

    def ready(self):
        # Registrar Django checks (warning si faltan feriados del ano, etc.)
        from . import checks  # noqa: F401
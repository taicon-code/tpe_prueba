"""
Validadores de contrasena adicionales al estandar de Django.

Se enchufan en settings.AUTH_PASSWORD_VALIDATORS y se aplican en:
  - User.objects.create_user / create_superuser (cuando se llama
    explicitamente con validate_password)
  - Vista de cambio de contrasena
  - Admin de Django (formulario de set password)
"""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplejidadPasswordValidator:
    """Exige al menos una mayuscula, una minuscula, un digito y un simbolo."""

    SIMBOLOS = r"!@#$%^&*()\-_=+\[\]{};:,.<>/?\\|`~'\""

    def validate(self, password, user=None):
        errores = []
        if not re.search(r'[A-Z]', password):
            errores.append(_('al menos una letra MAYUSCULA'))
        if not re.search(r'[a-z]', password):
            errores.append(_('al menos una letra minuscula'))
        if not re.search(r'\d', password):
            errores.append(_('al menos un digito'))
        if not re.search(f'[{self.SIMBOLOS}]', password):
            errores.append(_('al menos un simbolo (!@#$% ...)'))
        if errores:
            raise ValidationError(
                _('La contrasena debe contener: %(req)s.') % {'req': ', '.join(errores)},
                code='password_no_complexity',
            )

    def get_help_text(self):
        return _(
            'Su contrasena debe contener al menos una MAYUSCULA, una minuscula, '
            'un digito y un simbolo (!@#$% etc.).'
        )

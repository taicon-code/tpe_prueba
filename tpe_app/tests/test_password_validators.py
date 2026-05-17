"""Tests para tpe_app.utils.password_validators."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tpe_app.utils.password_validators import ComplejidadPasswordValidator


class ComplejidadPasswordValidatorTests(SimpleTestCase):
    def setUp(self):
        self.validator = ComplejidadPasswordValidator()

    def test_acepta_password_completa(self):
        # Mayuscula + minuscula + digito + simbolo
        self.assertIsNone(self.validator.validate('Password123!'))

    def test_rechaza_sin_mayuscula(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate('password123!')
        self.assertIn('MAYUSCULA', str(ctx.exception))

    def test_rechaza_sin_minuscula(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate('PASSWORD123!')
        self.assertIn('minuscula', str(ctx.exception))

    def test_rechaza_sin_digito(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate('Password!!!')
        self.assertIn('digito', str(ctx.exception))

    def test_rechaza_sin_simbolo(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate('Password1234')
        self.assertIn('simbolo', str(ctx.exception))

    def test_rechaza_solo_letras_minusculas(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate('aaaaaaaaaaaa')
        msg = str(ctx.exception)
        self.assertIn('MAYUSCULA', msg)
        self.assertIn('digito', msg)
        self.assertIn('simbolo', msg)

    def test_help_text_no_vacio(self):
        self.assertTrue(self.validator.get_help_text())

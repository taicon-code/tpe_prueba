"""Tests para tpe_app.services.plazos."""
from datetime import date

from django.test import TestCase

from tpe_app.services.plazos import (
    add_business_days,
    calcular_fecha_limite_ejecutoria,
    calcular_fecha_limite_rap,
    calcular_fecha_limite_rr,
)


class AddBusinessDaysTests(TestCase):
    def test_none_input_retorna_none(self):
        self.assertIsNone(add_business_days(None, 5))

    def test_suma_dias_habiles_lunes_a_lunes(self):
        # Lunes 2026-04-13 + 5 dias habiles = lunes 2026-04-20
        resultado = add_business_days(date(2026, 4, 13), 5)
        self.assertEqual(resultado, date(2026, 4, 20))

    def test_salta_fines_de_semana(self):
        # Viernes 2026-04-17 + 1 dia habil = lunes 2026-04-20
        resultado = add_business_days(date(2026, 4, 17), 1)
        self.assertEqual(resultado, date(2026, 4, 20))

    def test_salta_feriado_1_mayo(self):
        # 2026-04-30 (jueves) + 1 dia habil debe saltar 1-mayo (feriado) → lunes 2026-05-04
        # 1-mayo de 2026 es viernes y es feriado
        resultado = add_business_days(date(2026, 4, 30), 1)
        self.assertEqual(resultado, date(2026, 5, 4))


class CalcularFechaLimiteTests(TestCase):
    def test_rr_15_dias_habiles(self):
        # 2026-04-01 (miercoles) + 15 dias habiles
        resultado = calcular_fecha_limite_rr(date(2026, 4, 1))
        # 15 dias habiles desde mier 1-abr saltando fines de semana
        self.assertEqual(resultado, date(2026, 4, 23))

    def test_rap_3_dias_habiles(self):
        # 2026-04-01 (mier) + 3 dias habiles, saltando 04-03 (feriado Viernes
        # Santo en Bolivia) y fin de semana = martes 2026-04-07.
        resultado = calcular_fecha_limite_rap(date(2026, 4, 1))
        self.assertEqual(resultado, date(2026, 4, 7))

    def test_ejecutoria_post_rr_15_dias(self):
        # Mismo plazo que RR
        self.assertEqual(
            calcular_fecha_limite_ejecutoria(date(2026, 4, 1)),
            calcular_fecha_limite_rr(date(2026, 4, 1)),
        )

    def test_fecha_none_retorna_none(self):
        self.assertIsNone(calcular_fecha_limite_rr(None))
        self.assertIsNone(calcular_fecha_limite_rap(None))

"""Tests para tpe_app.services.plazos."""
from datetime import date

from django.test import TestCase

from tpe_app.services.plazos import (
    PLAZO_EJECUTORIA_POST_RR,
    PLAZO_RAP,
    PLAZO_RR,
    PlazoLegal,
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


class PlazoLegalTests(TestCase):
    def test_etiqueta_incluye_dias_y_articulo(self):
        p = PlazoLegal(dias_habiles=7, articulo='Art. 42 RFD-FFAA')
        self.assertIn('7 dias habiles', p.etiqueta)
        self.assertIn('Art. 42 RFD-FFAA', p.etiqueta)

    def test_calcular_None_retorna_None(self):
        self.assertIsNone(PLAZO_RR.calcular(None))

    def test_constantes_rr_rap_ejecutoria_son_PlazoLegal(self):
        self.assertIsInstance(PLAZO_RR, PlazoLegal)
        self.assertIsInstance(PLAZO_RAP, PlazoLegal)
        self.assertIsInstance(PLAZO_EJECUTORIA_POST_RR, PlazoLegal)

    def test_articulos_no_vacios(self):
        # Si alguien borra una cita normativa por accidente, este test lo detecta
        self.assertTrue(PLAZO_RR.articulo.strip())
        self.assertTrue(PLAZO_RAP.articulo.strip())
        self.assertTrue(PLAZO_EJECUTORIA_POST_RR.articulo.strip())

    def test_dias_habiles_rr_es_15(self):
        self.assertEqual(PLAZO_RR.dias_habiles, 15)
        self.assertEqual(PLAZO_RAP.dias_habiles, 3)
        self.assertEqual(PLAZO_EJECUTORIA_POST_RR.dias_habiles, 15)

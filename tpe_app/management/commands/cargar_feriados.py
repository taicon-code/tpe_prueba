"""Carga feriados nacionales de Bolivia para un ano dado.

Uso:
    python manage.py cargar_feriados 2027
    python manage.py cargar_feriados 2027 --replace   (sobrescribe existentes)

Maneja:
    - Feriados de fecha fija (Ano Nuevo, Dia del Trabajador, Navidad, etc.)
    - Feriados moviles (Carnaval, Viernes Santo, Corpus Christi) calculados
      a partir de la fecha de Pascua (algoritmo Anonymous Gregorian).

Notas:
    - 21 de junio (Ano Nuevo Andino-Amazonico) es feriado nacional desde 2010.
    - Las fechas de Corpus Christi y los carnavales mueven cada ano segun Pascua.
    - 22-jun (Ano Nuevo Aymara) y 6-ago (Independencia) son fijos.
"""
import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

security_log = logging.getLogger('tpe_app.security')


def _pascua(year):
    """Devuelve la fecha del Domingo de Pascua para el ano dado (algoritmo Meeus)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def feriados_bolivia(year):
    """Lista de (fecha, descripcion) feriados nacionales de Bolivia para el ano."""
    pascua = _pascua(year)
    return [
        (date(year, 1, 1),   'Ano Nuevo'),
        (date(year, 1, 22),  'Dia del Estado Plurinacional'),
        (pascua - timedelta(days=48), 'Carnaval (Lunes)'),
        (pascua - timedelta(days=47), 'Carnaval (Martes)'),
        (pascua - timedelta(days=2),  'Viernes Santo'),
        (date(year, 5, 1),   'Dia del Trabajador'),
        (pascua + timedelta(days=60), 'Corpus Christi'),
        (date(year, 6, 21),  'Ano Nuevo Andino-Amazonico'),
        (date(year, 8, 6),   'Dia de la Independencia'),
        (date(year, 11, 2),  'Dia de Todos los Difuntos'),
        (date(year, 12, 25), 'Navidad'),
    ]


class Command(BaseCommand):
    help = 'Carga los feriados nacionales de Bolivia para un ano en la tabla FeriadoBolivia.'

    def add_arguments(self, parser):
        parser.add_argument('anio', type=int, help='Ano a cargar (ej: 2027)')
        parser.add_argument(
            '--replace', action='store_true',
            help='Si una fecha ya existe, sobrescribir su descripcion.',
        )

    def handle(self, *args, **opts):
        from tpe_app.models import FeriadoBolivia

        anio = opts['anio']
        replace = opts['replace']

        if anio < 2010 or anio > 2100:
            raise CommandError(f'Ano fuera de rango razonable (2010-2100): {anio}')

        feriados = feriados_bolivia(anio)
        creados, actualizados, omitidos = 0, 0, 0

        for fecha, descripcion in feriados:
            existente = FeriadoBolivia.objects.filter(fecha=fecha).first()
            if existente:
                if replace and existente.descripcion != descripcion:
                    existente.descripcion = descripcion
                    existente.anio = anio
                    existente.save(update_fields=['descripcion', 'anio'])
                    actualizados += 1
                    self.stdout.write(f'  ~ {fecha} {descripcion} (actualizado)')
                else:
                    omitidos += 1
                    self.stdout.write(f'  - {fecha} ya existe ({existente.descripcion})')
            else:
                FeriadoBolivia.objects.create(fecha=fecha, descripcion=descripcion, anio=anio)
                creados += 1
                self.stdout.write(f'  + {fecha} {descripcion}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Ano {anio}: creados={creados}, actualizados={actualizados}, omitidos={omitidos}'
        ))
        security_log.info(
            'FERIADOS_LOADED anio=%s creados=%s actualizados=%s omitidos=%s',
            anio, creados, actualizados, omitidos,
        )

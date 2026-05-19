"""
Comando para cargar o actualizar feriados de Bolivia
Uso:
  python manage.py cargar_feriados --año 2027
  python manage.py cargar_feriados --limpiar 2026  # borra feriados del año anterior
"""

from django.core.management.base import BaseCommand
from tpe_app.models import FeriadoBolivia
from datetime import date


FERIADOS_BOLIVIA = {
    2026: [
        (date(2026, 1, 23), "Aniversario de la Revolución Democrática"),
        (date(2026, 2, 16), "Lunes de Carnaval"),
        (date(2026, 2, 17), "Martes de Carnaval"),
        (date(2026, 4, 3), "Viernes de Dolores"),
        (date(2026, 5, 1), "Día del Trabajo"),
        (date(2026, 6, 4), "Día de la Bandera"),
        (date(2026, 6, 5), "Corpus Christi"),
        (date(2026, 6, 22), "Aniversario de la Batalla de la Coronilla"),
        (date(2026, 8, 6), "Independencia de Bolivia"),
        (date(2026, 8, 7), "Día de los Derechos Cívicos"),
        (date(2026, 11, 2), "Día de Difuntos"),
        (date(2026, 12, 25), "Navidad"),
    ],
    2027: [
        (date(2027, 1, 23), "Aniversario de la Revolución Democrática"),
        (date(2027, 2, 8), "Lunes de Carnaval"),
        (date(2027, 2, 9), "Martes de Carnaval"),
        (date(2027, 3, 26), "Viernes de Dolores"),
        (date(2027, 5, 1), "Día del Trabajo"),
        (date(2027, 6, 4), "Día de la Bandera"),
        (date(2027, 5, 28), "Corpus Christi"),
        (date(2027, 6, 22), "Aniversario de la Batalla de la Coronilla"),
        (date(2027, 8, 6), "Independencia de Bolivia"),
        (date(2027, 8, 7), "Día de los Derechos Cívicos"),
        (date(2027, 11, 2), "Día de Difuntos"),
        (date(2027, 12, 25), "Navidad"),
    ],
}


class Command(BaseCommand):
    help = "Carga o actualiza los feriados de Bolivia en la BD"

    def add_arguments(self, parser):
        parser.add_argument('--año', type=int, help='Año específico a cargar')
        parser.add_argument('--limpiar', type=int, help='Borrar feriados de un año antes de cargar')

    def handle(self, *args, **options):
        año = options.get('año')
        limpiar = options.get('limpiar')

        if limpiar:
            count = FeriadoBolivia.objects.filter(anio=limpiar).delete()[0]
            self.stdout.write(
                self.style.WARNING(f"✓ Borrados {count} feriados de {limpiar}")
            )

        años_a_cargar = [año] if año else FERIADOS_BOLIVIA.keys()

        for anio in años_a_cargar:
            if anio not in FERIADOS_BOLIVIA:
                self.stdout.write(
                    self.style.ERROR(f"✗ No hay feriados definidos para {anio}")
                )
                continue

            creados = 0
            actualizados = 0

            for fecha, descripcion in FERIADOS_BOLIVIA[anio]:
                obj, created = FeriadoBolivia.objects.update_or_create(
                    fecha=fecha,
                    defaults={'descripcion': descripcion, 'anio': anio}
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {anio}: {creados} nuevos, {actualizados} actualizados"
                )
            )

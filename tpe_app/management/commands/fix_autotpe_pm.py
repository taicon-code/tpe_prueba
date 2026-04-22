"""
Comando para asignar PM faltante en autos TPE basado en:
1. Si tiene resolucion vinculada → obtener PM de la resolución
2. Si no → obtener el primer militar del sumario
3. Si no hay militares → advertencia

Uso: python manage.py fix_autotpe_pm
"""

from django.core.management.base import BaseCommand
from tpe_app.models import AUTOTPE

class Command(BaseCommand):
    help = 'Asigna PM faltante en autos TPE basado en resolución o primer militar del sumario'

    def handle(self, *args, **options):
        autos_sin_pm = AUTOTPE.objects.filter(pm__isnull=True).select_related('resolucion', 'sim')
        self.stdout.write(f"🔍 Encontrados {autos_sin_pm.count()} autos sin PM\n")

        count = 0
        ignorados = 0

        for auto in autos_sin_pm:
            pm = None

            # Estrategia 1: Si tiene resolución vinculada, obtener PM de ahí
            if auto.resolucion and auto.resolucion.pm:
                pm = auto.resolucion.pm
                origen = "resolución"

            # Estrategia 2: Obtener el primer militar del sumario
            if not pm:
                pm = auto.sim.militares.first()
                origen = "sumario"

            # Estrategia 3: Nada encontrado
            if not pm:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Auto {auto.TPE_NUM} ({auto.get_TPE_TIPO_display()}) - Sumario {auto.sim.SIM_COD} sin militares"
                    )
                )
                ignorados += 1
                continue

            # Guardar
            auto.pm = pm
            auto.save()
            count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Auto {auto.TPE_NUM} ({auto.get_TPE_TIPO_display()}) - PM desde {origen}: {pm.PM_GRADO} {pm.PM_PATERNO}, {pm.PM_NOMBRE}"
                )
            )

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"✅ {count} autos TPE corregidos"))
        if ignorados > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  {ignorados} autos no se pudieron corregir (sin militares)"))

from django.core.management.base import BaseCommand
from django.db.models import Q
from tpe_app.models import RES, DICTAMEN


class Command(BaseCommand):
    help = 'Rellenar el campo pm_id en RES existentes basándose en su dictamen asociado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué cambios se harían sin ejecutarlos',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        # RES que tienen pm_id vacío pero tienen dictamen asociado
        res_sin_pm = RES.objects.filter(pm_id__isnull=True).select_related('dictamen')

        if not res_sin_pm.exists():
            self.stdout.write(
                self.style.SUCCESS('✅ No hay RES con pm_id vacío. Nada que hacer.')
            )
            return

        actualizados = 0
        sin_pm_en_dictamen = 0
        errores = []

        for res in res_sin_pm:
            try:
                # Si la RES tiene dictamen y el dictamen tiene PM, asignar el PM
                if res.dictamen and res.dictamen.pm_id:
                    if not dry_run:
                        res.pm = res.dictamen.pm
                        res.save()
                    actualizados += 1
                    self.stdout.write(
                        f"  ✓ RES {res.RES_NUM}: asignado PM {res.dictamen.pm.PM_PATERNO}"
                    )
                else:
                    # No hay PM en el dictamen
                    sin_pm_en_dictamen += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️ RES {res.RES_NUM}: No tiene PM en su dictamen asociado"
                        )
                    )
            except Exception as e:
                errores.append(f"RES {res.RES_NUM}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"  ❌ RES {res.RES_NUM}: Error — {str(e)}")
                )

        # Resumen
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"📋 DRY-RUN: Se habrían actualizado {actualizados} RES")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Actualizadas: {actualizados} RES")
            )

        self.stdout.write(
            self.style.WARNING(f"⚠️ Sin PM en dictamen: {sin_pm_en_dictamen} RES")
        )

        if errores:
            self.stdout.write(self.style.ERROR(f"❌ Errores: {len(errores)}"))
            for error in errores:
                self.stdout.write(f"   - {error}")

        self.stdout.write("=" * 60)

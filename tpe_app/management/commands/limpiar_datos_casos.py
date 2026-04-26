from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Elimina TODOS los datos de casos, sumarios y militares. Conserva usuarios, abogados y vocales.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirmar que desea eliminar todos los datos (REQUERIDO para ejecutar)',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(self.style.WARNING("""
╔══════════════════════════════════════════════════════════════╗
║          ⚠️  ADVERTENCIA - OPERACIÓN DESTRUCTIVA  ⚠️          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Este comando eliminará PERMANENTEMENTE todos los datos de:  ║
║                                                              ║
║  ❌ Sumarios (SIM)                                           ║
║  ❌ Personal Militar (PM)                                    ║
║  ❌ Agendas                                                  ║
║  ❌ Dictámenes                                               ║
║  ❌ Resoluciones (RES)                                       ║
║  ❌ Recursos de Reconsideración (RR)                         ║
║  ❌ Autos TPE / TSP                                          ║
║  ❌ Recursos de Apelación (RAP)                              ║
║  ❌ RAEE                                                     ║
║  ❌ Custodias de Carpetas                                    ║
║  ❌ Documentos Adjuntos (PDFs)                               ║
║                                                              ║
║  ✅ SE CONSERVARÁ:                                           ║
║  ✅ Usuarios del sistema                                     ║
║  ✅ Abogados (ABOG)                                          ║
║  ✅ Vocales TPE                                              ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Para ejecutar, agregue el flag --confirmar:                 ║
║                                                              ║
║  python manage.py limpiar_datos_casos --confirmar            ║
╚══════════════════════════════════════════════════════════════╝
"""))
            return

        # Importar modelos dentro del handle para evitar imports circulares
        from tpe_app.models import (
            SIM, PM, PM_SIM, ABOG_SIM, CustodiaSIM,
            AGENDA, DICTAMEN, AUTOTPE,
            AUTOTSP, DocumentoAdjunto, VOCAL_TPE,
            Resolucion, RecursoTSP,
        )

        self.stdout.write("\n🔄 Iniciando limpieza de datos...\n")

        with transaction.atomic():
            # Orden importante: primero las dependientes, luego las principales

            n = RecursoTSP.objects.filter(instancia='ACLARACION_ENMIENDA').count()
            RecursoTSP.objects.filter(instancia='ACLARACION_ENMIENDA').delete()
            self.stdout.write(f"  ❌ RAEE (RecursoTSP.ACLARACION_ENMIENDA) eliminados: {n}")

            n = AUTOTSP.objects.count()
            AUTOTSP.objects.all().delete()
            self.stdout.write(f"  ❌ Autos TSP eliminados: {n}")

            n = RecursoTSP.objects.filter(instancia='APELACION').count()
            RecursoTSP.objects.filter(instancia='APELACION').delete()
            self.stdout.write(f"  ❌ Apelaciones (RecursoTSP.APELACION) eliminadas: {n}")

            n = AUTOTPE.objects.count()
            AUTOTPE.objects.all().delete()
            self.stdout.write(f"  ❌ Autos TPE eliminados: {n}")

            n = Resolucion.objects.filter(instancia='RECONSIDERACION').count()
            Resolucion.objects.filter(instancia='RECONSIDERACION').delete()
            self.stdout.write(f"  ❌ Reconsideraciones (Resolucion.RECONSIDERACION) eliminadas: {n}")

            n = Resolucion.objects.filter(instancia='PRIMERA').count()
            Resolucion.objects.filter(instancia='PRIMERA').delete()
            self.stdout.write(f"  ❌ Resoluciones (Resolucion.PRIMERA) eliminadas: {n}")

            n = DICTAMEN.objects.count()
            DICTAMEN.objects.all().delete()
            self.stdout.write(f"  ❌ Dictámenes eliminados: {n}")

            n = CustodiaSIM.objects.count()
            CustodiaSIM.objects.all().delete()
            self.stdout.write(f"  ❌ Custodias de carpetas eliminadas: {n}")

            n = ABOG_SIM.objects.count()
            ABOG_SIM.objects.all().delete()
            self.stdout.write(f"  ❌ Asignaciones Abogado-SIM eliminadas: {n}")

            n = PM_SIM.objects.count()
            PM_SIM.objects.all().delete()
            self.stdout.write(f"  ❌ Vinculaciones PM-SIM eliminadas: {n}")

            n = AGENDA.objects.count()
            AGENDA.objects.all().delete()
            self.stdout.write(f"  ❌ Agendas eliminadas: {n}")

            n = DocumentoAdjunto.objects.count()
            DocumentoAdjunto.objects.all().delete()
            self.stdout.write(f"  ❌ Documentos adjuntos (PDFs) eliminados: {n}")

            n = SIM.objects.count()
            SIM.objects.all().delete()
            self.stdout.write(f"  ❌ Sumarios (SIM) eliminados: {n}")

            # Borrar Vocales TPE antes que PM (FK RESTRICT)
            n = VOCAL_TPE.objects.count()
            VOCAL_TPE.objects.all().delete()
            self.stdout.write(f"  ❌ Vocales TPE eliminados: {n} (deberán re-registrarse)")

            n = PM.objects.count()
            PM.objects.all().delete()
            self.stdout.write(f"  ❌ Personal Militar (PM) eliminados: {n}")

        from tpe_app.models import ABOG
        from django.contrib.auth.models import User

        self.stdout.write(self.style.SUCCESS(f"""
╔══════════════════════════════════════════════════════════════╗
║                ✅ LIMPIEZA COMPLETADA                        ║
╠══════════════════════════════════════════════════════════════╣
║  DATOS CONSERVADOS:                                          ║
║    👤 Usuarios del sistema : {User.objects.count():>4}                         ║
║    ⚖️  Abogados             : {ABOG.objects.count():>4}                         ║
╠══════════════════════════════════════════════════════════════╣
║  ⚠️  PENDIENTE MANUAL:                                       ║
║    Volver a registrar los Vocales TPE (Presidente,           ║
║    Vicepresidente, Vocal, Secretario de Actas)               ║
╚══════════════════════════════════════════════════════════════╝
"""))

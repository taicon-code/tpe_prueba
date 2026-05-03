"""
Comando Django para importar datos históricos desde Excel (SOLO ACTUADOS).

Uso:
    python manage.py import_actuados_historicos --file plantilla_importacion_historico.xlsx
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tpe_app.models import PM, SIM, PM_SIM, Resolucion, RecursoTSP, AUTOTPE, AUTOTSP, DocumentoAdjunto, Notificacion
import pandas as pd
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa datos históricos (solo actuados) desde Excel'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='plantilla_importacion_historico.xlsx',
                            help='Ruta del archivo Excel')

    def handle(self, *args, **options):
        archivo = options['file']

        try:
            xls = pd.ExcelFile(archivo)
        except FileNotFoundError:
            raise CommandError(f'Archivo no encontrado: {archivo}')

        self.stdout.write(self.style.SUCCESS(f'\n📥 Iniciando importación desde {archivo}...\n'))

        try:
            with transaction.atomic():
                # 1. PM
                self._importar_pm(xls)
                # 2. SIM
                self._importar_sim(xls)
                # 3. PM_SIM
                self._importar_pm_sim(xls)
                # 4. Resoluciones
                self._importar_resoluciones(xls)
                # 5. Autos TPE
                self._importar_autos_tpe(xls)
                # 6. Recursos TSP
                self._importar_recursos_tsp(xls)
                # 7. Autos TSP
                self._importar_autos_tsp(xls)
                # 8. Documentos Adjuntos
                self._importar_documentos_adjuntos(xls)

            self.stdout.write(self.style.SUCCESS('\n✅ Importación completada exitosamente!\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error en importación: {str(e)}\n'))
            raise CommandError(str(e))

    def _importar_pm(self, xls):
        """Importa Personal Militar."""
        self.stdout.write('1️⃣  Importando PM...')

        df = pd.read_excel(xls, sheet_name='1_PM_Historico')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                PM.objects.update_or_create(
                    ci=str(row['ci']).strip(),
                    defaults={
                        'paterno': str(row['paterno']).strip().upper() if pd.notna(row['paterno']) else '',
                        'materno': str(row['materno']).strip().upper() if pd.notna(row['materno']) else '',
                        'nombre': str(row['nombre']).strip().upper() if pd.notna(row['nombre']) else '',
                        'grado': str(row['grado']).strip().upper() if pd.notna(row['grado']) else '',
                        'arma': str(row['arma']).strip().upper() if pd.notna(row['arma']) else '',
                        'especialidad': str(row['especialidad']).strip().upper() if pd.notna(row['especialidad']) else '',
                        'anio_promocion': int(row['anio_promocion']) if pd.notna(row['anio_promocion']) else None,
                        'escalafon': str(row['escalafon']).strip().upper() if pd.notna(row['escalafon']) else '',
                    }
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} PM importados'))

    def _importar_sim(self, xls):
        """Importa Sumarios."""
        self.stdout.write('2️⃣  Importando SIM...')

        df = pd.read_excel(xls, sheet_name='2_SIM_Historico')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                sim_id = int(row['id']) if pd.notna(row['id']) else None
                origen_id = int(row['origen_id']) if pd.notna(row['origen_id']) else None

                defaults = {
                    'codigo': str(row['codigo']).strip().upper(),
                    'version': int(row['version']) if pd.notna(row['version']) else 1,
                    'fecha_ingreso': pd.to_datetime(row['fecha_ingreso']).date() if pd.notna(row['fecha_ingreso']) else None,
                    'objeto': str(row['objeto']).strip().upper() if pd.notna(row['objeto']) else '',
                    'resumen': str(row['resumen']).strip().upper() if pd.notna(row['resumen']) else '',
                    'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                    'estado': str(row['estado']).strip() if pd.notna(row['estado']) else 'PARA_AGENDA',
                    'fase': str(row['fase']).strip() if pd.notna(row['fase']) else 'PARA_AGENDA',
                }

                if origen_id:
                    try:
                        defaults['origen'] = SIM.objects.get(id=origen_id)
                    except SIM.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  SIM origen_id={origen_id} no existe (fila {idx + 2})'))

                SIM.objects.update_or_create(
                    id=sim_id,
                    defaults=defaults
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} SIM importados'))

    def _importar_pm_sim(self, xls):
        """Importa relaciones PM ↔ SIM."""
        self.stdout.write('3️⃣  Importando PM_SIM...')

        df = pd.read_excel(xls, sheet_name='3_PM_SIM')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                sim = SIM.objects.get(id=int(row['sim_id']))
                pm = PM.objects.get(ci=str(row['pm_ci']).strip())

                PM_SIM.objects.update_or_create(
                    pm=pm,
                    sim=sim,
                    defaults={
                        'grado_en_fecha': str(row['grado_en_fecha']).strip().upper() if pd.notna(row['grado_en_fecha']) else '',
                    }
                )
            except (SIM.DoesNotExist, PM.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} PM_SIM importados'))

    def _importar_resoluciones(self, xls):
        """Importa Resoluciones (1RA y RR) + Notificaciones por separado."""
        self.stdout.write('4️⃣  Importando Resoluciones...')

        df = pd.read_excel(xls, sheet_name='4_Resoluciones')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                sim = SIM.objects.get(id=int(row['sim_id']))
                pm = PM.objects.get(ci=str(row['pm_ci']).strip())

                numero = str(row['numero']).strip() if pd.notna(row['numero']) else ''
                instancia = str(row['instancia']).strip() if pd.notna(row['instancia']) else 'PRIMERA'

                # Crear/actualizar Resolución SIN campos de notificación
                defaults = {
                    'sim': sim,
                    'pm': pm,
                    'numero': numero,
                    'instancia': instancia,
                    'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                    'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                    'fecha_presentacion': pd.to_datetime(row['fecha_presentacion']).date() if pd.notna(row['fecha_presentacion']) else None,
                    'fecha_limite': pd.to_datetime(row['fecha_limite']).date() if pd.notna(row['fecha_limite']) else None,
                    'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
                }

                resolucion, _ = Resolucion.objects.update_or_create(
                    numero=numero,
                    instancia=instancia,
                    defaults=defaults
                )

                # Crear Notificacion SEPARADAMENTE si hay datos
                if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                    notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                    valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                    if notif_tipo not in valid_tipos:
                        notif_tipo = 'FIRMA'

                    notif_fecha = pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None
                    notif_a = str(row['notif_a']).strip() if pd.notna(row['notif_a']) else ''

                    Notificacion.objects.update_or_create(
                        resolucion=resolucion,
                        defaults={
                            'tipo': notif_tipo,
                            'notificado_a': notif_a,
                            'fecha': notif_fecha,
                            'hora': None,
                        }
                    )

            except (SIM.DoesNotExist, PM.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Resoluciones importadas'))

    def _importar_autos_tpe(self, xls):
        """Importa Autos TPE + Notificaciones por separado."""
        self.stdout.write('5️⃣  Importando Autos TPE...')

        df = pd.read_excel(xls, sheet_name='5_Autos_TPE')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                sim = SIM.objects.get(id=int(row['sim_id']))
                pm = PM.objects.get(ci=str(row['pm_ci']).strip())

                numero_auto = str(row['numero']).strip() if pd.notna(row['numero']) else ''

                # Crear/actualizar Auto TPE SIN campos de notificación
                autotpe, _ = AUTOTPE.objects.update_or_create(
                    sim=sim,
                    pm=pm,
                    numero=numero_auto,
                    defaults={
                        'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                        'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                        'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
                        'memo_numero': str(row['memo_numero']).strip() if pd.notna(row['memo_numero']) else '',
                        'memo_fecha': pd.to_datetime(row['memo_fecha']).date() if pd.notna(row['memo_fecha']) else None,
                        'memo_fecha_entrega': pd.to_datetime(row['memo_fecha_entrega']).date() if pd.notna(row['memo_fecha_entrega']) else None,
                    }
                )

                # Crear Notificacion por separado
                if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                    notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                    valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                    if notif_tipo not in valid_tipos:
                        notif_tipo = 'FIRMA'

                    Notificacion.objects.update_or_create(
                        autotpe=autotpe,
                        defaults={
                            'tipo': notif_tipo,
                            'notificado_a': str(row['notif_a']).strip() if pd.notna(row['notif_a']) else '',
                            'fecha': pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None,
                            'hora': None,
                        }
                    )

            except (SIM.DoesNotExist, PM.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Autos TPE importados'))

    def _importar_recursos_tsp(self, xls):
        """Importa Recursos TSP (RAP y RAEE) + Notificaciones por separado."""
        self.stdout.write('6️⃣  Importando Recursos TSP...')

        df = pd.read_excel(xls, sheet_name='6_Recursos_TSP')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                sim = SIM.objects.get(id=int(row['sim_id']))
                pm = PM.objects.get(ci=str(row['pm_ci']).strip())

                numero_oficio = str(row['numero_oficio']).strip() if pd.notna(row['numero_oficio']) else ''

                # Crear/actualizar Recurso TSP SIN campos de notificación
                recurso, _ = RecursoTSP.objects.update_or_create(
                    sim=sim,
                    pm=pm,
                    numero_oficio=numero_oficio,
                    defaults={
                        'instancia': str(row['instancia']).strip() if pd.notna(row['instancia']) else 'APELACION',
                        'fecha_oficio': pd.to_datetime(row['fecha_oficio']).date() if pd.notna(row['fecha_oficio']) else None,
                        'fecha_presentacion': pd.to_datetime(row['fecha_presentacion']).date() if pd.notna(row['fecha_presentacion']) else None,
                        'fecha_limite': pd.to_datetime(row['fecha_limite']).date() if pd.notna(row['fecha_limite']) else None,
                        'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                        'numero': str(row['numero']).strip() if pd.notna(row['numero']) else '',
                        'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                        'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
                    }
                )

                # Crear Notificacion por separado
                if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                    notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                    valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                    if notif_tipo not in valid_tipos:
                        notif_tipo = 'FIRMA'

                    Notificacion.objects.update_or_create(
                        recurso_tsp=recurso,
                        defaults={
                            'tipo': notif_tipo,
                            'notificado_a': str(row['notif_a']).strip() if pd.notna(row['notif_a']) else '',
                            'fecha': pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None,
                            'hora': None,
                        }
                    )

            except (SIM.DoesNotExist, PM.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Recursos TSP importados'))

    def _importar_autos_tsp(self, xls):
        """Importa Autos TSP (respuesta a RAP/RAEE) + Notificaciones por separado."""
        self.stdout.write('7️⃣  Importando Autos TSP...')

        df = pd.read_excel(xls, sheet_name='7_Autos_TSP')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                recurso_id = int(row['recurso_tsp_id']) if pd.notna(row['recurso_tsp_id']) else None
                if not recurso_id:
                    continue

                recurso = RecursoTSP.objects.get(id=recurso_id)
                numero_auto = str(row['numero']).strip() if pd.notna(row['numero']) else ''

                # Crear/actualizar Auto TSP SIN campos de notificación
                autotsp, _ = AUTOTSP.objects.update_or_create(
                    recurso_tsp=recurso,
                    numero=numero_auto,
                    defaults={
                        'sim': recurso.sim,
                        'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                        'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                        'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
                    }
                )

                # Crear Notificacion por separado
                if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                    notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                    valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                    if notif_tipo not in valid_tipos:
                        notif_tipo = 'FIRMA'

                    Notificacion.objects.update_or_create(
                        autotsp=autotsp,
                        defaults={
                            'tipo': notif_tipo,
                            'notificado_a': str(row['notif_a']).strip() if pd.notna(row['notif_a']) else '',
                            'fecha': pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None,
                            'hora': None,
                        }
                    )

            except (RecursoTSP.DoesNotExist, ValueError) as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Autos TSP importados'))

    def _importar_documentos_adjuntos(self, xls):
        """Importa Documentos Adjuntos (PDFs)."""
        self.stdout.write('8️⃣  Importando Documentos Adjuntos...')

        df = pd.read_excel(xls, sheet_name='8_Documentos_Adjuntos')
        df = df.dropna(how='all')

        for idx, row in df.iterrows():
            try:
                DocumentoAdjunto.objects.update_or_create(
                    tabla=str(row['tabla']).strip(),
                    registro_id=int(row['registro_id']) if pd.notna(row['registro_id']) else None,
                    archivo=str(row['archivo']).strip(),
                    defaults={
                        'tipo': str(row['tipo']).strip() if pd.notna(row['tipo']) else 'PDF',
                        'nombre': str(row['nombre']).strip().upper() if pd.notna(row['nombre']) else '',
                        'fecha_registro': pd.to_datetime(row['fecha_registro']).date() if pd.notna(row['fecha_registro']) else None,
                    }
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Documentos Adjuntos importados'))

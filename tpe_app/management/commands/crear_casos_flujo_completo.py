# tpe_app/management/commands/crear_casos_flujo_completo.py
"""
Comando para crear casos de prueba con FLUJO COMPLETO a traves de todos los roles.

USO:
    python manage.py crear_casos_flujo_completo           - crea todo sin borrar nada
    python manage.py crear_casos_flujo_completo --reset   - borra datos de prueba y recrea todo

CASOS CREADOS:
  1. SOLICITUD ASCENSO (SASJUR-25/25)
     - Multiples militares con dictamenes individuales
     - Algunos aprueban, otros rechazan (procedente/improcedente)

  2. SIM DJE CON AUTO EJECUTORIA DIRECTO
     - Flujo simplificado sin Resolucion previa
     - Solo genera Auto de Ejecutoria

  3. SUMARIO MULTI-MILITAR CON DISTINTAS APELACIONES
     - 3 militares en el mismo SIM
     - Cada uno con su dictamen
     - Algunos se conforman en RES
     - Otros van a RR y RAP
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from tpe_app.models import (
    PM, ABOG, VOCAL_TPE, SIM, PM_SIM, ABOG_SIM,
    AGENDA, DICTAMEN, AUTOTPE, CustodiaSIM,
    Resolucion, RecursoTSP,
    PerfilUsuario, add_business_days
)


class Command(BaseCommand):
    help = 'Crea casos de prueba con flujo completo a traves de todos los roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Borra todos los datos de prueba antes de recrear',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('[!] Borrando datos existentes...'))
            self._limpiar_datos()
            self.stdout.write(self.style.SUCCESS('[OK] Datos borrados.\n'))

        self.stdout.write('\n[*] Creando usuarios para todos los roles...')
        admin, abog1, abog2, abog3, admin1, admin2, admin3, vocal, ayudante, buscador = self._crear_usuarios()
        self.stdout.write(self.style.SUCCESS('[OK] 10 usuarios creados'))

        self.stdout.write('[*] Creando Personal Militar, Abogados y Vocales...')
        pm_military, abogados, vocales = self._crear_actores()
        self.stdout.write(self.style.SUCCESS('[OK] Personal y abogados creados'))

        self.stdout.write('[*] Creando agendas...')
        agendas = self._crear_agendas()
        self.stdout.write(self.style.SUCCESS('[OK] Agendas creadas'))

        # Obtener ABOGs (abogados)
        abog_objs = ABOG.objects.all()[:3]
        abog_1 = abog_objs[0] if len(abog_objs) > 0 else None
        abog_2 = abog_objs[1] if len(abog_objs) > 1 else None
        abog_3 = abog_objs[2] if len(abog_objs) > 2 else None
        vocal_obj = VOCAL_TPE.objects.first()

        self.stdout.write('\n[*] Caso 1: SOLICITUD DE ASCENSO (SASJUR-25/25)...')
        self._caso_solicitud_ascenso(abog_1, abog_2, admin2, vocal_obj, agendas, pm_military)
        self.stdout.write(self.style.SUCCESS('[OK] Caso 1 creado con flujo completo'))

        self.stdout.write('\n[*] Caso 2: SIM DJE (Solo Auto Ejecutoria)...')
        self._caso_auto_ejecutoria_directo(abog_2, abog_3, admin1, admin2, admin3, agendas, pm_military)
        self.stdout.write(self.style.SUCCESS('[OK] Caso 2 creado con flujo directo a ejecutoria'))

        self.stdout.write('\n[*] Caso 3: SUMARIO MULTI-MILITAR (Diferentes apelaciones)...')
        self._caso_multi_militar_apelaciones(abog_1, admin2, vocal_obj, agendas, pm_military)
        self.stdout.write(self.style.SUCCESS('[OK] Caso 3 creado con multiples caminos de apelacion'))

        self._mostrar_resumen()

    def _limpiar_datos(self):
        """Borra todos los datos de prueba sin afectar el sistema base."""
        RecursoTSP.objects.all().delete()
        AUTOTPE.objects.all().delete()
        Resolucion.objects.all().delete()
        DICTAMEN.objects.all().delete()
        CustodiaSIM.objects.all().delete()
        AGENDA.objects.all().delete()
        ABOG_SIM.objects.all().delete()
        PM_SIM.objects.all().delete()
        SIM.objects.all().delete()

    def _crear_usuarios(self):
        """Crea 10 usuarios para diferentes roles."""
        usuarios = {}
        roles_config = [
            ('admin_flujo', 'admin123', 'ADMINISTRADOR', None, None),
            ('abog1_flujo', 'abog123', 'ABOG1_ASESOR', 'abog1', None),
            ('abog2_flujo', 'abog123', 'ABOG2_AUTOS', 'abog2', None),
            ('abog3_flujo', 'abog123', 'ABOG3_BUSCADOR', 'abog3', None),
            ('admin1_flujo', 'admin123', 'ADMIN1_AGENDADOR', None, None),
            ('admin2_flujo', 'admin123', 'ADMIN2_ARCHIVO', None, None),
            ('admin3_flujo', 'admin123', 'ADMIN3_NOTIFICADOR', None, None),
            ('vocal_flujo', 'vocal123', 'VOCAL_TPE', None, 'vocal_sec'),
            ('ayudante_flujo', 'ayud123', 'AYUDANTE', None, None),
            ('buscador_flujo', 'buscar123', 'BUSCADOR', None, None),
        ]

        abog_refs = {
            'abog1': ABOG.objects.filter(paterno='RODRIGUEZ').first(),
            'abog2': ABOG.objects.filter(paterno='LLANOS').first(),
            'abog3': ABOG.objects.filter(paterno='SALINAS').first(),
        }

        pm_vocal, _ = PM.objects.get_or_create(
            ci=40000001, defaults=dict(
                escalafon='OFICIAL SUPERIOR', grado='MY.',
                arma='COM.', nombre='JUAN', paterno='FIGUEROA',
                materno='QUISPE', estado='ACTIVO'
            )
        )
        vocal_sec, _ = VOCAL_TPE.objects.get_or_create(
            pm=pm_vocal, cargo='SECRETARIO_ACTAS', defaults=dict(activo=True)
        )

        vocal_refs = {'vocal_sec': vocal_sec}

        for username, password, rol, abog_key, vocal_key in roles_config:
            if not User.objects.filter(username=username).exists():
                if rol == 'ADMINISTRADOR':
                    user = User.objects.create_superuser(
                        username=username, password=password, email=f'{username}@tpe.bo'
                    )
                else:
                    user = User.objects.create_user(
                        username=username, password=password, email=f'{username}@tpe.bo'
                    )

                abog_obj = abog_refs.get(abog_key) if abog_key else None
                vocal_obj = vocal_refs.get(vocal_key) if vocal_key else None

                PerfilUsuario.objects.create(
                    user=user, rol=rol, abogado=abog_obj, vocal=vocal_obj, activo=True
                )
                self.stdout.write(f'   [OK] {rol:20} -> {username}')
            else:
                self.stdout.write(f'   [skip] {username} ya existe')

            usuarios[username] = User.objects.get(username=username)

        return (usuarios['admin_flujo'], usuarios['abog1_flujo'], usuarios['abog2_flujo'],
                usuarios['abog3_flujo'], usuarios['admin1_flujo'], usuarios['admin2_flujo'],
                usuarios['admin3_flujo'], usuarios['vocal_flujo'], usuarios['ayudante_flujo'],
                usuarios['buscador_flujo'])

    def _crear_actores(self):
        """Crea o recupera PM, ABOG, VOCAL."""
        pm_list = {}
        for i, (ci, grado, arma, nombre, paterno, materno) in enumerate([
            (50000001, 'CAP.', 'INF.', 'JUAN', 'ROJAS', 'CONDORI'),
            (50000002, 'TTE.', 'CAB.', 'PEDRO', 'MIRANDA', 'QUISPE'),
            (50000003, 'MY.', 'ART.', 'ROBERTO', 'SANTOS', 'FLORES'),
            (50000004, 'TCNL.', 'ING.', 'MARIO', 'GOMEZ', 'LOPEZ'),
            (50000005, 'SOF. 1RO.', 'INT.', 'LUIS', 'VARGAS', 'HUANCA'),
            (50000006, 'SGTO. 1RO.', 'INF.', 'CARLOS', 'RAMOS', 'CHOQUE'),
            (50000007, 'MY.', 'SAN.', 'ANA', 'GARCIA', 'RIOS'),
        ]):
            pm, _ = PM.objects.get_or_create(ci=ci, defaults=dict(
                escalafon='OFICIAL' if 'MY' in grado or 'TCNL' in grado else 'OTRO',
                grado=grado, arma=arma, nombre=nombre,
                paterno=paterno, materno=materno, estado='ACTIVO'
            ))
            pm_list[f'pm{i+1}'] = pm

        abog_list = {}
        for i, (ci, grado, arma, nombre, paterno, materno) in enumerate([
            (60000001, 'MY.', 'INF.', 'JORGE', 'RODRIGUEZ', 'SALINAS'),
            (60000002, 'CAP.', 'INT.', 'PATRICIA', 'LLANOS', 'VERA'),
            (60000003, 'SBTTE.', 'COM.', 'LUIS', 'SALINAS', 'PINTO'),
        ]):
            abog, _ = ABOG.objects.get_or_create(ci=ci, defaults=dict(
                grado=grado, arma=arma, nombre=nombre,
                paterno=paterno, materno=materno
            ))
            abog_list[f'abog{i+1}'] = abog

        self.stdout.write(f'   > {len(pm_list)} militares | {len(abog_list)} abogados')
        return pm_list, abog_list, {'vocal_sec': VOCAL_TPE.objects.first()}

    def _crear_agendas(self):
        """Crea 3 agendas para los casos."""
        agendas = {}
        for i, (num, fec) in enumerate(
            [('AG-FLUJO-001/26', date(2026, 4, 20)),
             ('AG-FLUJO-002/26', date(2026, 4, 25)),
             ('AG-FLUJO-003/26', date(2026, 5, 5))]
        ):
            ag, _ = AGENDA.objects.get_or_create(numero=num, defaults=dict(
                fecha_prog=fec, fecha_real=fec, tipo='ORDINARIA'
            ))
            agendas[f'ag{i+1}'] = ag
        return agendas

    def _caso_solicitud_ascenso(self, abog1, abog2, admin2, vocal, agendas, pm_military):
        """CASO 1: Solicitud de Ascenso con multiples militares"""
        sim = SIM.objects.create(
            codigo='SASJUR-25/25',
            fecha_ingreso=date(2026, 4, 1),
            estado='PARA_AGENDA',
            tipo='SOLICITUD_ASCENSO_AL_GRADO_INMEDIATO_SUPERIOR',
            objeto='SOLICITUD DE ASCENSO POR MERITOS EXTRAORDINARIOS PARA OFICIALES',
            resumen='SOLICITUD ASCENSO MULTIPLES OFICIALES'
        )
        self.stdout.write(f'   > {sim.codigo}: PARA_AGENDA (ingreso)')

        pm1, pm2 = pm_military['pm1'], pm_military['pm2']
        PM_SIM.objects.create(sim=sim, pm=pm1)
        PM_SIM.objects.create(sim=sim, pm=pm2)
        ABOG_SIM.objects.create(sim=sim, abog=abog1)
        ABOG_SIM.objects.create(sim=sim, abog=abog2)

        sim.estado = 'PROCESO_EN_EL_TPE'
        sim.fase = 'PARA_DICTAMEN'
        sim.save()
        self.stdout.write(f'   > {sim.codigo}: PROCESO_EN_EL_TPE')

        CustodiaSIM.objects.create(
            sim=sim, tipo_custodio='ADMIN2_ARCHIVO', estado='RECIBIDA_CONFORME',
            usuario=admin2
        )
        self.stdout.write(f'   > Custodia: ADMIN2_ARCHIVO')

        CustodiaSIM.objects.create(
            sim=sim, tipo_custodio='ABOG_ASESOR', abog=abog1,
            estado='PENDIENTE_CONFIRMACION', usuario=admin2
        )
        self.stdout.write(f'   > Custodia: ABOG_ASESOR (ABOG1)')

        dic1 = DICTAMEN.objects.create(
            sim=sim, pm=pm1, abog=abog1, agenda=agendas['ag1'],
            numero='01/26', conclusion='SE RECOMIENDA APROBAR ASCENSO POR MERITOS',
            estado='PENDIENTE'
        )

        cust1 = CustodiaSIM.objects.filter(sim=sim, abog=abog1).first()
        if cust1:
            cust1.estado = 'RECIBIDA_CONFORME'
            cust1.fecha_entrega = None
            cust1.save()

        self.stdout.write(f'   > Dictamen PM1: APROBADO')

        CustodiaSIM.objects.create(
            sim=sim, tipo_custodio='ABOG_ASESOR', abog=abog2,
            estado='PENDIENTE_CONFIRMACION', usuario=admin2
        )

        dic2 = DICTAMEN.objects.create(
            sim=sim, pm=pm2, abog=abog2, agenda=agendas['ag1'],
            numero='02/26', conclusion='SE RECOMIENDA DENEGAR ASCENSO - FALTA ANTIGUEDAD',
            estado='PENDIENTE'
        )

        cust2 = CustodiaSIM.objects.filter(sim=sim, abog=abog2).first()
        if cust2:
            cust2.estado = 'RECIBIDA_CONFORME'
            cust2.fecha_entrega = None
            cust2.save()

        self.stdout.write(f'   > Dictamen PM2: DENEGADO')

        dic1.estado = 'CONFIRMADO'
        dic1.secretario = vocal
        dic1.conclusion_secretario = 'CONFIRMADO'
        dic1.fecha_confirmacion = date(2026, 4, 22)
        dic1.save()

        dic2.estado = 'CONFIRMADO'
        dic2.secretario = vocal
        dic2.conclusion_secretario = 'CONFIRMADO - FALTA ANTIGUEDAD'
        dic2.fecha_confirmacion = date(2026, 4, 22)
        dic2.save()
        self.stdout.write(f'   > Vocal: Confirma dictamenes')

        res1 = Resolucion.objects.create(
            sim=sim, pm=pm1, abog=abog1, agenda=agendas['ag1'], dictamen=dic1,
            instancia='PRIMERA', numero='01/26', fecha=date(2026, 4, 23),
            tipo='SOLICITUD_ASCENSO',
            texto=f'APROBADO ASCENSO DE {pm1.grado} {pm1.paterno}',
            tipo_notif='FIRMA', notif_a=f'{pm1.grado} {pm1.paterno}',
            fecha_notif=date(2026, 4, 24)
        )

        res2 = Resolucion.objects.create(
            sim=sim, pm=pm2, abog=abog2, agenda=agendas['ag1'], dictamen=dic2,
            instancia='PRIMERA', numero='02/26', fecha=date(2026, 4, 23),
            tipo='SOLICITUD_ASCENSO',
            texto=f'DENEGADA SOLICITUD ASCENSO {pm2.grado} {pm2.paterno}',
            tipo_notif='FIRMA', notif_a=f'{pm2.grado} {pm2.paterno}',
            fecha_notif=date(2026, 4, 24)
        )
        self.stdout.write(f'   > RES 01/26 (PROCEDENTE) y 02/26 (IMPROCEDENTE)')

        auto = AUTOTPE.objects.create(
            sim=sim, pm=pm1, abog=abog2, resolucion=res1,
            tipo='AUTO_EJECUTORIA', numero='01/26',
            fecha=date(2026, 4, 25),
            texto='EJECUTORIADA RESOLUCION 01/26 ASCENSO APROBADO',
            tipo_notif='FIRMA', notif_a=f'{pm1.grado} {pm1.paterno}',
            fecha_notif=date(2026, 4, 26)
        )
        self.stdout.write(f'   > Auto de Ejecutoria 01/26')

        sim.estado = 'CONCLUIDO'
        sim.fase = 'CONCLUIDO'
        sim.save()

    def _caso_auto_ejecutoria_directo(self, abog2, abog3, admin1, admin2, admin3, agendas, pm_military):
        """CASO 2: SIM DJE (De Oficio) solo con Auto Ejecutoria"""
        pm = pm_military['pm3']

        sim = SIM.objects.create(
            codigo='DJE-FLUJO-01/26',
            fecha_ingreso=date(2026, 3, 15),
            estado='PARA_AGENDA',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DE VIOLACION GRAVE DE REGLAMENTO',
            resumen='VIOLACION GRAVE - DE OFICIO'
        )
        self.stdout.write(f'   > {sim.codigo}: Ingresa (SIM de oficio)')

        PM_SIM.objects.create(sim=sim, pm=pm)
        ABOG_SIM.objects.create(sim=sim, abog=abog2)

        sim.estado = 'PROCESO_EN_EL_TPE'
        sim.fase = 'PARA_DICTAMEN'
        sim.save()

        CustodiaSIM.objects.create(
            sim=sim, tipo_custodio='ADMIN2_ARCHIVO',
            estado='RECIBIDA_CONFORME', usuario=admin2
        )

        dic = DICTAMEN.objects.create(
            sim=sim, pm=pm, abog=abog2, agenda=agendas['ag2'],
            numero='01/26', conclusion='DE OFICIO - PROCEDE SOBRESEIMIENTO PREVENTIVO',
            estado='CONFIRMADO'
        )
        self.stdout.write(f'   > Sin RES (de oficio) - Directo a Auto')

        auto = AUTOTPE.objects.create(
            sim=sim, pm=pm, abog=abog3, agenda=agendas['ag2'],
            tipo='AUTO_EJECUTORIA', numero='02/26',
            fecha=date(2026, 3, 25),
            texto='AUTO DE EJECUCION DE OFICIO - SOBRESEIMIENTO PREVENTIVO',
            tipo_notif='FIRMA', notif_a=f'{pm.grado} {pm.paterno}',
            fecha_notif=date(2026, 3, 26)
        )
        self.stdout.write(f'   > Auto de Ejecutoria 02/26 (directo, sin RES)')

        CustodiaSIM.objects.create(
            sim=sim, tipo_custodio='ARCHIVO', motivo='ARCHIVO',
            estado='RECIBIDA_CONFORME', usuario=admin1,
            nro_oficio_archivo='OF-FLUJO-001/26',
            fecha_oficio_archivo=date(2026, 3, 27)
        )

        sim.estado = 'CONCLUIDO'
        sim.fase = 'CONCLUIDO'
        sim.save()
        self.stdout.write(f'   > {sim.codigo}: CONCLUIDO')

    def _caso_multi_militar_apelaciones(self, abog1, admin2, vocal, agendas, pm_military):
        """CASO 3: Sumario con 3 militares - diferentes destinos"""
        pm1, pm2, pm3 = pm_military['pm4'], pm_military['pm5'], pm_military['pm6']
        abog2 = ABOG.objects.filter(paterno='LLANOS').first() or abog1

        sim = SIM.objects.create(
            codigo='DJE-FLUJO-02/26',
            fecha_ingreso=date(2026, 3, 1),
            estado='PARA_AGENDA',
            tipo='DISCIPLINARIO',
            objeto='SUMARIO CONTRA TRES MILITARES POR INFRACCIONES MILITARES',
            resumen='MULTI-MILITAR - 3 IMPLICADOS'
        )
        self.stdout.write(f'   > {sim.codigo}: Ingresa (3 militares)')

        PM_SIM.objects.create(sim=sim, pm=pm1)
        PM_SIM.objects.create(sim=sim, pm=pm2)
        PM_SIM.objects.create(sim=sim, pm=pm3)

        ABOG_SIM.objects.create(sim=sim, abog=abog1)
        ABOG_SIM.objects.create(sim=sim, abog=abog2)

        sim.estado = 'PROCESO_EN_EL_TPE'
        sim.fase = 'PARA_DICTAMEN'
        sim.save()

        CustodiaSIM.objects.create(
            sim=sim, tipo_custodio='ADMIN2_ARCHIVO',
            estado='RECIBIDA_CONFORME', usuario=admin2
        )

        dic1 = DICTAMEN.objects.create(
            sim=sim, pm=pm1, abog=abog1, agenda=agendas['ag2'],
            numero='01/26', conclusion='SANCION ADMINISTRATIVA POR 30 DIAS',
            estado='CONFIRMADO',
            secretario=vocal, conclusion_secretario='CONFIRMADO', fecha_confirmacion=date(2026, 3, 15)
        )

        dic2 = DICTAMEN.objects.create(
            sim=sim, pm=pm2, abog=abog1, agenda=agendas['ag2'],
            numero='02/26', conclusion='SANCION DISCIPLINARIA RETIRO OBLIGATORIO',
            estado='CONFIRMADO',
            secretario=vocal, conclusion_secretario='CONFIRMADO', fecha_confirmacion=date(2026, 3, 15)
        )

        dic3 = DICTAMEN.objects.create(
            sim=sim, pm=pm3, abog=abog2, agenda=agendas['ag2'],
            numero='03/26', conclusion='SANCION POR NEGLIGENCIA - LETRA B',
            estado='CONFIRMADO',
            secretario=vocal, conclusion_secretario='CONFIRMADO', fecha_confirmacion=date(2026, 3, 15)
        )
        self.stdout.write(f'   > Dictamenes: PM1, PM2, PM3 confirmados')

        res1 = Resolucion.objects.create(
            sim=sim, pm=pm1, abog=abog1, agenda=agendas['ag2'], dictamen=dic1,
            instancia='PRIMERA', numero='03/26', fecha=date(2026, 3, 20),
            tipo='ADMINISTRATIVO',
            texto=f'SANCION ADMINISTRATIVA A {pm1.grado} {pm1.paterno} - 30 DIAS',
            tipo_notif='FIRMA', notif_a=f'{pm1.grado} {pm1.paterno}',
            fecha_notif=date(2026, 3, 21)
        )

        res2 = Resolucion.objects.create(
            sim=sim, pm=pm2, abog=abog1, agenda=agendas['ag2'], dictamen=dic2,
            instancia='PRIMERA', numero='04/26', fecha=date(2026, 3, 20),
            tipo='SANCION_RETIRO_OBLIGATORIO',
            texto=f'SANCION RETIRO OBLIGATORIO A {pm2.grado} {pm2.paterno}',
            tipo_notif='FIRMA', notif_a=f'{pm2.grado} {pm2.paterno}',
            fecha_notif=date(2026, 3, 21)
        )

        res3 = Resolucion.objects.create(
            sim=sim, pm=pm3, abog=abog2, agenda=agendas['ag2'], dictamen=dic3,
            instancia='PRIMERA', numero='05/26', fecha=date(2026, 3, 20),
            tipo='SANCION_LETRA_B',
            texto=f'SANCION LETRA B A {pm3.grado} {pm3.paterno}',
            tipo_notif='FIRMA', notif_a=f'{pm3.grado} {pm3.paterno}',
            fecha_notif=date(2026, 3, 21)
        )
        self.stdout.write(f'   > RES 03/26, 04/26, 05/26 emitidas')

        auto1 = AUTOTPE.objects.create(
            sim=sim, pm=pm1, abog=abog1, resolucion=res1,
            tipo='AUTO_EJECUTORIA', numero='03/26',
            fecha=date(2026, 4, 5),
            texto=f'EJECUTORIADA RESOLUCION 03/26 CONTRA {pm1.grado} {pm1.paterno}',
            tipo_notif='FIRMA', notif_a=f'{pm1.grado} {pm1.paterno}',
            fecha_notif=date(2026, 4, 6)
        )
        self.stdout.write(f'   > PM1: CONFORMADO - RES 03/26 > Auto > CONCLUIDO')

        rr2 = Resolucion.objects.create(
            sim=sim, pm=pm2, abog=abog1, agenda=agendas['ag3'],
            instancia='RECONSIDERACION', resolucion_origen=res2,
            numero='06/26', fecha_presentacion=date(2026, 4, 1),
            resumen='PROCEDENCIA'
        )
        self.stdout.write(f'   > PM2: Presenta RR (pendiente resolucion)')

        rr3 = Resolucion.objects.create(
            sim=sim, pm=pm3, abog=abog2, agenda=agendas['ag3'],
            instancia='RECONSIDERACION', resolucion_origen=res3,
            numero='07/26', fecha_presentacion=date(2026, 3, 28),
            resumen='IMPROCEDENCIA',
            fecha=date(2026, 4, 5),
            texto='EL TRIBUNAL RECHAZA RECURSO - MANTIENE SANCION LETRA B'
        )

        rap3 = RecursoTSP.objects.create(
            sim=sim, pm=pm3, abog=abog2, resolucion=rr3,
            instancia='APELACION',
            fechaPRESEN=date(2026, 4, 8),
            numero_oficio='OFI-FLUJO-001/26',
            fechaOFI=date(2026, 4, 9)
        )

        sim.estado = 'EN_APELACION_TSP'
        sim.fase = 'EN_APELACION_TSP'
        sim.save()
        self.stdout.write(f'   > PM3: RR deniega > RAP ante TSP > EN_APELACION_TSP')

    def _mostrar_resumen(self):
        """Muestra resumen final de datos creados."""
        self.stdout.write(self.style.SUCCESS("""
[OK] FLUJO COMPLETO CREADO EXITOSAMENTE

CREDENCIALES DE ACCESO:
  admin_flujo / admin123 (ADMINISTRADOR)
  admin1_flujo / admin123 (ADMIN1 - Agendador)
  admin2_flujo / admin123 (ADMIN2 - Archivo)
  admin3_flujo / admin123 (ADMIN3 - Notificador)
  abog1_flujo / abog123 (ABOG1 - Asesor)
  abog2_flujo / abog123 (ABOG2 - Autos)
  abog3_flujo / abog123 (ABOG3 - Buscador)
  vocal_flujo / vocal123 (VOCAL - Secretario Actas)
  ayudante_flujo / ayud123 (AYUDANTE)
  buscador_flujo / buscar123 (BUSCADOR)

CASOS CREADOS:

1. SASJUR-25/25 (Solicitud de Ascenso - Multi-militar)
   - 2 militares (PM1, PM2)
   - PM1: Dictamen APROBADO > RES PROCEDENTE > Auto Ejecutoria
   - PM2: Dictamen DENEGADO > RES IMPROCEDENTE > Auto Ejecutoria
   - Estado: CONCLUIDO
   - Verifica: Ingreso > Custodia > Agenda > Dictamen > Vocal > RES > Auto

2. DJE-FLUJO-01/26 (SIM De Oficio - Solo Auto Ejecutoria)
   - 1 militar (PM3)
   - Sin Resolucion previa (de oficio)
   - Flujo rapido: Ingreso > Dictamen > Auto > Archivo
   - Estado: CONCLUIDO

3. DJE-FLUJO-02/26 (Sumario Multi-militar - Diferentes apelaciones)
   - 3 militares (PM4, PM5, PM6)
   - PM4: RES > NO APELA > Auto Ejecutoria > CONCLUIDO
   - PM5: RES > RR (en proceso) > PROCESO_EN_EL_TPE
   - PM6: RES > RR DENIEGA > RAP ante TSP > EN_APELACION_TSP

VERIFICAR FLUJO CON CADA ROL:
- Admin2 Dashboard: Verifica custodia ACTIVA y PENDIENTE_CONFIRMACION
- Abogado Dashboard: Verifica dictamenes pendientes y resoluciones
- Vocal Dashboard: Verifica dictamenes para confirmacion
- Admin3 Dashboard: Verifica autos para notificar
- Admin1 Dashboard: Verifica ejecuciones pendientes
- Buscador: Busca por codigo SIM para ver historial

COMANDO PARA RECREAR (borrar datos de prueba):
  python manage.py crear_casos_flujo_completo --reset
"""))
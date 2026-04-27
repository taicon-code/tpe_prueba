# tpe_app/management/commands/poblar_bd_demo.py
"""
Comando para llenar la base de datos con datos de demostración realistas.
Cubre 7 escenarios distintos del flujo militar completo.

USO:
    python manage.py poblar_bd_demo           ← crea todo sin borrar nada
    python manage.py poblar_bd_demo --reset   ← borra SIM/PM/ABOG y recrea todo

ESCENARIOS creados:
  1. SIM PARA_AGENDA       → sumario recién ingresado, esperando agenda
  2. SIM PROCESO (dictamen)→ tiene agenda y dictamen PENDIENTE
  3. SIM con RES           → resolución emitida, sin apelación → CONCLUIDO
  4. SIM con RR            → recurso de reconsideración en proceso
  5. SIM EN_APELACION_TSP  → apelado ante el TSP
  6. SIM SOBRESEÍDO        → auto TPE de sobreseimiento → CONCLUIDO
  7. SIM SOLICITUD ASCENSO → caso no disciplinario → CONCLUIDO
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from tpe_app.models import (
    PM, VOCAL_TPE, SIM, PM_SIM, ABOG_SIM,
    AGENDA, DICTAMEN, AUTOTPE, AUTOTSP,
    Resolucion, RecursoTSP, Notificacion,
    PerfilUsuario,
)


class Command(BaseCommand):
    help = 'Llena la BD con datos de demostración para probar todos los roles y flujos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Borra todos los SIM, PM, ABOG y documentos antes de recrear',
        )

    # ─────────────────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('\n⚠️  Borrando datos existentes...'))
            RecursoTSP.objects.all().delete()
            AUTOTSP.objects.all().delete()
            AUTOTPE.objects.all().delete()
            Resolucion.objects.all().delete()
            DICTAMEN.objects.all().delete()
            AGENDA.objects.all().delete()
            ABOG_SIM.objects.all().delete()
            PM_SIM.objects.all().delete()
            SIM.objects.all().delete()
            PM.objects.all().delete()
            VOCAL_TPE.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('   Datos borrados.\n'))

        # ── 1. PERSONAL MILITAR ───────────────────────────────────────────────
        self.stdout.write('👥 Creando Personal Militar...')

        pm_tte, _ = PM.objects.get_or_create(ci=10000001, defaults=dict(
            escalafon='OFICIAL SUBALTERNO', grado='TTE.', arma='INF.',
            nombre='JUAN', paterno='CONDORI', materno='MAMANI',
            estado='ACTIVO', especialidad='COMBATE',
        ))
        pm_cap, _ = PM.objects.get_or_create(ci=10000002, defaults=dict(
            escalafon='OFICIAL SUBALTERNO', grado='CAP.', arma='CAB.',
            nombre='PEDRO', paterno='VARGAS', materno='QUISPE',
            estado='ACTIVO',
        ))
        pm_my, _ = PM.objects.get_or_create(ci=10000003, defaults=dict(
            escalafon='OFICIAL SUPERIOR', grado='MY.', arma='ART.',
            nombre='ROBERTO', paterno='FLORES', materno='CONDORI',
            estado='ACTIVO',
        ))
        pm_tcnl, _ = PM.objects.get_or_create(ci=10000004, defaults=dict(
            escalafon='OFICIAL SUPERIOR', grado='TCNL.', arma='ING.',
            nombre='MARIO', paterno='GUTIERREZ', materno='LOPEZ',
            estado='ACTIVO',
        ))
        pm_cnl, _ = PM.objects.get_or_create(ci=10000005, defaults=dict(
            escalafon='OFICIAL SUPERIOR', grado='CNL.', arma='COM.',
            nombre='CARLOS', paterno='MENDOZA', materno='TORREZ',
            estado='ACTIVO',
        ))
        pm_sof, _ = PM.objects.get_or_create(ci=10000006, defaults=dict(
            escalafon='SUBOFICIAL', grado='SOF. 1RO.', arma='INT.',
            nombre='HUGO', paterno='MAMANI', materno='CHOQUE',
            estado='ACTIVO',
        ))
        pm_my2, _ = PM.objects.get_or_create(ci=10000007, defaults=dict(
            escalafon='OFICIAL SUPERIOR', grado='MY.', arma='SAN.',
            nombre='ANA MARIA', paterno='GARCIA', materno='RIOS',
            estado='ACTIVO',
        ))
        # Militar adicional para sumario con dos implicados
        pm_sgto, _ = PM.objects.get_or_create(ci=10000008, defaults=dict(
            escalafon='SARGENTO', grado='SGTO. 1RO.', arma='INF.',
            nombre='LUIS', paterno='TICONA', materno='HUANCA',
            estado='ACTIVO',
        ))
        self.stdout.write(self.style.SUCCESS('   ✅ 8 militares creados'))

        # ── 2. PM ABOGADOS (demos — registrados como Personal Militar) ───────
        self.stdout.write('⚖️  Creando PM Abogados (demo)...')

        abog1, _ = PM.objects.get_or_create(ci=20000001, defaults=dict(
            escalafon='OFICIAL SUPERIOR', grado='MY.', arma='INF.',
            nombre='JORGE', paterno='RODRIGUEZ', materno='SALINAS', estado='ACTIVO',
        ))
        abog2, _ = PM.objects.get_or_create(ci=20000002, defaults=dict(
            escalafon='OFICIAL SUBALTERNO', grado='CAP.', arma='INT.',
            nombre='PATRICIA', paterno='LLANOS', materno='VERA', estado='ACTIVO',
        ))
        self.stdout.write(self.style.SUCCESS('   ✅ 2 PM abogados demo creados'))

        # ── 3. VOCALES TPE ────────────────────────────────────────────────────
        self.stdout.write('🎖️  Creando Vocales del Tribunal...')

        # Usamos militares existentes como vocales
        pm_pres, _ = PM.objects.get_or_create(ci=30000001, defaults=dict(
            escalafon='GENERAL', grado='GRAL. BRIG.', arma='INF.',
            nombre='ANTONIO', paterno='PEREZ', materno='ALBA',
            estado='ACTIVO',
        ))
        pm_sec, _ = PM.objects.get_or_create(ci=30000002, defaults=dict(
            escalafon='OFICIAL SUPERIOR', grado='MY.', arma='COM.',
            nombre='SILVIA', paterno='CHURA', materno='RAMOS',
            estado='ACTIVO',
        ))
        vocal_pres, _ = VOCAL_TPE.objects.get_or_create(
            pm=pm_pres, cargo='PRESIDENTE',
            defaults=dict(activo=True, cargo_em='JEFE DPTO. I-PERS'))
        vocal_sec, _ = VOCAL_TPE.objects.get_or_create(
            pm=pm_sec, cargo='SECRETARIO_ACTAS',
            defaults=dict(activo=True, cargo_em='AYUDANTE DE ÓRDENES DPTO. I-PERS'))
        self.stdout.write(self.style.SUCCESS('   ✅ 2 vocales creados (Presidente + Secretario de Actas)'))

        # ── 4. USUARIOS ───────────────────────────────────────────────────────
        self.stdout.write('👤 Creando Usuarios del sistema...')
        self._crear_usuario('admin',    'admin123',    'ADMINISTRADOR',   None,  None)
        self._crear_usuario('abogado1', 'abog123',     'ABOG1_ASESOR',   abog1, None)
        self._crear_usuario('abogado2', 'abog123',     'ABOG2_AUTOS',    abog2, None)
        self._crear_usuario('secretario', 'sec123',   'SECRETARIO_ACTAS', None, vocal_sec)
        self._crear_usuario('adminvista', 'admin123',  'ADMIN1_AGENDADOR', None, None)
        self._crear_usuario('buscador1', 'buscar123',  'BUSCADOR',        None, None)
        self.stdout.write(self.style.SUCCESS('   ✅ 6 usuarios creados'))

        # ── 5. AGENDAS ────────────────────────────────────────────────────────
        self.stdout.write('📅 Creando Agendas...')

        agenda1, _ = AGENDA.objects.get_or_create(numero='AG-001/26', defaults=dict(
            fecha_prog=date(2026, 3, 10),
            fecha_real=date(2026, 3, 10),
            tipo='ORDINARIA',
        ))
        agenda2, _ = AGENDA.objects.get_or_create(numero='AG-002/26', defaults=dict(
            fecha_prog=date(2026, 3, 25),
            fecha_real=date(2026, 3, 25),
            tipo='ORDINARIA',
        ))
        agenda3, _ = AGENDA.objects.get_or_create(numero='AG-003/26', defaults=dict(
            fecha_prog=date(2026, 4, 8),
            fecha_real=date(2026, 4, 8),
            tipo='EXTRAORDINARIA',
        ))
        agenda_futura, _ = AGENDA.objects.get_or_create(numero='AG-004/26', defaults=dict(
            fecha_prog=date(2026, 4, 22),
            fecha_real=None,
            tipo='ORDINARIA',
        ))
        self.stdout.write(self.style.SUCCESS('   ✅ 4 agendas creadas'))

        # ── 6. SUMARIOS (SIM) — 7 escenarios ─────────────────────────────────
        self.stdout.write('\n📋 Creando Sumarios con sus flujos...')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 1: PARA_AGENDA
        # SIM recién ingresado, abogado asignado, esperando agenda
        # ─────────────────────────────────────────────────────────────────────
        sim1, _ = SIM.objects.get_or_create(codigo='DJE-001/26', defaults=dict(
            fecha_ingreso=date(2026, 4, 10),
            estado='PARA_AGENDA',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DEL CONSUMO DE BEBIDAS ALCOHOLICAS PMA. Y ACCIDENTE DE TRANSITO',
            resumen='BEBIDAS ALCOHOLICAS Y ACCIDENTE',
        ))
        PM_SIM.objects.get_or_create(sim=sim1, pm=pm_tte)
        PM_SIM.objects.get_or_create(sim=sim1, pm=pm_sgto)  # dos implicados
        ABOG_SIM.objects.get_or_create(sim=sim1, abogado=abog1)
        self.stdout.write('   📌 Escenario 1: DJE-001/26 → PARA AGENDA (2 implicados)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 2: PROCESO_EN_EL_TPE — tiene dictamen PENDIENTE
        # ─────────────────────────────────────────────────────────────────────
        sim2, _ = SIM.objects.get_or_create(codigo='DJE-002/26', defaults=dict(
            fecha_ingreso=date(2026, 3, 5),
            estado='PROCESO_EN_EL_TPE',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DE MALTRATO AL PERSONAL SUBALTERNO',
            resumen='MALTRATO AL PERSONAL',
        ))
        PM_SIM.objects.get_or_create(sim=sim2, pm=pm_cap)
        ABOG_SIM.objects.get_or_create(sim=sim2, abogado=abog1)

        dic2, _ = DICTAMEN.objects.get_or_create(
            sim=sim2, agenda=agenda1,
            defaults=dict(
                numero='01/26',
                conclusion='SE RECOMIENDA LA SANCION DISCIPLINARIA POR MALTRATO AL PERSONAL',
                abogado=abog1,
                pm=pm_cap,
                estado='PENDIENTE',
            )
        )
        self.stdout.write('   📌 Escenario 2: DJE-002/26 → PROCESO (dictamen pendiente)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 3: RES emitida → CONCLUIDO
        # ─────────────────────────────────────────────────────────────────────
        sim3, _ = SIM.objects.get_or_create(codigo='DJE-003/26', defaults=dict(
            fecha_ingreso=date(2026, 2, 10),
            estado='CONCLUIDO',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DE HURTO DE ARMAMENTO INSTITUCIONAL',
            resumen='HURTO DE ARMAMENTO',
        ))
        PM_SIM.objects.get_or_create(sim=sim3, pm=pm_my)
        ABOG_SIM.objects.get_or_create(sim=sim3, abogado=abog2)

        dic3, _ = DICTAMEN.objects.get_or_create(
            sim=sim3, agenda=agenda1,
            defaults=dict(
                numero='02/26',
                conclusion='SE RECOMIENDA SANCION ARRESTO POR 60 DIAS',
                abogado=abog2, pm=pm_my,
                estado='CONFIRMADO',
                secretario=vocal_sec,
                conclusion_secretario='CONFIRMADO EL DICTAMEN SIN MODIFICACIONES',
                fecha_confirmacion=date(2026, 2, 15),
            )
        )
        res3, _ = Resolucion.objects.get_or_create(
            sim=sim3, instancia='PRIMERA', numero='15/26',
            defaults=dict(
                fecha=date(2026, 2, 20),
                tipo='SANCION_ARRESTO',
                texto='EL TRIBUNAL DE PERSONAL DEL EJERCITO RESUELVE: SANCIONAR AL MY. ROBERTO FLORES CONDORI CON 60 DIAS DE ARRESTO.',
                abogado=abog2, agenda=agenda1, dictamen=dic3, pm=pm_my,
            ))
        Notificacion.objects.get_or_create(resolucion=res3, defaults=dict(
            tipo='FIRMA', notificado_a='MY. ROBERTO FLORES CONDORI', fecha=date(2026, 2, 21)
        ))
        # Auto de ejecutoria (caso terminado sin apelación)
        auto3, _ = AUTOTPE.objects.get_or_create(sim=sim3, tipo='AUTO_EJECUTORIA', defaults=dict(
            numero='08/26',
            fecha=date(2026, 3, 15),
            texto='SE DECLARA EJECUTORIADA LA RESOLUCION NRO. 15/26 DEL TRIBUNAL DE PERSONAL.',
            abogado=abog2, agenda=agenda2, pm=pm_my, resolucion=res3,
        ))
        Notificacion.objects.get_or_create(autotpe=auto3, defaults=dict(
            tipo='FIRMA', notificado_a='MY. ROBERTO FLORES CONDORI', fecha=date(2026, 3, 16)
        ))
        self.stdout.write('   📌 Escenario 3: DJE-003/26 → CONCLUIDO (RES + AUTO EJECUTORIA)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 4: RES + RR en proceso
        # ─────────────────────────────────────────────────────────────────────
        sim4, _ = SIM.objects.get_or_create(codigo='DJE-004/26', defaults=dict(
            fecha_ingreso=date(2026, 1, 15),
            estado='PROCESO_EN_EL_TPE',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DE COBROS IRREGULARES AL PERSONAL',
            resumen='COBROS IRREGULARES',
        ))
        PM_SIM.objects.get_or_create(sim=sim4, pm=pm_tcnl)
        ABOG_SIM.objects.get_or_create(sim=sim4, abogado=abog1)

        dic4, _ = DICTAMEN.objects.get_or_create(
            sim=sim4, agenda=agenda1,
            defaults=dict(
                numero='03/26',
                conclusion='SE RECOMIENDA SANCION LETRA B POR COBROS IRREGULARES',
                abogado=abog1, pm=pm_tcnl,
                estado='MODIFICADO',
                secretario=vocal_sec,
                conclusion_secretario='SE MODIFICA: SE RECOMIENDA ARCHIVO DE OBRADOS POR INSUFICIENCIA PROBATORIA',
                fecha_confirmacion=date(2026, 1, 25),
            )
        )
        res4, _ = Resolucion.objects.get_or_create(
            sim=sim4, instancia='PRIMERA', numero='05/26',
            defaults=dict(
                fecha=date(2026, 2, 1),
                tipo='SANCION_LETRA_B',
                texto='EL TRIBUNAL RESUELVE: SANCIONAR AL TCNL. MARIO GUTIERREZ LOPEZ CON LETRA B (PERDIDA DE ANTIGUEDAD).',
                abogado=abog1, agenda=agenda1, dictamen=dic4, pm=pm_tcnl,
            ))
        Notificacion.objects.get_or_create(resolucion=res4, defaults=dict(
            tipo='CEDULON', notificado_a='TCNL. MARIO GUTIERREZ LOPEZ', fecha=date(2026, 2, 3)
        ))
        rr4, _ = Resolucion.objects.get_or_create(
            sim=sim4, instancia='RECONSIDERACION', resolucion_origen=res4,
            defaults=dict(
                numero='02/26',
                fecha_presentacion=date(2026, 2, 10),
                fecha=None,
                texto=None,
                resumen='PROCEDENCIA',
                abogado=abog1, agenda=agenda2, pm=pm_tcnl,
            ))
        self.stdout.write('   📌 Escenario 4: DJE-004/26 → RES emitida + RR pendiente (MODIFICADO por Secretario)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 5: EN_APELACION_TSP
        # ─────────────────────────────────────────────────────────────────────
        sim5, _ = SIM.objects.get_or_create(codigo='DJE-005/26', defaults=dict(
            fecha_ingreso=date(2025, 11, 10),
            estado='EN_APELACION_TSP',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DE INDISCIPLINA PROFESIONAL Y ABANDONO DE SERVICIO',
            resumen='INDISCIPLINA Y ABANDONO',
        ))
        PM_SIM.objects.get_or_create(sim=sim5, pm=pm_cnl)
        ABOG_SIM.objects.get_or_create(sim=sim5, abogado=abog2)

        dic5, _ = DICTAMEN.objects.get_or_create(
            sim=sim5, agenda=agenda1,
            defaults=dict(
                numero='04/26',
                conclusion='SE RECOMIENDA SANCION RETIRO OBLIGATORIO',
                abogado=abog2, pm=pm_cnl,
                estado='CONFIRMADO',
                secretario=vocal_sec,
                conclusion_secretario='CONFIRMADO',
                fecha_confirmacion=date(2025, 12, 1),
            )
        )
        res5, _ = Resolucion.objects.get_or_create(
            sim=sim5, instancia='PRIMERA', numero='52/25',
            defaults=dict(
                fecha=date(2025, 12, 10),
                tipo='SANCION_RETIRO_OBLIGATORIO',
                texto='EL TRIBUNAL RESUELVE: SANCIONAR AL CNL. CARLOS MENDOZA TORREZ CON RETIRO OBLIGATORIO.',
                abogado=abog2, agenda=agenda1, dictamen=dic5, pm=pm_cnl,
            ))
        Notificacion.objects.get_or_create(resolucion=res5, defaults=dict(
            tipo='EDICTO', notificado_a='PERIODICO LA RAZON', fecha=date(2025, 12, 15)
        ))
        rr5, _ = Resolucion.objects.get_or_create(
            sim=sim5, instancia='RECONSIDERACION', resolucion_origen=res5,
            defaults=dict(
                numero='12/25',
                fecha_presentacion=date(2025, 12, 20),
                fecha=date(2026, 1, 10),
                texto='EL TRIBUNAL RESUELVE: MANTENER EN TODOS SUS TERMINOS LA RESOLUCION NRO. 52/25.',
                resumen='IMPROCEDENCIA',
                abogado=abog2, agenda=agenda2, pm=pm_cnl,
            ))
        rap5, _ = RecursoTSP.objects.get_or_create(
            sim=sim5, instancia='APELACION', resolucion=rr5,
            defaults=dict(
                fecha_presentacion=date(2026, 1, 15),
                numero_oficio='OFI-012/26',
                fecha_oficio=date(2026, 1, 16),
                pm=pm_cnl,
            ))
        self.stdout.write('   📌 Escenario 5: DJE-005/26 → EN APELACION TSP (RES + RR + RAP)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 6: SOBRESEÍDO
        # ─────────────────────────────────────────────────────────────────────
        sim6, _ = SIM.objects.get_or_create(codigo='DJE-006/26', defaults=dict(
            fecha_ingreso=date(2026, 1, 20),
            estado='CONCLUIDO',
            tipo='DISCIPLINARIO',
            objeto='ESTABLECER CIRCUNSTANCIAS DE FALTA LISTA Y ABANDONO DE DESTINO',
            resumen='FALTA LISTA Y ABANDONO',
        ))
        PM_SIM.objects.get_or_create(sim=sim6, pm=pm_sof)
        ABOG_SIM.objects.get_or_create(sim=sim6, abogado=abog2)

        dic6, _ = DICTAMEN.objects.get_or_create(
            sim=sim6, agenda=agenda2,
            defaults=dict(
                numero='05/26',
                conclusion='SE RECOMIENDA SOBRESEIMIENTO POR INSUFICIENCIA DE PRUEBAS',
                abogado=abog2, pm=pm_sof,
                estado='CONFIRMADO',
                secretario=vocal_sec,
                conclusion_secretario='CONFIRMADO',
                fecha_confirmacion=date(2026, 2, 5),
            )
        )
        auto6, _ = AUTOTPE.objects.get_or_create(sim=sim6, tipo='SOBRESEIDO', defaults=dict(
            numero='03/26',
            fecha=date(2026, 2, 10),
            texto='EL TRIBUNAL DE PERSONAL DEL EJERCITO RESUELVE: DECLARAR SOBRESEIDO EL PROCESO SUMARIO CONTRA SOF. 1RO. HUGO MAMANI CHOQUE POR INSUFICIENCIA PROBATORIA.',
            abogado=abog2, agenda=agenda2, pm=pm_sof,
        ))
        Notificacion.objects.get_or_create(autotpe=auto6, defaults=dict(
            tipo='FIRMA', notificado_a='SOF. 1RO. HUGO MAMANI CHOQUE', fecha=date(2026, 2, 11)
        ))
        self.stdout.write('   📌 Escenario 6: DJE-006/26 → CONCLUIDO (SOBRESEÍDO)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 7: SOLICITUD DE ASCENSO (no disciplinario)
        # ─────────────────────────────────────────────────────────────────────
        sim7, _ = SIM.objects.get_or_create(codigo='SLC-001/26', defaults=dict(
            fecha_ingreso=date(2026, 3, 1),
            estado='CONCLUIDO',
            tipo='SOLICITUD_ASCENSO_AL_GRADO_INMEDIATO_SUPERIOR',
            objeto='SOLICITUD DE ASCENSO AL GRADO INMEDIATO SUPERIOR POR MERITOS EXTRAORDINARIOS',
            resumen='SOLICITUD ASCENSO',
        ))
        PM_SIM.objects.get_or_create(sim=sim7, pm=pm_my2)
        ABOG_SIM.objects.get_or_create(sim=sim7, abogado=abog1)

        dic7, _ = DICTAMEN.objects.get_or_create(
            sim=sim7, agenda=agenda3,
            defaults=dict(
                numero='06/26',
                conclusion='SE RECOMIENDA APROBAR LA SOLICITUD DE ASCENSO',
                abogado=abog1, pm=pm_my2,
                estado='CONFIRMADO',
                secretario=vocal_sec,
                conclusion_secretario='CONFIRMADO',
                fecha_confirmacion=date(2026, 3, 10),
            )
        )
        res7, _ = Resolucion.objects.get_or_create(
            sim=sim7, instancia='PRIMERA', numero='20/26',
            defaults=dict(
                fecha=date(2026, 3, 15),
                tipo='SOLICITUD_ASCENSO',
                texto='EL TRIBUNAL RESUELVE: APROBAR LA SOLICITUD DE ASCENSO AL GRADO INMEDIATO SUPERIOR DE MY. ANA MARIA GARCIA RIOS.',
                abogado=abog1, agenda=agenda3, dictamen=dic7, pm=pm_my2,
            ))
        Notificacion.objects.get_or_create(resolucion=res7, defaults=dict(
            tipo='FIRMA', notificado_a='MY. ANA MARIA GARCIA RIOS', fecha=date(2026, 3, 16)
        ))
        self.stdout.write('   📌 Escenario 7: SLC-001/26 → CONCLUIDO (SOLICITUD ASCENSO aprobada)')

        # ── RESUMEN FINAL ─────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("""
╔══════════════════════════════════════════════════════════════════════╗
║          ✅  BASE DE DATOS DE DEMOSTRACIÓN LISTA                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  USUARIOS DEL SISTEMA                                                ║
║  ─────────────────────────────────────────────────────────────────  ║
║  Rol            │ Usuario       │ Contraseña                        ║
║  ADMINISTRADOR  │ admin         │ admin123                          ║
║  ABOGADO 1      │ abogado1      │ abog123   (MY. RODRIGUEZ)         ║
║  ABOGADO 2      │ abogado2      │ abog123   (CAP. LLANOS)           ║
║  SECRETARIO     │ secretario    │ sec123    (VOCAL ACTAS)           ║
║  ADMIN1         │ adminvista    │ admin123                          ║
║  BUSCADOR       │ buscador1     │ buscar123                         ║
╠══════════════════════════════════════════════════════════════════════╣
║  ESCENARIOS DISPONIBLES                                              ║
║  ─────────────────────────────────────────────────────────────────  ║
║  DJE-001/26 → PARA AGENDA      (2 implicados, sin agenda aún)      ║
║  DJE-002/26 → PROCESO          (dictamen PENDIENTE de confirmar)    ║
║  DJE-003/26 → CONCLUIDO        (RES + Auto Ejecutoria)             ║
║  DJE-004/26 → PROCESO          (dictamen MODIFICADO + RR activo)   ║
║  DJE-005/26 → EN APELACION TSP (RES + RR + RAP elevado)           ║
║  DJE-006/26 → CONCLUIDO        (SOBRESEÍDO)                        ║
║  SLC-001/26 → CONCLUIDO        (SOLICITUD ASCENSO aprobada)        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Para borrar y recrear:  python manage.py poblar_bd_demo --reset   ║
╚══════════════════════════════════════════════════════════════════════╝
"""))

    # ─────────────────────────────────────────────────────────────────────────
    def _crear_usuario(self, username, password, rol, pm, vocal):
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'   - {username} ya existe, omitido')
            return
        if rol == 'ADMINISTRADOR':
            user = User.objects.create_superuser(username=username, password=password,
                                                 email=f'{username}@tpe.bo')
        else:
            user = User.objects.create_user(username=username, password=password,
                                            email=f'{username}@tpe.bo')
        PerfilUsuario.objects.create(
            user=user, rol=rol, pm=pm, vocal=vocal, activo=True)
        self.stdout.write(f'   ✅ {rol:15} → {username} / {password}')

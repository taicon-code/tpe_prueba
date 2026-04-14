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
    PM, ABOG, VOCAL_TPE, SIM, PM_SIM, ABOG_SIM,
    AGENDA, DICTAMEN, RES, RR, AUTOTPE, RAP, AUTOTSP, RAEE,
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
            RAEE.objects.all().delete()
            AUTOTSP.objects.all().delete()
            RAP.objects.all().delete()
            AUTOTPE.objects.all().delete()
            RR.objects.all().delete()
            RES.objects.all().delete()
            DICTAMEN.objects.all().delete()
            AGENDA.objects.all().delete()
            ABOG_SIM.objects.all().delete()
            PM_SIM.objects.all().delete()
            SIM.objects.all().delete()
            PM.objects.all().delete()
            ABOG.objects.all().delete()
            VOCAL_TPE.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('   Datos borrados.\n'))

        # ── 1. PERSONAL MILITAR ───────────────────────────────────────────────
        self.stdout.write('👥 Creando Personal Militar...')

        pm_tte, _ = PM.objects.get_or_create(PM_CI=10000001, defaults=dict(
            PM_ESCALAFON='OFICIAL SUBALTERNO', PM_GRADO='TTE.', PM_ARMA='INF.',
            PM_NOMBRE='JUAN', PM_PATERNO='CONDORI', PM_MATERNO='MAMANI',
            PM_ESTADO='ACTIVO', PM_ESPEC='COMBATE',
        ))
        pm_cap, _ = PM.objects.get_or_create(PM_CI=10000002, defaults=dict(
            PM_ESCALAFON='OFICIAL SUBALTERNO', PM_GRADO='CAP.', PM_ARMA='CAB.',
            PM_NOMBRE='PEDRO', PM_PATERNO='VARGAS', PM_MATERNO='QUISPE',
            PM_ESTADO='ACTIVO',
        ))
        pm_my, _ = PM.objects.get_or_create(PM_CI=10000003, defaults=dict(
            PM_ESCALAFON='OFICIAL SUPERIOR', PM_GRADO='MY.', PM_ARMA='ART.',
            PM_NOMBRE='ROBERTO', PM_PATERNO='FLORES', PM_MATERNO='CONDORI',
            PM_ESTADO='ACTIVO',
        ))
        pm_tcnl, _ = PM.objects.get_or_create(PM_CI=10000004, defaults=dict(
            PM_ESCALAFON='OFICIAL SUPERIOR', PM_GRADO='TCNL.', PM_ARMA='ING.',
            PM_NOMBRE='MARIO', PM_PATERNO='GUTIERREZ', PM_MATERNO='LOPEZ',
            PM_ESTADO='ACTIVO',
        ))
        pm_cnl, _ = PM.objects.get_or_create(PM_CI=10000005, defaults=dict(
            PM_ESCALAFON='OFICIAL SUPERIOR', PM_GRADO='CNL.', PM_ARMA='COM.',
            PM_NOMBRE='CARLOS', PM_PATERNO='MENDOZA', PM_MATERNO='TORREZ',
            PM_ESTADO='ACTIVO',
        ))
        pm_sof, _ = PM.objects.get_or_create(PM_CI=10000006, defaults=dict(
            PM_ESCALAFON='SUBOFICIAL', PM_GRADO='SOF. 1RO.', PM_ARMA='INT.',
            PM_NOMBRE='HUGO', PM_PATERNO='MAMANI', PM_MATERNO='CHOQUE',
            PM_ESTADO='ACTIVO',
        ))
        pm_my2, _ = PM.objects.get_or_create(PM_CI=10000007, defaults=dict(
            PM_ESCALAFON='OFICIAL SUPERIOR', PM_GRADO='MY.', PM_ARMA='SAN.',
            PM_NOMBRE='ANA MARIA', PM_PATERNO='GARCIA', PM_MATERNO='RIOS',
            PM_ESTADO='ACTIVO',
        ))
        # Militar adicional para sumario con dos implicados
        pm_sgto, _ = PM.objects.get_or_create(PM_CI=10000008, defaults=dict(
            PM_ESCALAFON='SARGENTO', PM_GRADO='SGTO. 1RO.', PM_ARMA='INF.',
            PM_NOMBRE='LUIS', PM_PATERNO='TICONA', PM_MATERNO='HUANCA',
            PM_ESTADO='ACTIVO',
        ))
        self.stdout.write(self.style.SUCCESS('   ✅ 8 militares creados'))

        # ── 2. ABOGADOS ───────────────────────────────────────────────────────
        self.stdout.write('⚖️  Creando Abogados...')

        abog1, _ = ABOG.objects.get_or_create(AB_CI=20000001, defaults=dict(
            AB_GRADO='MY.', AB_ARMA='INF.',
            AB_NOMBRE='JORGE', AB_PATERNO='RODRIGUEZ', AB_MATERNO='SALINAS',
        ))
        abog2, _ = ABOG.objects.get_or_create(AB_CI=20000002, defaults=dict(
            AB_GRADO='CAP.', AB_ARMA='INT.',
            AB_NOMBRE='PATRICIA', AB_PATERNO='LLANOS', AB_MATERNO='VERA',
        ))
        self.stdout.write(self.style.SUCCESS('   ✅ 2 abogados creados'))

        # ── 3. VOCALES TPE ────────────────────────────────────────────────────
        self.stdout.write('🎖️  Creando Vocales del Tribunal...')

        # Usamos militares existentes como vocales
        pm_pres, _ = PM.objects.get_or_create(PM_CI=30000001, defaults=dict(
            PM_ESCALAFON='GENERAL', PM_GRADO='GRAL. BRIG.', PM_ARMA='INF.',
            PM_NOMBRE='ANTONIO', PM_PATERNO='PEREZ', PM_MATERNO='ALBA',
            PM_ESTADO='ACTIVO',
        ))
        pm_sec, _ = PM.objects.get_or_create(PM_CI=30000002, defaults=dict(
            PM_ESCALAFON='OFICIAL SUPERIOR', PM_GRADO='MY.', PM_ARMA='COM.',
            PM_NOMBRE='SILVIA', PM_PATERNO='CHURA', PM_MATERNO='RAMOS',
            PM_ESTADO='ACTIVO',
        ))
        vocal_pres, _ = VOCAL_TPE.objects.get_or_create(
            pm=pm_pres, cargo='PRESIDENTE', defaults=dict(activo=True))
        vocal_sec, _ = VOCAL_TPE.objects.get_or_create(
            pm=pm_sec, cargo='SECRETARIO_ACTAS', defaults=dict(activo=True))
        self.stdout.write(self.style.SUCCESS('   ✅ 2 vocales creados (Presidente + Secretario de Actas)'))

        # ── 4. USUARIOS ───────────────────────────────────────────────────────
        self.stdout.write('👤 Creando Usuarios del sistema...')
        self._crear_usuario('admin',    'admin123',    'ADMINISTRADOR', None, None)
        self._crear_usuario('abogado1', 'abog123',     'ABOGADO',       abog1, None)
        self._crear_usuario('abogado2', 'abog123',     'ABOGADO',       abog2, None)
        self._crear_usuario('secretario', 'sec123',   'VOCAL_TPE',     None, vocal_sec)
        self._crear_usuario('adminvista', 'admin123',  'ADMINISTRATIVO', None, None)
        self._crear_usuario('buscador1', 'buscar123',  'BUSCADOR',      None, None)
        self.stdout.write(self.style.SUCCESS('   ✅ 6 usuarios creados'))

        # ── 5. AGENDAS ────────────────────────────────────────────────────────
        self.stdout.write('📅 Creando Agendas...')

        agenda1, _ = AGENDA.objects.get_or_create(AG_NUM='AG-001/26', defaults=dict(
            AG_FECPROG=date(2026, 3, 10),
            AG_FECREAL=date(2026, 3, 10),
            AG_TIPO='ORDINARIA',
        ))
        agenda2, _ = AGENDA.objects.get_or_create(AG_NUM='AG-002/26', defaults=dict(
            AG_FECPROG=date(2026, 3, 25),
            AG_FECREAL=date(2026, 3, 25),
            AG_TIPO='ORDINARIA',
        ))
        agenda3, _ = AGENDA.objects.get_or_create(AG_NUM='AG-003/26', defaults=dict(
            AG_FECPROG=date(2026, 4, 8),
            AG_FECREAL=date(2026, 4, 8),
            AG_TIPO='EXTRAORDINARIA',
        ))
        agenda_futura, _ = AGENDA.objects.get_or_create(AG_NUM='AG-004/26', defaults=dict(
            AG_FECPROG=date(2026, 4, 22),
            AG_FECREAL=None,
            AG_TIPO='ORDINARIA',
        ))
        self.stdout.write(self.style.SUCCESS('   ✅ 4 agendas creadas'))

        # ── 6. SUMARIOS (SIM) — 7 escenarios ─────────────────────────────────
        self.stdout.write('\n📋 Creando Sumarios con sus flujos...')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 1: PARA_AGENDA
        # SIM recién ingresado, abogado asignado, esperando agenda
        # ─────────────────────────────────────────────────────────────────────
        sim1, _ = SIM.objects.get_or_create(SIM_COD='DJE-001/26', defaults=dict(
            SIM_FECING=date(2026, 4, 10),
            SIM_ESTADO='PARA_AGENDA',
            SIM_TIPO='DISCIPLINARIO',
            SIM_OBJETO='ESTABLECER CIRCUNSTANCIAS DEL CONSUMO DE BEBIDAS ALCOHOLICAS PMA. Y ACCIDENTE DE TRANSITO',
            SIM_RESUM='BEBIDAS ALCOHOLICAS Y ACCIDENTE',
        ))
        PM_SIM.objects.get_or_create(sim=sim1, pm=pm_tte)
        PM_SIM.objects.get_or_create(sim=sim1, pm=pm_sgto)  # dos implicados
        ABOG_SIM.objects.get_or_create(sim=sim1, abog=abog1)
        self.stdout.write('   📌 Escenario 1: DJE-001/26 → PARA AGENDA (2 implicados)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 2: PROCESO_EN_EL_TPE — tiene dictamen PENDIENTE
        # ─────────────────────────────────────────────────────────────────────
        sim2, _ = SIM.objects.get_or_create(SIM_COD='DJE-002/26', defaults=dict(
            SIM_FECING=date(2026, 3, 5),
            SIM_ESTADO='PROCESO_EN_EL_TPE',
            SIM_TIPO='DISCIPLINARIO',
            SIM_OBJETO='ESTABLECER CIRCUNSTANCIAS DE MALTRATO AL PERSONAL SUBALTERNO',
            SIM_RESUM='MALTRATO AL PERSONAL',
        ))
        PM_SIM.objects.get_or_create(sim=sim2, pm=pm_cap)
        ABOG_SIM.objects.get_or_create(sim=sim2, abog=abog1)

        dic2, _ = DICTAMEN.objects.get_or_create(
            sim=sim2, agenda=agenda1,
            defaults=dict(
                DIC_NUM='01/26',
                DIC_CONCL='SE RECOMIENDA LA SANCION DISCIPLINARIA POR MALTRATO AL PERSONAL',
                abog=abog1,
                pm=pm_cap,
                DIC_ESTADO='PENDIENTE',
            )
        )
        self.stdout.write('   📌 Escenario 2: DJE-002/26 → PROCESO (dictamen pendiente)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 3: RES emitida → CONCLUIDO
        # ─────────────────────────────────────────────────────────────────────
        sim3, _ = SIM.objects.get_or_create(SIM_COD='DJE-003/26', defaults=dict(
            SIM_FECING=date(2026, 2, 10),
            SIM_ESTADO='CONCLUIDO',
            SIM_TIPO='DISCIPLINARIO',
            SIM_OBJETO='ESTABLECER CIRCUNSTANCIAS DE HURTO DE ARMAMENTO INSTITUCIONAL',
            SIM_RESUM='HURTO DE ARMAMENTO',
        ))
        PM_SIM.objects.get_or_create(sim=sim3, pm=pm_my)
        ABOG_SIM.objects.get_or_create(sim=sim3, abog=abog2)

        dic3, _ = DICTAMEN.objects.get_or_create(
            sim=sim3, agenda=agenda1,
            defaults=dict(
                DIC_NUM='02/26',
                DIC_CONCL='SE RECOMIENDA SANCION ARRESTO POR 60 DIAS',
                abog=abog2, pm=pm_my,
                DIC_ESTADO='CONFIRMADO',
                secretario=vocal_sec,
                DIC_CONCL_SEC='CONFIRMADO EL DICTAMEN SIN MODIFICACIONES',
                DIC_CONFIR_FEC=date(2026, 2, 15),
            )
        )
        res3, _ = RES.objects.get_or_create(sim=sim3, defaults=dict(
            RES_NUM='15/26',
            RES_FEC=date(2026, 2, 20),
            RES_TIPO='SANCION_ARRESTO',
            RES_RESOL='EL TRIBUNAL DE PERSONAL DEL EJERCITO RESUELVE: SANCIONAR AL MY. ROBERTO FLORES CONDORI CON 60 DIAS DE ARRESTO.',
            abog=abog2, agenda=agenda1, dictamen=dic3, pm=pm_my,
            RES_TIPO_NOTIF='FIRMA',
            RES_NOT='MY. ROBERTO FLORES CONDORI',
            RES_FECNOT=date(2026, 2, 21),
        ))
        # Auto de ejecutoria (caso terminado sin apelación)
        AUTOTPE.objects.get_or_create(sim=sim3, TPE_TIPO='AUTO_EJECUTORIA', defaults=dict(
            TPE_NUM='08/26',
            TPE_FEC=date(2026, 3, 15),
            TPE_RESOL='SE DECLARA EJECUTORIADA LA RESOLUCION NRO. 15/26 DEL TRIBUNAL DE PERSONAL.',
            abog=abog2, agenda=agenda2, pm=pm_my, res=res3,
            TPE_TIPO_NOTIF='FIRMA',
            TPE_NOT='MY. ROBERTO FLORES CONDORI',
            TPE_FECNOT=date(2026, 3, 16),
        ))
        self.stdout.write('   📌 Escenario 3: DJE-003/26 → CONCLUIDO (RES + AUTO EJECUTORIA)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 4: RES + RR en proceso
        # ─────────────────────────────────────────────────────────────────────
        sim4, _ = SIM.objects.get_or_create(SIM_COD='DJE-004/26', defaults=dict(
            SIM_FECING=date(2026, 1, 15),
            SIM_ESTADO='PROCESO_EN_EL_TPE',
            SIM_TIPO='DISCIPLINARIO',
            SIM_OBJETO='ESTABLECER CIRCUNSTANCIAS DE COBROS IRREGULARES AL PERSONAL',
            SIM_RESUM='COBROS IRREGULARES',
        ))
        PM_SIM.objects.get_or_create(sim=sim4, pm=pm_tcnl)
        ABOG_SIM.objects.get_or_create(sim=sim4, abog=abog1)

        dic4, _ = DICTAMEN.objects.get_or_create(
            sim=sim4, agenda=agenda1,
            defaults=dict(
                DIC_NUM='03/26',
                DIC_CONCL='SE RECOMIENDA SANCION LETRA B POR COBROS IRREGULARES',
                abog=abog1, pm=pm_tcnl,
                DIC_ESTADO='MODIFICADO',
                secretario=vocal_sec,
                DIC_CONCL_SEC='SE MODIFICA: SE RECOMIENDA ARCHIVO DE OBRADOS POR INSUFICIENCIA PROBATORIA',
                DIC_CONFIR_FEC=date(2026, 1, 25),
            )
        )
        res4, _ = RES.objects.get_or_create(sim=sim4, defaults=dict(
            RES_NUM='05/26',
            RES_FEC=date(2026, 2, 1),
            RES_TIPO='SANCION_LETRA_B',
            RES_RESOL='EL TRIBUNAL RESUELVE: SANCIONAR AL TCNL. MARIO GUTIERREZ LOPEZ CON LETRA B (PERDIDA DE ANTIGUEDAD).',
            abog=abog1, agenda=agenda1, dictamen=dic4, pm=pm_tcnl,
            RES_TIPO_NOTIF='CEDULON',
            RES_NOT='TCNL. MARIO GUTIERREZ LOPEZ',
            RES_FECNOT=date(2026, 2, 3),
        ))
        rr4, _ = RR.objects.get_or_create(sim=sim4, res=res4, defaults=dict(
            RR_NUM='02/26',
            RR_FECPRESEN=date(2026, 2, 10),
            # RR_FECLIMITE se calcula automáticamente en save()
            RR_FEC=None,  # pendiente de resolver
            RR_RESOL=None,
            RR_RESUM='RECURSO DE RECONSIDERACION PRESENTADO POR EL TCNL. MARIO GUTIERREZ LOPEZ',
            abog=abog1, agenda=agenda2, pm=pm_tcnl,
        ))
        self.stdout.write('   📌 Escenario 4: DJE-004/26 → RES emitida + RR pendiente (MODIFICADO por Secretario)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 5: EN_APELACION_TSP
        # ─────────────────────────────────────────────────────────────────────
        sim5, _ = SIM.objects.get_or_create(SIM_COD='DJE-005/26', defaults=dict(
            SIM_FECING=date(2025, 11, 10),
            SIM_ESTADO='EN_APELACION_TSP',
            SIM_TIPO='DISCIPLINARIO',
            SIM_OBJETO='ESTABLECER CIRCUNSTANCIAS DE INDISCIPLINA PROFESIONAL Y ABANDONO DE SERVICIO',
            SIM_RESUM='INDISCIPLINA Y ABANDONO',
        ))
        PM_SIM.objects.get_or_create(sim=sim5, pm=pm_cnl)
        ABOG_SIM.objects.get_or_create(sim=sim5, abog=abog2)

        dic5, _ = DICTAMEN.objects.get_or_create(
            sim=sim5, agenda=agenda1,
            defaults=dict(
                DIC_NUM='04/26',
                DIC_CONCL='SE RECOMIENDA SANCION RETIRO OBLIGATORIO',
                abog=abog2, pm=pm_cnl,
                DIC_ESTADO='CONFIRMADO',
                secretario=vocal_sec,
                DIC_CONCL_SEC='CONFIRMADO',
                DIC_CONFIR_FEC=date(2025, 12, 1),
            )
        )
        res5, _ = RES.objects.get_or_create(sim=sim5, defaults=dict(
            RES_NUM='52/25',
            RES_FEC=date(2025, 12, 10),
            RES_TIPO='SANCION_RETIRO_OBLIGATORIO',
            RES_RESOL='EL TRIBUNAL RESUELVE: SANCIONAR AL CNL. CARLOS MENDOZA TORREZ CON RETIRO OBLIGATORIO.',
            abog=abog2, agenda=agenda1, dictamen=dic5, pm=pm_cnl,
            RES_TIPO_NOTIF='EDICTO',
            RES_NOT='PERIODICO LA RAZON',
            RES_FECNOT=date(2025, 12, 15),
        ))
        rr5, _ = RR.objects.get_or_create(sim=sim5, res=res5, defaults=dict(
            RR_NUM='12/25',
            RR_FECPRESEN=date(2025, 12, 20),
            RR_FEC=date(2026, 1, 10),
            RR_RESOL='EL TRIBUNAL RESUELVE: MANTENER EN TODOS SUS TERMINOS LA RESOLUCION NRO. 52/25.',
            RR_RESUM='SE MANTIENE LA SANCION DE RETIRO OBLIGATORIO',
            abog=abog2, agenda=agenda2, pm=pm_cnl,
        ))
        rap5, _ = RAP.objects.get_or_create(sim=sim5, defaults=dict(
            rr=rr5,
            RAP_FECPRESEN=date(2026, 1, 15),
            RAP_OFI='OFI-012/26',
            RAP_FECOFI=date(2026, 1, 16),
            # RAP_FECLIMITE se calcula automáticamente en save()
            pm=pm_cnl,
        ))
        self.stdout.write('   📌 Escenario 5: DJE-005/26 → EN APELACION TSP (RES + RR + RAP)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 6: SOBRESEÍDO
        # ─────────────────────────────────────────────────────────────────────
        sim6, _ = SIM.objects.get_or_create(SIM_COD='DJE-006/26', defaults=dict(
            SIM_FECING=date(2026, 1, 20),
            SIM_ESTADO='CONCLUIDO',
            SIM_TIPO='DISCIPLINARIO',
            SIM_OBJETO='ESTABLECER CIRCUNSTANCIAS DE FALTA LISTA Y ABANDONO DE DESTINO',
            SIM_RESUM='FALTA LISTA Y ABANDONO',
        ))
        PM_SIM.objects.get_or_create(sim=sim6, pm=pm_sof)
        ABOG_SIM.objects.get_or_create(sim=sim6, abog=abog2)

        dic6, _ = DICTAMEN.objects.get_or_create(
            sim=sim6, agenda=agenda2,
            defaults=dict(
                DIC_NUM='05/26',
                DIC_CONCL='SE RECOMIENDA SOBRESEIMIENTO POR INSUFICIENCIA DE PRUEBAS',
                abog=abog2, pm=pm_sof,
                DIC_ESTADO='CONFIRMADO',
                secretario=vocal_sec,
                DIC_CONCL_SEC='CONFIRMADO',
                DIC_CONFIR_FEC=date(2026, 2, 5),
            )
        )
        AUTOTPE.objects.get_or_create(sim=sim6, TPE_TIPO='SOBRESEIDO', defaults=dict(
            TPE_NUM='03/26',
            TPE_FEC=date(2026, 2, 10),
            TPE_RESOL='EL TRIBUNAL DE PERSONAL DEL EJERCITO RESUELVE: DECLARAR SOBRESEIDO EL PROCESO SUMARIO CONTRA SOF. 1RO. HUGO MAMANI CHOQUE POR INSUFICIENCIA PROBATORIA.',
            abog=abog2, agenda=agenda2, pm=pm_sof,
            TPE_TIPO_NOTIF='FIRMA',
            TPE_NOT='SOF. 1RO. HUGO MAMANI CHOQUE',
            TPE_FECNOT=date(2026, 2, 11),
        ))
        self.stdout.write('   📌 Escenario 6: DJE-006/26 → CONCLUIDO (SOBRESEÍDO)')

        # ─────────────────────────────────────────────────────────────────────
        # ESCENARIO 7: SOLICITUD DE ASCENSO (no disciplinario)
        # ─────────────────────────────────────────────────────────────────────
        sim7, _ = SIM.objects.get_or_create(SIM_COD='SLC-001/26', defaults=dict(
            SIM_FECING=date(2026, 3, 1),
            SIM_ESTADO='CONCLUIDO',
            SIM_TIPO='SOLICITUD_ASCENSO_AL_GRADO_INMEDIATO_SUPERIOR',
            SIM_OBJETO='SOLICITUD DE ASCENSO AL GRADO INMEDIATO SUPERIOR POR MERITOS EXTRAORDINARIOS',
            SIM_RESUM='SOLICITUD ASCENSO',
        ))
        PM_SIM.objects.get_or_create(sim=sim7, pm=pm_my2)
        ABOG_SIM.objects.get_or_create(sim=sim7, abog=abog1)

        dic7, _ = DICTAMEN.objects.get_or_create(
            sim=sim7, agenda=agenda3,
            defaults=dict(
                DIC_NUM='06/26',
                DIC_CONCL='SE RECOMIENDA APROBAR LA SOLICITUD DE ASCENSO',
                abog=abog1, pm=pm_my2,
                DIC_ESTADO='CONFIRMADO',
                secretario=vocal_sec,
                DIC_CONCL_SEC='CONFIRMADO',
                DIC_CONFIR_FEC=date(2026, 3, 10),
            )
        )
        res7, _ = RES.objects.get_or_create(sim=sim7, defaults=dict(
            RES_NUM='20/26',
            RES_FEC=date(2026, 3, 15),
            RES_TIPO='SOLICITUD_ASCENSO',
            RES_RESOL='EL TRIBUNAL RESUELVE: APROBAR LA SOLICITUD DE ASCENSO AL GRADO INMEDIATO SUPERIOR DE MY. ANA MARIA GARCIA RIOS.',
            abog=abog1, agenda=agenda3, dictamen=dic7, pm=pm_my2,
            RES_TIPO_NOTIF='FIRMA',
            RES_NOT='MY. ANA MARIA GARCIA RIOS',
            RES_FECNOT=date(2026, 3, 16),
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
║  ADMINISTRATIVO │ adminvista    │ admin123                          ║
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
    def _crear_usuario(self, username, password, rol, abogado, vocal):
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'   ⏭  {username} ya existe, omitido')
            return
        if rol == 'ADMINISTRADOR':
            user = User.objects.create_superuser(username=username, password=password,
                                                 email=f'{username}@tpe.bo')
        else:
            user = User.objects.create_user(username=username, password=password,
                                            email=f'{username}@tpe.bo')
        PerfilUsuario.objects.create(
            user=user, rol=rol, abogado=abogado, vocal=vocal, activo=True)
        self.stdout.write(f'   ✅ {rol:15} → {username} / {password}')

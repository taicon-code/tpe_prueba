"""
Management command para importar el histórico de sumarios desde Excel.

Uso:
    python manage.py importar_historico plantilla_historico_sim.xlsx
    python manage.py importar_historico plantilla_historico_sim.xlsx --dry-run
    python manage.py importar_historico plantilla_historico_sim.xlsx --desde-hoja 4_RES

Opciones:
    --dry-run        Valida el archivo sin insertar nada en la base de datos
    --desde-hoja     Nombre de la hoja desde donde continuar (ej: 4_RES)
    --log            Ruta del archivo de log (default: importacion_historico.log)
"""

import os
import sys
import logging
from datetime import date, time, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from openpyxl import load_workbook

from tpe_app.models import (
    PM, SIM, PM_SIM,
    AUTOTPE, Resolucion, RecursoTSP,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_fecha(valor) -> date | None:
    """Convierte distintos formatos a date. Retorna None si está vacío."""
    if valor is None or str(valor).strip() == "":
        return None
    if isinstance(valor, (date, datetime)):
        return valor.date() if isinstance(valor, datetime) else valor
    texto = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha no reconocida: '{texto}'")


def _parse_hora(valor) -> time | None:
    """Convierte HH:MM a time. Retorna None si está vacío."""
    if valor is None or str(valor).strip() == "":
        return None
    if isinstance(valor, time):
        return valor
    if isinstance(valor, datetime):
        return valor.time()
    texto = str(valor).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(texto, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Hora no reconocida: '{texto}'")


def _str(valor) -> str | None:
    """Limpia y convierte a string. Retorna None si está vacío."""
    if valor is None:
        return None
    s = str(valor).strip()
    return s if s else None


def _ci(valor):
    """Convierte cédula a int o None."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None


def _iter_filas(ws, encabezado_fila=2, datos_desde=3):
    """
    Genera dicts {nombre_columna: valor} para cada fila de datos.
    Salta filas completamente vacías.
    """
    headers = []
    for cell in ws[encabezado_fila]:
        # Limpiar saltos de línea del encabezado
        h = str(cell.value or "").split("\n")[0].strip()
        headers.append(h)

    for row in ws.iter_rows(min_row=datos_desde, values_only=True):
        # Saltar fila si todas las celdas están vacías
        if all(v is None or str(v).strip() == "" for v in row):
            continue
        yield dict(zip(headers, row))


# ─── Command ─────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Importa el histórico de sumarios SIM desde la plantilla Excel."

    def add_arguments(self, parser):
        parser.add_argument(
            "archivo",
            type=str,
            help="Ruta al archivo Excel (plantilla_historico_sim.xlsx)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Valida sin insertar datos.",
        )
        parser.add_argument(
            "--desde-hoja",
            type=str,
            default=None,
            help="Nombre de la hoja desde donde continuar (ej: 4_RES).",
        )
        parser.add_argument(
            "--log",
            type=str,
            default="importacion_historico.log",
            help="Ruta del archivo de log (default: importacion_historico.log).",
        )

    # ── Entry point ───────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        archivo  = options["archivo"]
        dry_run  = options["dry_run"]
        desde    = options["desde_hoja"]
        log_path = options["log"]

        # Configurar logger
        logging.basicConfig(
            filename=log_path,
            filemode="a",
            encoding="utf-8",
            format="%(asctime)s [%(levelname)s] %(message)s",
            level=logging.DEBUG,
        )
        self.log = logging.getLogger(__name__)

        if not Path(archivo).exists():
            raise CommandError(f"Archivo no encontrado: {archivo}")

        self.stdout.write(f"\nCargando: {archivo}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  MODO DRY-RUN — no se insertara nada\n"))

        wb = load_workbook(archivo, data_only=True)

        # Contadores globales
        self.ok    = {}   # {hoja: cantidad insertada}
        self.skip  = {}   # {hoja: cantidad omitida}
        self.errores = [] # [(hoja, fila, mensaje)]

        # Orden y función de cada hoja
        pasos = [
            ("1_SIM",     self._importar_sim),
            ("2_PM",      self._importar_pm),
            ("3_PM_SIM",  self._importar_pm_sim),
            ("4_RES",     self._importar_res),
            ("5_RR",      self._importar_rr),
            ("6_RAP",     self._importar_rap),
            ("7_AUTOTPE", self._importar_autotpe),
            ("8_RAEE",    self._importar_raee),
        ]

        # Saltar hojas si se indicó --desde-hoja
        activo = desde is None
        for nombre_hoja, fn in pasos:
            if not activo:
                if nombre_hoja == desde:
                    activo = True
                else:
                    self.stdout.write(f"  [SALTADA] {nombre_hoja}")
                    continue

            if nombre_hoja not in wb.sheetnames:
                self.stdout.write(self.style.WARNING(f"  [NO ENCONTRADA] {nombre_hoja}"))
                continue

            ws = wb[nombre_hoja]
            self.stdout.write(f"\n  Procesando hoja: {nombre_hoja} ...")

            try:
                if dry_run:
                    with transaction.atomic():
                        fn(ws, nombre_hoja)
                        transaction.set_rollback(True)
                else:
                    with transaction.atomic():
                        fn(ws, nombre_hoja)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"    ERROR CRITICO en {nombre_hoja}: {exc}"))
                self.log.exception(f"ERROR CRITICO en {nombre_hoja}")

        self._imprimir_resumen(dry_run, log_path)

    # ── Resumen final ─────────────────────────────────────────────────────────

    def _imprimir_resumen(self, dry_run, log_path):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RESUMEN DE IMPORTACION")
        if dry_run:
            self.stdout.write(self.style.WARNING("  (DRY-RUN — ningun dato fue guardado)"))
        self.stdout.write("=" * 60)

        total_ok   = 0
        total_skip = 0
        for hoja in self.ok:
            ok   = self.ok.get(hoja, 0)
            skip = self.skip.get(hoja, 0)
            total_ok   += ok
            total_skip += skip
            self.stdout.write(f"  {hoja:<14}  insertados: {ok:>5}   omitidos: {skip:>5}")

        self.stdout.write("-" * 60)
        self.stdout.write(f"  TOTAL           insertados: {total_ok:>5}   omitidos: {total_skip:>5}")

        if self.errores:
            self.stdout.write(self.style.ERROR(f"\n  ERRORES ({len(self.errores)}):"))
            for hoja, num_fila, msg in self.errores[:20]:
                self.stdout.write(self.style.ERROR(f"    [{hoja} fila {num_fila}] {msg}"))
            if len(self.errores) > 20:
                self.stdout.write(self.style.ERROR(f"    ... y {len(self.errores)-20} mas. Ver: {log_path}"))
        else:
            self.stdout.write(self.style.SUCCESS("\n  Sin errores."))

        self.stdout.write(f"\n  Log completo: {log_path}\n")

    # ── Registro de resultados ────────────────────────────────────────────────

    def _registrar_ok(self, hoja):
        self.ok[hoja] = self.ok.get(hoja, 0) + 1

    def _registrar_skip(self, hoja, num_fila, motivo):
        self.skip[hoja] = self.skip.get(hoja, 0) + 1
        self.log.warning(f"[{hoja} fila {num_fila}] OMITIDA: {motivo}")

    def _registrar_error(self, hoja, num_fila, exc):
        self.errores.append((hoja, num_fila, str(exc)))
        self.log.error(f"[{hoja} fila {num_fila}] {exc}", exc_info=True)

    # ═════════════════════════════════════════════════════════════════════════
    # IMPORTADORES POR HOJA
    # ═════════════════════════════════════════════════════════════════════════

    # ── Hoja 1: SIM ──────────────────────────────────────────────────────────

    def _importar_sim(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod = _str(fila.get("SIM_COD"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "SIM_COD vacio")
                    continue

                objeto = _str(fila.get("SIM_OBJETO"))
                resum  = _str(fila.get("SIM_RESUM"))
                tipo   = _str(fila.get("SIM_TIPO"))
                if not objeto:
                    self._registrar_skip(hoja, num_fila, f"{cod}: SIM_OBJETO vacio")
                    continue
                if not resum:
                    self._registrar_skip(hoja, num_fila, f"{cod}: SIM_RESUM vacio")
                    continue
                if not tipo:
                    self._registrar_skip(hoja, num_fila, f"{cod}: SIM_TIPO vacio")
                    continue

                _, creado = SIM.objects.get_or_create(
                    SIM_COD=cod.upper(),
                    defaults=dict(
                        SIM_FECING=_parse_fecha(fila.get("SIM_FECING")),
                        SIM_ESTADO=_str(fila.get("SIM_ESTADO")) or "PARA_AGENDA",
                        SIM_OBJETO=objeto.upper(),
                        SIM_RESUM=resum.upper()[:200],
                        SIM_AUTOFINAL=(_str(fila.get("SIM_AUTOFINAL")) or ""),
                        SIM_TIPO=tipo.upper(),
                    ),
                )
                if creado:
                    self._registrar_ok(hoja)
                else:
                    self._registrar_skip(hoja, num_fila, f"{cod}: ya existe, omitido")
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 2: PM ───────────────────────────────────────────────────────────

    def _importar_pm(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                nombre  = _str(fila.get("PM_NOMBRE"))
                paterno = _str(fila.get("PM_PATERNO"))
                ci      = _ci(fila.get("PM_CI"))

                if not nombre or not paterno:
                    self._registrar_skip(hoja, num_fila, "PM_NOMBRE o PM_PATERNO vacios")
                    continue

                # Buscar por CI si existe, sino por nombre+paterno
                if ci:
                    pm, creado = PM.objects.get_or_create(
                        PM_CI=ci,
                        defaults=dict(
                            PM_NOMBRE=nombre.upper(),
                            PM_PATERNO=paterno.upper(),
                            PM_MATERNO=(_str(fila.get("PM_MATERNO")) or "").upper() or None,
                            PM_ESCALAFON=_str(fila.get("PM_ESCALAFON")),
                            PM_GRADO=_str(fila.get("PM_GRADO")),
                            PM_ARMA=_str(fila.get("PM_ARMA")),
                            PM_ESPEC=(_str(fila.get("PM_ESPEC")) or "").upper() or None,
                            PM_ESTADO=_str(fila.get("PM_ESTADO")) or "ACTIVO",
                            PM_PROMOCION=_parse_fecha(fila.get("PM_PROMOCION")),
                        ),
                    )
                else:
                    pm, creado = PM.objects.get_or_create(
                        PM_NOMBRE=nombre.upper(),
                        PM_PATERNO=paterno.upper(),
                        defaults=dict(
                            PM_MATERNO=(_str(fila.get("PM_MATERNO")) or "").upper() or None,
                            PM_ESCALAFON=_str(fila.get("PM_ESCALAFON")),
                            PM_GRADO=_str(fila.get("PM_GRADO")),
                            PM_ARMA=_str(fila.get("PM_ARMA")),
                            PM_ESPEC=(_str(fila.get("PM_ESPEC")) or "").upper() or None,
                            PM_ESTADO=_str(fila.get("PM_ESTADO")) or "ACTIVO",
                            PM_PROMOCION=_parse_fecha(fila.get("PM_PROMOCION")),
                        ),
                    )

                if creado:
                    self._registrar_ok(hoja)
                else:
                    self._registrar_skip(hoja, num_fila, f"{nombre} {paterno}: ya existe, omitido")
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 3: PM_SIM ───────────────────────────────────────────────────────

    def _importar_pm_sim(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod = _str(fila.get("SIM_COD"))
                ci  = _ci(fila.get("PM_CI"))

                if not cod or not ci:
                    self._registrar_skip(hoja, num_fila, "SIM_COD o PM_CI vacios")
                    continue

                sim = SIM.objects.filter(SIM_COD=cod.upper(), SIM_VERSION=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}")
                    continue

                try:
                    pm = PM.objects.get(PM_CI=ci)
                except PM.DoesNotExist:
                    self._registrar_skip(hoja, num_fila, f"PM no encontrado con CI: {ci}")
                    continue

                _, creado = PM_SIM.objects.get_or_create(sim=sim, pm=pm)
                if creado:
                    self._registrar_ok(hoja)
                else:
                    self._registrar_skip(hoja, num_fila, f"{cod}+{ci}: relacion ya existe")
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 4: RES ──────────────────────────────────────────────────────────

    def _importar_res(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod     = _str(fila.get("SIM_COD"))
                res_num = _str(fila.get("RES_NUM"))
                res_fec = _parse_fecha(fila.get("RES_FEC"))
                res_tipo= _str(fila.get("RES_TIPO"))
                res_res = _str(fila.get("RES_RESOL"))

                if not cod:
                    self._registrar_skip(hoja, num_fila, "SIM_COD vacio"); continue
                if not res_num:
                    self._registrar_skip(hoja, num_fila, f"{cod}: RES_NUM vacio"); continue
                if not res_fec:
                    self._registrar_skip(hoja, num_fila, f"{cod}: RES_FEC vacio"); continue
                if not res_tipo:
                    self._registrar_skip(hoja, num_fila, f"{cod}: RES_TIPO vacio"); continue
                if not res_res:
                    self._registrar_skip(hoja, num_fila, f"{cod}: RES_RESOL vacio"); continue

                sim = SIM.objects.filter(SIM_COD=cod.upper(), SIM_VERSION=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                _, creado = Resolucion.objects.get_or_create(
                    sim=sim,
                    RES_INSTANCIA='PRIMERA',
                    RES_NUM=res_num.upper(),
                    defaults=dict(
                        RES_FEC=res_fec,
                        RES_TIPO=res_tipo,
                        RES_RESOL=res_res.upper(),
                        RES_TIPO_NOTIF=_str(fila.get("RES_TIPO_NOTIF")),
                        RES_NOT=_str(fila.get("RES_NOT")),
                        RES_FECNOT=_parse_fecha(fila.get("RES_FECNOT")),
                        RES_HORNOT=_parse_hora(fila.get("RES_HORNOT")),
                    ),
                )
                if creado:
                    self._registrar_ok(hoja)
                else:
                    self._registrar_skip(hoja, num_fila, f"{cod}/{res_num}: ya existe")
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 5: RR ───────────────────────────────────────────────────────────

    def _importar_rr(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod     = _str(fila.get("SIM_COD"))
                res_num = _str(fila.get("RES_NUM"))

                if not cod:
                    self._registrar_skip(hoja, num_fila, "SIM_COD vacio"); continue
                if not res_num:
                    self._registrar_skip(hoja, num_fila, f"{cod}: RES_NUM vacio"); continue

                sim = SIM.objects.filter(SIM_COD=cod.upper(), SIM_VERSION=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                try:
                    res = Resolucion.objects.get(
                        sim=sim, RES_INSTANCIA='PRIMERA', RES_NUM=res_num.upper()
                    )
                except Resolucion.DoesNotExist:
                    self._registrar_skip(hoja, num_fila, f"RES no encontrada: {res_num} en {cod}"); continue
                except Resolucion.MultipleObjectsReturned:
                    res = Resolucion.objects.filter(
                        sim=sim, RES_INSTANCIA='PRIMERA', RES_NUM=res_num.upper()
                    ).first()

                # Un sumario solo tiene un RR por resolución PRIMERA
                if Resolucion.objects.filter(
                    sim=sim, RES_INSTANCIA='RECONSIDERACION', resolucion_origen=res
                ).exists():
                    self._registrar_skip(hoja, num_fila, f"{cod}: RR ya existe para {res_num}"); continue

                Resolucion.objects.create(
                    sim=sim,
                    RES_INSTANCIA='RECONSIDERACION',
                    resolucion_origen=res,
                    RES_FECPRESEN=_parse_fecha(fila.get("RR_FECPRESEN")),
                    RES_NUM=_str(fila.get("RR_NUM")),
                    RES_FEC=_parse_fecha(fila.get("RR_FEC")),
                    RES_RESOL=(_str(fila.get("RR_RESOL")) or "").upper() or None,
                    RES_RESUM=((_str(fila.get("RR_RESUM")) or "")[:20]) or None,
                    RES_TIPO_NOTIF=_str(fila.get("RR_TIPO_NOTIF")),
                    RES_NOT=_str(fila.get("RR_NOT")),
                    RES_FECNOT=_parse_fecha(fila.get("RR_FECNOT")),
                    RES_HORNOT=_parse_hora(fila.get("RR_HORNOT")),
                )
                self._registrar_ok(hoja)
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 6: RAP ──────────────────────────────────────────────────────────

    def _importar_rap(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod = _str(fila.get("SIM_COD"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "SIM_COD vacio"); continue

                sim = SIM.objects.filter(SIM_COD=cod.upper(), SIM_VERSION=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                if RecursoTSP.objects.filter(sim=sim, TSP_INSTANCIA='APELACION').exists():
                    self._registrar_skip(hoja, num_fila, f"{cod}: RAP ya existe"); continue

                RecursoTSP.objects.create(
                    sim=sim,
                    TSP_INSTANCIA='APELACION',
                    TSP_FECPRESEN=_parse_fecha(fila.get("RAP_FECPRESEN")),
                    TSP_OFI=_str(fila.get("RAP_OFI")),
                    TSP_FECOFI=_parse_fecha(fila.get("RAP_FECOFI")),
                    TSP_NUM=_str(fila.get("RAP_NUM")),
                    TSP_FEC=_parse_fecha(fila.get("RAP_FEC")),
                    TSP_TIPO=_str(fila.get("RAP_TIPO")),
                    TSP_RESOL=(_str(fila.get("RAP_RESOL")) or "").upper() or None,
                    TSP_TIPO_NOTIF=_str(fila.get("RAP_TIPO_NOTIF")),
                    TSP_NOT=_str(fila.get("RAP_NOT")),
                    TSP_FECNOT=_parse_fecha(fila.get("RAP_FECNOT")),
                    TSP_HORNOT=_parse_hora(fila.get("RAP_HORNOT")),
                )
                self._registrar_ok(hoja)
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 7: AUTOTPE ──────────────────────────────────────────────────────

    def _importar_autotpe(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod = _str(fila.get("SIM_COD"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "SIM_COD vacio"); continue

                sim = SIM.objects.filter(SIM_COD=cod.upper(), SIM_VERSION=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                AUTOTPE.objects.create(
                    sim=sim,
                    TPE_NUM=_str(fila.get("TPE_NUM")),
                    TPE_FEC=_parse_fecha(fila.get("TPE_FEC")),
                    TPE_TIPO=_str(fila.get("TPE_TIPO")),
                    TPE_RESOL=(_str(fila.get("TPE_RESOL")) or "").upper() or None,
                    TPE_TIPO_NOTIF=_str(fila.get("TPE_TIPO_NOTIF")),
                    TPE_NOT=_str(fila.get("TPE_NOT")),
                    TPE_FECNOT=_parse_fecha(fila.get("TPE_FECNOT")),
                    TPE_HORNOT=_parse_hora(fila.get("TPE_HORNOT")),
                    TPE_MEMO_NUM=_str(fila.get("TPE_MEMO_NUM")),
                    TPE_MEMO_FEC=_parse_fecha(fila.get("TPE_MEMO_FEC")),
                    TPE_MEMO_ENTREGA=_parse_fecha(fila.get("TPE_MEMO_ENTREGA")),
                )
                self._registrar_ok(hoja)
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

    # ── Hoja 8: RAEE ─────────────────────────────────────────────────────────

    def _importar_raee(self, ws, hoja):
        for num_fila, fila in enumerate(
            _iter_filas(ws), start=3
        ):
            try:
                cod = _str(fila.get("SIM_COD"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "SIM_COD vacio"); continue

                sim = SIM.objects.filter(SIM_COD=cod.upper(), SIM_VERSION=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                RecursoTSP.objects.create(
                    sim=sim,
                    TSP_INSTANCIA='ACLARACION_ENMIENDA',
                    TSP_NUM=_str(fila.get("RAE_NUM")),
                    TSP_FEC=_parse_fecha(fila.get("RAE_FEC")),
                    TSP_RESOL=(_str(fila.get("RAE_RESOL")) or "").upper() or None,
                    TSP_RESUM=(_str(fila.get("RAE_RESUM")) or "")[:200] or None,
                    TSP_TIPO_NOTIF=_str(fila.get("RAE_TIPO_NOTIF")),
                    TSP_NOT=_str(fila.get("RAE_NOT")),
                    TSP_FECNOT=_parse_fecha(fila.get("RAE_FECNOT")),
                    TSP_HORNOT=_parse_hora(fila.get("RAE_HORNOT")),
                )
                self._registrar_ok(hoja)
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

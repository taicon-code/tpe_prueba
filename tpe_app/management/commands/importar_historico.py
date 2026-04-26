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
                cod = _str(fila.get("codigo"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "codigo vacio")
                    continue

                objeto = _str(fila.get("objeto"))
                resum  = _str(fila.get("resumen"))
                tipo   = _str(fila.get("tipo"))
                if not objeto:
                    self._registrar_skip(hoja, num_fila, f"{cod}: objeto vacio")
                    continue
                if not resum:
                    self._registrar_skip(hoja, num_fila, f"{cod}: resumen vacio")
                    continue
                if not tipo:
                    self._registrar_skip(hoja, num_fila, f"{cod}: tipo vacio")
                    continue

                _, creado = SIM.objects.get_or_create(
                    codigo=cod.upper(),
                    defaults=dict(
                        fecha_ingreso=_parse_fecha(fila.get("fecha_ingreso")),
                        estado=_str(fila.get("estado")) or "PARA_AGENDA",
                        objeto=objeto.upper(),
                        resumen=resum.upper()[:200],
                        auto_final=(_str(fila.get("auto_final")) or ""),
                        tipo=tipo.upper(),
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
                nombre  = _str(fila.get("nombre"))
                paterno = _str(fila.get("paterno"))
                ci      = _ci(fila.get("ci"))

                if not nombre or not paterno:
                    self._registrar_skip(hoja, num_fila, "nombre o paterno vacios")
                    continue

                # Buscar por CI si existe, sino por nombre+paterno
                if ci:
                    pm, creado = PM.objects.get_or_create(
                        ci=ci,
                        defaults=dict(
                            nombre=nombre.upper(),
                            paterno=paterno.upper(),
                            materno=(_str(fila.get("materno")) or "").upper() or None,
                            escalafon=_str(fila.get("escalafon")),
                            grado=_str(fila.get("grado")),
                            arma=_str(fila.get("arma")),
                            especialidad=(_str(fila.get("especialidad")) or "").upper() or None,
                            estado=_str(fila.get("estado")) or "ACTIVO",
                            anio_promocion=_parse_fecha(fila.get("anio_promocion")),
                        ),
                    )
                else:
                    pm, creado = PM.objects.get_or_create(
                        nombre=nombre.upper(),
                        paterno=paterno.upper(),
                        defaults=dict(
                            materno=(_str(fila.get("materno")) or "").upper() or None,
                            escalafon=_str(fila.get("escalafon")),
                            grado=_str(fila.get("grado")),
                            arma=_str(fila.get("arma")),
                            especialidad=(_str(fila.get("especialidad")) or "").upper() or None,
                            estado=_str(fila.get("estado")) or "ACTIVO",
                            anio_promocion=_parse_fecha(fila.get("anio_promocion")),
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
                cod = _str(fila.get("codigo"))
                ci  = _ci(fila.get("ci"))

                if not cod or not ci:
                    self._registrar_skip(hoja, num_fila, "codigo o ci vacios")
                    continue

                sim = SIM.objects.filter(codigo=cod.upper(), version=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}")
                    continue

                try:
                    pm = PM.objects.get(ci=ci)
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
                cod     = _str(fila.get("codigo"))
                res_num = _str(fila.get("numero"))
                res_fec = _parse_fecha(fila.get("fecha"))
                res_tipo= _str(fila.get("tipo"))
                res_res = _str(fila.get("texto"))

                if not cod:
                    self._registrar_skip(hoja, num_fila, "codigo vacio"); continue
                if not res_num:
                    self._registrar_skip(hoja, num_fila, f"{cod}: numero vacio"); continue
                if not res_fec:
                    self._registrar_skip(hoja, num_fila, f"{cod}: fecha vacio"); continue
                if not res_tipo:
                    self._registrar_skip(hoja, num_fila, f"{cod}: tipo vacio"); continue
                if not res_res:
                    self._registrar_skip(hoja, num_fila, f"{cod}: texto vacio"); continue

                sim = SIM.objects.filter(codigo=cod.upper(), version=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                _, creado = Resolucion.objects.get_or_create(
                    sim=sim,
                    instancia='PRIMERA',
                    numero=res_num.upper(),
                    defaults=dict(
                        fecha=res_fec,
                        tipo=res_tipo,
                        texto=res_res.upper(),
                        tipo_notif=_str(fila.get("tipo_notif")),
                        notif_a=_str(fila.get("notif_a")),
                        fecha_notif=_parse_fecha(fila.get("fecha_notif")),
                        hora_notif=_parse_hora(fila.get("hora_notif")),
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
                cod     = _str(fila.get("codigo"))
                res_num = _str(fila.get("numero"))

                if not cod:
                    self._registrar_skip(hoja, num_fila, "codigo vacio"); continue
                if not res_num:
                    self._registrar_skip(hoja, num_fila, f"{cod}: numero vacio"); continue

                sim = SIM.objects.filter(codigo=cod.upper(), version=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                try:
                    res = Resolucion.objects.get(
                        sim=sim, instancia='PRIMERA', numero=res_num.upper()
                    )
                except Resolucion.DoesNotExist:
                    self._registrar_skip(hoja, num_fila, f"RES no encontrada: {res_num} en {cod}"); continue
                except Resolucion.MultipleObjectsReturned:
                    res = Resolucion.objects.filter(
                        sim=sim, instancia='PRIMERA', numero=res_num.upper()
                    ).first()

                # Un sumario solo tiene un RR por resolución PRIMERA
                if Resolucion.objects.filter(
                    sim=sim, instancia='RECONSIDERACION', resolucion_origen=res
                ).exists():
                    self._registrar_skip(hoja, num_fila, f"{cod}: RR ya existe para {res_num}"); continue

                Resolucion.objects.create(
                    sim=sim,
                    instancia='RECONSIDERACION',
                    resolucion_origen=res,
                    fecha_presentacion=_parse_fecha(fila.get("RR_FECPRESEN")),
                    numero=_str(fila.get("RR_NUM")),
                    fecha=_parse_fecha(fila.get("RR_FEC")),
                    texto=(_str(fila.get("RR_RESOL")) or "").upper() or None,
                    resumen=((_str(fila.get("RR_RESUM")) or "")[:20]) or None,
                    tipo_notif=_str(fila.get("RR_TIPO_NOTIF")),
                    notif_a=_str(fila.get("RR_NOT")),
                    fecha_notif=_parse_fecha(fila.get("RR_FECNOT")),
                    hora_notif=_parse_hora(fila.get("RR_HORNOT")),
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
                cod = _str(fila.get("codigo"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "codigo vacio"); continue

                sim = SIM.objects.filter(codigo=cod.upper(), version=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                if RecursoTSP.objects.filter(sim=sim, instancia='APELACION').exists():
                    self._registrar_skip(hoja, num_fila, f"{cod}: RAP ya existe"); continue

                RecursoTSP.objects.create(
                    sim=sim,
                    instancia='APELACION',
                    fechaPRESEN=_parse_fecha(fila.get("RAP_FECPRESEN")),
                    numero_oficio=_str(fila.get("RAP_OFI")),
                    fechaOFI=_parse_fecha(fila.get("RAP_FECOFI")),
                    numero=_str(fila.get("RAP_NUM")),
                    fecha=_parse_fecha(fila.get("RAP_FEC")),
                    tipo=_str(fila.get("RAP_TIPO")),
                    texto=(_str(fila.get("RAP_RESOL")) or "").upper() or None,
                    tipo_notif=_str(fila.get("RAP_TIPO_NOTIF")),
                    notif_a=_str(fila.get("RAP_NOT")),
                    fecha_notif=_parse_fecha(fila.get("RAP_FECNOT")),
                    hora_notif=_parse_hora(fila.get("RAP_HORNOT")),
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
                cod = _str(fila.get("codigo"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "codigo vacio"); continue

                sim = SIM.objects.filter(codigo=cod.upper(), version=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                AUTOTPE.objects.create(
                    sim=sim,
                    numero=_str(fila.get("numero")),
                    fecha=_parse_fecha(fila.get("fecha")),
                    tipo=_str(fila.get("tipo")),
                    texto=(_str(fila.get("texto")) or "").upper() or None,
                    tipo_notif=_str(fila.get("tipo_notif")),
                    notif_a=_str(fila.get("notif_a")),
                    fecha_notif=_parse_fecha(fila.get("fecha_notif")),
                    hora_notif=_parse_hora(fila.get("hora_notif")),
                    memo_numero=_str(fila.get("memo_numero")),
                    memo_fecha=_parse_fecha(fila.get("memo_fecha")),
                    memo_fecha_entrega=_parse_fecha(fila.get("memo_fecha_entrega")),
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
                cod = _str(fila.get("codigo"))
                if not cod:
                    self._registrar_skip(hoja, num_fila, "codigo vacio"); continue

                sim = SIM.objects.filter(codigo=cod.upper(), version=1).first()
                if not sim:
                    self._registrar_skip(hoja, num_fila, f"SIM no encontrado: {cod}"); continue

                RecursoTSP.objects.create(
                    sim=sim,
                    instancia='ACLARACION_ENMIENDA',
                    numero=_str(fila.get("RAE_NUM")),
                    fecha=_parse_fecha(fila.get("RAE_FEC")),
                    texto=(_str(fila.get("RAE_RESOL")) or "").upper() or None,
                    resumen=(_str(fila.get("RAE_RESUM")) or "")[:200] or None,
                    tipo_notif=_str(fila.get("RAE_TIPO_NOTIF")),
                    notif_a=_str(fila.get("RAE_NOT")),
                    fecha_notif=_parse_fecha(fila.get("RAE_FECNOT")),
                    hora_notif=_parse_hora(fila.get("RAE_HORNOT")),
                )
                self._registrar_ok(hoja)
            except Exception as exc:
                self._registrar_error(hoja, num_fila, exc)

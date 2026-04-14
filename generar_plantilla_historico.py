"""
Genera la plantilla Excel para carga masiva del histórico de sumarios (SIM).
Ejecutar desde la raíz del proyecto:
    python generar_plantilla_historico.py

Produce: plantilla_historico_sim.xlsx
"""

from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, Protection
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

# ─── Paleta de colores ───────────────────────────────────────────────────────
COLOR_REQUERIDO  = "C00000"   # Rojo oscuro — campo obligatorio
COLOR_OPCIONAL   = "203864"   # Azul oscuro  — campo opcional
COLOR_FK         = "833C00"   # Marrón       — clave foránea
COLOR_HEADER_BG  = "1F3864"   # Fondo header (azul marino)
COLOR_EJEMPLO_BG = "E2EFDA"   # Fondo fila ejemplo (verde claro)
COLOR_NOTA_BG    = "FFF2CC"   # Fondo celda nota (amarillo)

FILL_REQUERIDO  = PatternFill("solid", fgColor=COLOR_REQUERIDO)
FILL_OPCIONAL   = PatternFill("solid", fgColor=COLOR_OPCIONAL)
FILL_FK         = PatternFill("solid", fgColor=COLOR_FK)
FILL_HEADER     = PatternFill("solid", fgColor=COLOR_HEADER_BG)
FILL_EJEMPLO    = PatternFill("solid", fgColor=COLOR_EJEMPLO_BG)
FILL_NOTA       = PatternFill("solid", fgColor=COLOR_NOTA_BG)

FONT_HEADER  = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
FONT_LABEL   = Font(bold=True, color="FFFFFF", name="Calibri", size=9)
FONT_EJEMPLO = Font(italic=True, name="Calibri", size=9)
FONT_NORMAL  = Font(name="Calibri", size=9)
FONT_NOTA    = Font(bold=True, name="Calibri", size=9)

THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"),
)

ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT   = Alignment(horizontal="left",   vertical="center", wrap_text=True)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def _header_cell(ws, row, col, text, fill):
    c = ws.cell(row=row, column=col, value=text)
    c.fill = fill
    c.font = FONT_LABEL
    c.alignment = ALIGN_CENTER
    c.border = THIN_BORDER
    return c


def _data_cell(ws, row, col, value=""):
    c = ws.cell(row=row, column=col, value=value)
    c.font = FONT_EJEMPLO
    c.fill = FILL_EJEMPLO
    c.alignment = ALIGN_LEFT
    c.border = THIN_BORDER
    return c


def _add_validation(ws, choices, col_letter, start_row=3, end_row=5002):
    """Agrega dropdown de validación para una columna."""
    formula = '"' + ",".join(choices) + '"'
    dv = DataValidation(
        type="list",
        formula1=formula,
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Valor inválido",
        error="Seleccione un valor de la lista desplegable.",
    )
    ws.add_data_validation(dv)
    dv.sqref = f"{col_letter}{start_row}:{col_letter}{end_row}"


def _autofit(ws, min_width=12, max_width=40):
    """Ajusta el ancho de columnas."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, min_width), max_width)


def _freeze_and_filter(ws, freeze_cell="A3", filter_range=None):
    ws.freeze_panes = freeze_cell
    if filter_range:
        ws.auto_filter.ref = filter_range


def _build_sheet(ws, columns, example_row, title=None):
    """
    columns = [(header_text, fill, validation_choices_or_None, width), ...]
    example_row = [val1, val2, ...]
    """
    ROW_TITLE   = 1
    ROW_HEADERS = 2
    ROW_EJEMPLO = 3

    # ── Fila 1: título de la hoja ──────────────────────────────────────────
    if title:
        ws.merge_cells(start_row=1, start_column=1,
                       end_row=1,   end_column=len(columns))
        c = ws.cell(row=1, column=1, value=title)
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.font = Font(bold=True, color="FFFFFF", size=12, name="Calibri")
        c.alignment = ALIGN_CENTER
        ws.row_dimensions[1].height = 22

    # ── Fila 2: encabezados ────────────────────────────────────────────────
    for idx, (header, fill, _, _w) in enumerate(columns, start=1):
        _header_cell(ws, ROW_HEADERS, idx, header, fill)
    ws.row_dimensions[2].height = 36

    # ── Fila 3: ejemplo ────────────────────────────────────────────────────
    for idx, val in enumerate(example_row, start=1):
        _data_cell(ws, ROW_EJEMPLO, idx, val)
    ws.row_dimensions[3].height = 18

    # ── Validaciones y anchos ─────────────────────────────────────────────
    for idx, (_, _, choices, width) in enumerate(columns, start=1):
        col_letter = get_column_letter(idx)
        ws.column_dimensions[col_letter].width = width
        if choices:
            _add_validation(ws, choices, col_letter)

    # ── Congelar y filtro ──────────────────────────────────────────────────
    ws.freeze_panes = "A3"
    last_col = get_column_letter(len(columns))
    ws.auto_filter.ref = f"A2:{last_col}2"


# ─── Choices (valores exactos del models.py) ─────────────────────────────────

TIPO_SIM = [
    "DISCIPLINARIO", "ADMINISTRATIVO", "ASCENSO POSTUMO",
    "SOLICITUD_LETRA_D", "SOLICITUD_LICENCIA_MAXIMA",
    "SOLICITUD_RESTITUCION_ANTIGUEDAD",
    "SOLICITUD_DE_RESTITUCION_DE_DERECHOS_PROFESIONALES",
    "SOLICITUD_ASCENSO_AL_GRADO_INMEDIATO_SUPERIOR",
    "SOLICITUD_ART_114_(Invalidez Instructor)",
    "SOLICITUD_ART_117_(Fallecimiento)",
    "SOLICITUD_ART_118_(Invalidez Sldo)",
]
ESTADO_SIM   = ["PARA_AGENDA", "PROCESO_EN_EL_TPE", "EN_APELACION_TSP", "CONCLUIDO", "OBSERVADO"]
ESCALAFON_PM = ["GENERAL", "OFICIAL_SUPERIOR", "OFICIAL_SUBALTERNO", "SUBOFICIAL", "SARGENTO", "TROPA", "EMPLEADO_CIVIL"]
GRADO_PM = [
    "GENERAL_EJERCITO", "GENERAL_DIVISION", "GENERAL_BRIGADA",
    "CORONEL", "TCNEL", "MAYOR",
    "CAPITAN", "TENIENTE", "SUBTENIENTE",
    "SUBOFICIAL_MAESTRE", "SUBOFICIAL_MAYOR", "SUBOFICIAL_1RO",
    "SUBOFICIAL_2DO", "SUBOFICIAL_INICIAL",
    "SARGENTO_1RO", "SARGENTO_2DO", "SARGENTO_INICIAL",
    "CABO", "DRAGONEANTE", "SOLDADO",
    "PROF_V", "PROF_IV", "PROF_III", "PROF_II", "PROF_I",
    "TEC_V", "TEC_IV", "TEC_III", "TEC_II", "TEC_I",
    "ADM_V", "ADM_IV", "ADM_III", "ADM_II", "ADM_I",
    "APAD_V", "APAD_IV", "APAD_III", "APAD_II", "APAD_I",
]
ARMA_PM     = ["INFANTERIA", "CABALLERIA", "ARTILLERIA", "INGENIERIA",
               "COMUNICACIONES", "INTENDENCIA", "SANIDAD", "TOPOGRAFIA",
               "AVIACION", "MÚSICA"]
ESTADO_PM   = ["ACTIVO", "RETIRO OBLIGATORIO", "RESERVA_ACTIVA", "BAJA", "FALLECIDO"]
TIPO_RES    = [
    "ARCHIVO_OBRADOS", "ADMINISTRATIVO", "SANCIONES_DISCIPLINARIAS",
    "SANCION_ARRESTO", "SANCION_LETRA_B", "SANCION_RETIRO_OBLIGATORIO",
    "SANCION_BAJA", "SOLICITUD_LETRA_D", "SOLICITUD_LICENCIA_MAXIMA",
    "SOLICITUD_ASCENSO", "SOLICITUD_RESTITUCION_ANTIGUEDAD",
    "SOLICITUD_RESTITUCION_DE_DERECHOS_PROFESIONALES",
    "SOLICITUD_ART_114_(Invalidez Instructor)",
    "SOLICITUD_ART_117_(Fallecimiento)", "SOLICITUD_ART_118_(Invalidez Sldo)",
    "OTRO",
]
NOTIF_CHOICES = ["FIRMA", "EDICTO", "CEDULON"]
TIPO_AUTOTPE  = [
    "SOBRESEIDO", "NULIDAD_OBRADOS", "SANCION_ARRESTO", "SANCION_LETRA_B",
    "SANCION_RETIRO_OBLIGATORIO", "AUTO_CUMPLIMIENTO", "AUTO_EJECUTORIA",
    "AUTO_EXCUSA", "AUTO_RECHAZO_RECURSO",
]
TIPO_RAP = ["REVOCAR", "CONFIRMAR", "MODIFICAR",
            "ANULAR HASTA EL VICIO MAS ANTIGUO", "OTRO"]


# ─── MAIN ────────────────────────────────────────────────────────────────────

def generar_plantilla():
    wb = Workbook()

    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 0: INSTRUCCIONES
    # ──────────────────────────────────────────────────────────────────────────
    ws0 = wb.active
    ws0.title = "INSTRUCCIONES"

    instrucciones = [
        ("PLANTILLA DE CARGA MASIVA — HISTÓRICO SIM", "C00000"),
        ("", ""),
        ("LEYENDA DE COLORES EN ENCABEZADOS:", "1F3864"),
        ("  Rojo (C00000)  → Campo OBLIGATORIO (no puede quedar vacío)", "C00000"),
        ("  Azul (203864)  → Campo OPCIONAL (puede quedar vacío si no hay dato)", "203864"),
        ("  Marrón (833C00) → Clave FORÁNEA — debe coincidir con un valor en la hoja de referencia", "833C00"),
        ("", ""),
        ("ORDEN DE CARGA EN LA BASE DE DATOS:", "1F3864"),
        ("  1. Hoja 1_SIM       → Primero, los sumarios principales", ""),
        ("  2. Hoja 2_PM        → Personal Militar (puede existir ya en la BD)", ""),
        ("  3. Hoja 3_PM_SIM    → Relación militar ↔ sumario", ""),
        ("  4. Hoja 4_RES       → Primera Resolución del TPE", ""),
        ("  5. Hoja 5_RR        → Recurso de Reconsideración", ""),
        ("  6. Hoja 6_RAP       → Recurso de Apelación al TSP", ""),
        ("  7. Hoja 7_AUTOTPE   → Autos del Tribunal TPE", ""),
        ("  8. Hoja 8_RAEE      → Recurso de Aclaración, Explicación y Enmienda", ""),
        ("", ""),
        ("REGLAS GENERALES:", "1F3864"),
        ("  • Fechas en formato: AAAA-MM-DD  (ej: 2010-03-15)", ""),
        ("  • Horas en formato: HH:MM         (ej: 09:30)", ""),
        ("  • SIM_COD es el código único del sumario (ej: SIM-001/2005)", ""),
        ("  • PM_CI es la cédula de identidad del militar (clave foránea entre 2_PM y 3_PM_SIM)", ""),
        ("  • La fila 3 de cada hoja es un EJEMPLO — borrarla antes de la importación", ""),
        ("  • Campos con lista desplegable: usar EXACTAMENTE el valor de la lista", ""),
        ("  • Si un expediente no tiene RR, RAP o AUTOTPE, simplemente no se llena esa hoja", ""),
        ("", ""),
        ("CONSEJOS PARA DIGITALIZACIÓN DESDE PDF:", "1F3864"),
        ("  • Usar Claude Vision (claude.ai) para extraer texto de páginas escaneadas", ""),
        ("  • Procesar por lotes de 50 PDFs para revisar errores temprano", ""),
        ("  • Guardar el PDF original con el mismo nombre que SIM_COD para trazabilidad", ""),
        ("  • Campos que falten en el documento físico: dejar en BLANCO (no poner 'S/D' ni '-')", ""),
    ]

    ws0.column_dimensions["A"].width = 85
    for i, (texto, color) in enumerate(instrucciones, start=1):
        c = ws0.cell(row=i, column=1, value=texto)
        c.font = Font(
            bold=(color != ""),
            color=(color if color else "000000"),
            name="Calibri",
            size=10,
        )
        c.alignment = ALIGN_LEFT
        ws0.row_dimensions[i].height = 18


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 1: SIM
    # ──────────────────────────────────────────────────────────────────────────
    ws1 = wb.create_sheet("1_SIM")
    cols_sim = [
        # (encabezado, fill, choices, width)
        ("SIM_COD\n(Código único SIM, máx 10 car.)", FILL_REQUERIDO, None,        20),
        ("SIM_FECING\n(Fecha ingreso TPE\nAAAA-MM-DD)", FILL_OPCIONAL, None,    16),
        ("SIM_ESTADO\n(Estado del sumario)",         FILL_REQUERIDO, ESTADO_SIM, 20),
        ("SIM_TIPO\n(Tipo de sumario)",              FILL_REQUERIDO, TIPO_SIM,   30),
        ("SIM_OBJETO\n(Objeto completo del sumario)", FILL_REQUERIDO, None,      45),
        ("SIM_RESUM\n(Resumen breve, máx 200 car.)", FILL_REQUERIDO, None,       30),
        ("SIM_AUTOFINAL\n(Auto Final/Dictamen)",      FILL_OPCIONAL,  None,      35),
    ]
    ej_sim = [
        "S001-2005",
        "2005-03-15",
        "CONCLUIDO",
        "DISCIPLINARIO",
        "INVESTIGACION POR ABANDONO DE GUARDIA EN LA UNIDAD MILITAR N 4 DE INFANTERIA",
        "ABANDONO DE GUARDIA",
        "ARCHIVADO POR PRESCRIPCION",
    ]
    _build_sheet(ws1, cols_sim, ej_sim,
                 title="HOJA 1 — SUMARIO INFORMATIVO MILITAR (SIM)  |  Una fila por sumario")


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 2: PM — Personal Militar
    # ──────────────────────────────────────────────────────────────────────────
    ws2 = wb.create_sheet("2_PM")
    cols_pm = [
        ("PM_CI\n(Cédula Identidad, único)",      FILL_REQUERIDO, None,        16),
        ("PM_ESCALAFON\n(Escalafón)",             FILL_OPCIONAL,  ESCALAFON_PM, 20),
        ("PM_GRADO\n(Grado militar)",             FILL_OPCIONAL,  None,         22),
        ("PM_ARMA\n(Arma o especialidad)",        FILL_OPCIONAL,  ARMA_PM,      18),
        ("PM_ESPEC\n(Especialidad adicional)",    FILL_OPCIONAL,  None,         15),
        ("PM_NOMBRE\n(Nombre/s)",                 FILL_REQUERIDO, None,         20),
        ("PM_PATERNO\n(Apellido Paterno)",        FILL_REQUERIDO, None,         20),
        ("PM_MATERNO\n(Apellido Materno)",        FILL_OPCIONAL,  None,         20),
        ("PM_ESTADO\n(Estado del militar)",       FILL_OPCIONAL,  ESTADO_PM,    20),
        ("PM_PROMOCION\n(Fecha promoción\nAAAA-MM-DD)", FILL_OPCIONAL, None,    16),
    ]
    ej_pm = [
        "4521890",
        "OFICIAL_SUPERIOR",
        "CORONEL",
        "INFANTERIA",
        "",
        "JUAN CARLOS",
        "MAMANI",
        "QUISPE",
        "RETIRO OBLIGATORIO",
        "1998-12-01",
    ]
    _build_sheet(ws2, cols_pm, ej_pm,
                 title="HOJA 2 — PERSONAL MILITAR (PM)  |  Una fila por militar (no duplicar cédula)")

    # Nota: grado tiene muchos valores — agregar validación especial
    grado_choices_short = [
        "GENERAL_EJERCITO","GENERAL_DIVISION","GENERAL_BRIGADA",
        "CORONEL","TCNEL","MAYOR",
        "CAPITAN","TENIENTE","SUBTENIENTE",
        "SUBOFICIAL_MAESTRE","SUBOFICIAL_MAYOR","SUBOFICIAL_1RO",
        "SUBOFICIAL_2DO","SUBOFICIAL_INICIAL",
        "SARGENTO_1RO","SARGENTO_2DO","SARGENTO_INICIAL",
        "CABO","DRAGONEANTE","SOLDADO",
    ]
    _add_validation(ws2, grado_choices_short, "C")  # columna C = PM_GRADO (militares activos)


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 3: PM_SIM — Relación Militar ↔ Sumario
    # ──────────────────────────────────────────────────────────────────────────
    ws3 = wb.create_sheet("3_PM_SIM")
    cols_pm_sim = [
        ("SIM_COD\n(FK → hoja 1_SIM)",          FILL_FK,         None, 20),
        ("PM_CI\n(FK → hoja 2_PM  Cédula)",     FILL_FK,         None, 16),
        ("OBSERVACION\n(opcional — rol del militar en el sumario)", FILL_OPCIONAL, None, 35),
    ]
    ej_pm_sim = ["S001-2005", "4521890", "INVESTIGADO PRINCIPAL"]
    _build_sheet(ws3, cols_pm_sim, ej_pm_sim,
                 title="HOJA 3 — PM_SIM  |  Un militar puede aparecer en varios sumarios")


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 4: RES — Primera Resolución del TPE
    # ──────────────────────────────────────────────────────────────────────────
    ws4 = wb.create_sheet("4_RES")
    cols_res = [
        ("SIM_COD\n(FK → hoja 1_SIM)",                   FILL_FK,        None,         20),
        ("RES_NUM\n(Número de resolución)",               FILL_REQUERIDO, None,         16),
        ("RES_FEC\n(Fecha resolución\nAAAA-MM-DD)",       FILL_REQUERIDO, None,         14),
        ("RES_TIPO\n(Tipo de resolución)",                FILL_REQUERIDO, TIPO_RES,     28),
        ("RES_RESOL\n(Texto de la resolución)",          FILL_REQUERIDO, None,         45),
        ("RES_TIPO_NOTIF\n(Tipo notificación)",          FILL_OPCIONAL,  NOTIF_CHOICES, 16),
        ("RES_NOT\n(Notificado a / Dirección / Periódico)", FILL_OPCIONAL, None,        28),
        ("RES_FECNOT\n(Fecha notificación\nAAAA-MM-DD)", FILL_OPCIONAL,  None,         14),
        ("RES_HORNOT\n(Hora notificación\nHH:MM)",       FILL_OPCIONAL,  None,         12),
    ]
    ej_res = [
        "S001-2005",
        "RES-045/2006",
        "2006-08-10",
        "SANCIONES_DISCIPLINARIAS",
        "SE IMPONE SANCION DE ARRESTO DE 15 DIAS AL TCnel. MAMANI POR ABANDONO DE GUARDIA",
        "FIRMA",
        "TCnel. Juan Carlos Mamani Quispe",
        "2006-08-15",
        "09:30",
    ]
    _build_sheet(ws4, cols_res, ej_res,
                 title="HOJA 4 — PRIMERA RESOLUCIÓN (RES)  |  Un sumario puede tener máximo una RES")


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 5: RR — Recurso de Reconsideración
    # ──────────────────────────────────────────────────────────────────────────
    ws5 = wb.create_sheet("5_RR")
    cols_rr = [
        ("SIM_COD\n(FK → hoja 1_SIM)",                    FILL_FK,        None,          20),
        ("RES_NUM\n(FK → hoja 4_RES  N° resolución)",     FILL_FK,        None,          16),
        ("RR_FECPRESEN\n(Fecha presentación recurso\nAAAA-MM-DD)", FILL_OPCIONAL, None,  14),
        ("RR_NUM\n(Número RR)",                           FILL_OPCIONAL,  None,          14),
        ("RR_FEC\n(Fecha resolución RR\nAAAA-MM-DD)",     FILL_OPCIONAL,  None,          14),
        ("RR_RESOL\n(Texto resolución RR)",               FILL_OPCIONAL,  None,          45),
        ("RR_RESUM\n(Resumen, máx 200 car.)",             FILL_OPCIONAL,  None,          28),
        ("RR_TIPO_NOTIF\n(Tipo notificación)",            FILL_OPCIONAL,  NOTIF_CHOICES,  16),
        ("RR_NOT\n(Notificado a)",                        FILL_OPCIONAL,  None,          28),
        ("RR_FECNOT\n(Fecha notificación\nAAAA-MM-DD)",   FILL_OPCIONAL,  None,          14),
        ("RR_HORNOT\n(Hora notificación\nHH:MM)",         FILL_OPCIONAL,  None,          12),
    ]
    ej_rr = [
        "S001-2005",
        "RES-045/2006",
        "2006-08-25",
        "RR-012/2006",
        "2006-09-20",
        "SE CONFIRMA LA SANCION DE ARRESTO IMPUESTA POR LA PRIMERA RESOLUCION",
        "CONFIRMACION SANCION",
        "EDICTO",
        "El Diario — pág. 12",
        "2006-09-25",
        "10:00",
    ]
    _build_sheet(ws5, cols_rr, ej_rr,
                 title="HOJA 5 — RECURSO DE RECONSIDERACIÓN (RR)  |  Solo si el sumario tiene RR")


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 6: RAP — Recurso de Apelación al TSP
    # ──────────────────────────────────────────────────────────────────────────
    ws6 = wb.create_sheet("6_RAP")
    cols_rap = [
        ("SIM_COD\n(FK → hoja 1_SIM)",                    FILL_FK,        None,       20),
        ("RAP_FECPRESEN\n(Fecha presentación RAP\nAAAA-MM-DD)", FILL_OPCIONAL, None,  14),
        ("RAP_OFI\n(N° Oficio de Elevación)",             FILL_OPCIONAL,  None,       16),
        ("RAP_FECOFI\n(Fecha oficio elevación\nAAAA-MM-DD)", FILL_OPCIONAL, None,     14),
        ("RAP_NUM\n(N° Resolución TSP)",                   FILL_OPCIONAL,  None,      16),
        ("RAP_FEC\n(Fecha resolución TSP\nAAAA-MM-DD)",   FILL_OPCIONAL,  None,       14),
        ("RAP_TIPO\n(Tipo resolución TSP)",               FILL_OPCIONAL,  TIPO_RAP,   25),
        ("RAP_RESOL\n(Texto resolución TSP)",             FILL_OPCIONAL,  None,       45),
        ("RAP_TIPO_NOTIF\n(Tipo notificación)",           FILL_OPCIONAL,  NOTIF_CHOICES, 16),
        ("RAP_NOT\n(Notificado a)",                       FILL_OPCIONAL,  None,       28),
        ("RAP_FECNOT\n(Fecha notificación\nAAAA-MM-DD)", FILL_OPCIONAL,  None,        14),
        ("RAP_HORNOT\n(Hora notificación\nHH:MM)",       FILL_OPCIONAL,  None,        12),
    ]
    ej_rap = [
        "S001-2005",
        "2006-10-05",
        "OFI-231/2006",
        "2006-10-08",
        "RAP-089/2007",
        "2007-03-15",
        "CONFIRMAR",
        "EL TSP CONFIRMA LA SEGUNDA RESOLUCION EN TODOS SUS TERMINOS",
        "FIRMA",
        "TCnel. Juan Carlos Mamani Quispe",
        "2007-03-20",
        "08:45",
    ]
    _build_sheet(ws6, cols_rap, ej_rap,
                 title="HOJA 6 — RECURSO DE APELACIÓN TSP (RAP)  |  Solo si el sumario llegó al TSP")


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 7: AUTOTPE — Autos del Tribunal
    # ──────────────────────────────────────────────────────────────────────────
    ws7 = wb.create_sheet("7_AUTOTPE")
    cols_tpe = [
        ("SIM_COD\n(FK → hoja 1_SIM)",                   FILL_FK,        None,          20),
        ("TPE_NUM\n(Número de Auto)",                     FILL_OPCIONAL,  None,          16),
        ("TPE_FEC\n(Fecha del Auto\nAAAA-MM-DD)",        FILL_OPCIONAL,  None,           14),
        ("TPE_TIPO\n(Tipo de Auto)",                     FILL_OPCIONAL,  TIPO_AUTOTPE,   28),
        ("TPE_RESOL\n(Texto del Auto)",                  FILL_OPCIONAL,  None,           45),
        ("TPE_TIPO_NOTIF\n(Tipo notificación)",          FILL_OPCIONAL,  NOTIF_CHOICES,  16),
        ("TPE_NOT\n(Notificado a)",                      FILL_OPCIONAL,  None,           28),
        ("TPE_FECNOT\n(Fecha notificación\nAAAA-MM-DD)", FILL_OPCIONAL,  None,           14),
        ("TPE_HORNOT\n(Hora notificación\nHH:MM)",       FILL_OPCIONAL,  None,           12),
        ("TPE_MEMO_NUM\n(N° Memorándum)",                FILL_OPCIONAL,  None,           16),
        ("TPE_MEMO_FEC\n(Fecha memorándum\nAAAA-MM-DD)", FILL_OPCIONAL,  None,           14),
        ("TPE_MEMO_ENTREGA\n(Fecha entrega\nAAAA-MM-DD)", FILL_OPCIONAL, None,           14),
    ]
    ej_tpe = [
        "S001-2005",
        "ATPE-015/2007",
        "2007-04-10",
        "AUTO_EJECUTORIA",
        "SE DECLARA EJECUTORIADA LA RESOLUCION Y SE ORDENA SU CUMPLIMIENTO INMEDIATO",
        "FIRMA",
        "Unidad de Personal - Cmd. Ejército",
        "2007-04-12",
        "11:00",
        "MEMO-089/2007",
        "2007-04-12",
        "2007-04-15",
    ]
    _build_sheet(ws7, cols_tpe, ej_tpe,
                 title="HOJA 7 — AUTOS TPE  |  Un sumario puede tener varios Autos")


    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 8: RAEE — Recurso de Aclaración, Explicación y Enmienda
    # ──────────────────────────────────────────────────────────────────────────
    ws8 = wb.create_sheet("8_RAEE")
    cols_raee = [
        ("SIM_COD\n(FK → hoja 1_SIM)",                   FILL_FK,       None,          20),
        ("RAE_NUM\n(Número resolución RAEE)",             FILL_OPCIONAL, None,          16),
        ("RAE_FEC\n(Fecha resolución\nAAAA-MM-DD)",       FILL_OPCIONAL, None,          14),
        ("RAE_RESOL\n(Texto de la resolución)",          FILL_OPCIONAL, None,           45),
        ("RAE_RESUM\n(Resumen, máx 200 car.)",           FILL_OPCIONAL, None,           28),
        ("RAE_TIPO_NOTIF\n(Tipo notificación)",          FILL_OPCIONAL, NOTIF_CHOICES,  16),
        ("RAE_NOT\n(Notificado a)",                      FILL_OPCIONAL, None,           28),
        ("RAE_FECNOT\n(Fecha notificación\nAAAA-MM-DD)", FILL_OPCIONAL, None,           14),
        ("RAE_HORNOT\n(Hora notificación\nHH:MM)",       FILL_OPCIONAL, None,           12),
    ]
    ej_raee = [
        "S001-2005",
        "RAEE-003/2007",
        "2007-05-02",
        "SE ACLARA EL PUNTO 3 DE LA RESOLUCION TSP EN EL SENTIDO DE QUE EL PLAZO ES DE 30 DIAS",
        "ACLARACION PLAZO RESOLUCION TSP",
        "CEDULON",
        "TCnel. Juan Carlos Mamani Quispe — Domicilio conocido",
        "2007-05-06",
        "09:00",
    ]
    _build_sheet(ws8, cols_raee, ej_raee,
                 title="HOJA 8 — RAEE  |  Solo si el sumario tuvo recurso de aclaración")


    # ──────────────────────────────────────────────────────────────────────────
    # Guardar
    # ──────────────────────────────────────────────────────────────────────────
    nombre = "plantilla_historico_sim.xlsx"
    wb.save(nombre)
    print(f"\nPlantilla generada: {nombre}")
    print("  Hojas creadas:")
    for ws in wb.worksheets:
        print(f"    • {ws.title}")
    print("\nRecuerda: la fila 3 de cada hoja es un EJEMPLO — bórrala antes de importar.\n")


if __name__ == "__main__":
    generar_plantilla()

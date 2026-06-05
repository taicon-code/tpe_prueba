# tpe_app/views/buscador_views.py
import unicodedata
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Value
from django.db.models.functions import Replace, Collate
from django.core.exceptions import ValidationError

from ..decorators import rol_requerido, ROLES_OPERATIVOS, ROLES_REGISTRO_PM
from ..models import SIM, PM, AUTOTPE, ActuadoTSP, Resolucion, ApelacionTSP, DocumentoAdjunto, CustodiaSIM
from ..utils.upload_validators import validar_imagen, validar_pdf
from ..utils.audit import log_acceso


def _normalizar(texto):
    """Quita acentos y ñ para búsqueda flexible. 'alarcón' → 'ALARCON', 'siñani' → 'SINANI'."""
    nfkd = unicodedata.normalize('NFKD', texto)
    sin_acentos = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.upper()


def _format_date_safe(fecha, formato='%d/%m/%y'):
    """Formatea fecha de forma segura. En Windows, strftime con %y falla en fechas < 1900.
    Este método convierte manualmente sin usar strftime para %y."""
    if not fecha:
        return 'S/F'
    try:
        if formato == '%d/%m/%y':
            return f'{fecha.day:02d}/{fecha.month:02d}/{fecha.year % 100:02d}'
        return fecha.strftime(formato)
    except (ValueError, AttributeError):
        return 'S/F'


def _campo_sin_n(campo):
    """Reemplaza Ñ→N en el campo de BD para comparación. Los datos están en mayúsculas."""
    return Replace(campo, Value('Ñ'), Value('N'))


def _obtener_historial_completo(personal_id):
    """Obtiene el historial completo de un personal"""
    from ..models import Memorandum

    try:
        personal = PM.objects.get(id=personal_id)
    except PM.DoesNotExist:
        return None

    # Obtener todos los SIM donde participa este personal (orden cronológico)
    # Orden: 1) fecha_ingreso si existe, 2) año extraído del código (ej: DJE-259/19 → 19)
    # Esto maneja sumarios históricos sin fecha de ingreso
    from django.db.models import Case, When, Value, IntegerField
    from django.db.models.functions import Substr, Length, Cast

    sims = SIM.objects.filter(militares__id=personal_id).annotate(
        # Extraer año del código (últimos 2 caracteres: ej: "DJE-259/19" → "19" → 19)
        # Substr(campo, posición, longitud) - posición comienza en 1
        year_from_code=Cast(
            Substr('codigo', Length('codigo') - 1, 2),
            output_field=IntegerField()
        )
    ).order_by('year_from_code', 'codigo', 'version', 'fecha_ingreso').distinct()

    # Convertir a lista para preservar el orden
    sim_ids = [sim.id for sim in sims]

    resoluciones = Resolucion.objects.filter(sim__in=sim_ids, instancia='PRIMERA', pm=personal)
    segundas_resoluciones = Resolucion.objects.filter(sim__in=sim_ids, instancia='RECONSIDERACION', pm=personal)
    autos_tpe = AUTOTPE.objects.filter(sim__in=sim_ids, pm=personal)

    historial = {
        'personal': personal,
        'sumarios': sims,  # Mantiene el order_by('fecha_ingreso', 'version')
        'resoluciones': resoluciones,
        'segundas_resoluciones': segundas_resoluciones,
        'apelaciones_tsp': ApelacionTSP.objects.filter(sim__in=sim_ids, pm=personal),
        'actuados_tsp': ActuadoTSP.objects.filter(sim__in=sim_ids),
        'autos_tpe': autos_tpe,
        'memorandums': Memorandum.objects.filter(
            Q(resolucion__in=resoluciones) |
            Q(resolucion__in=segundas_resoluciones) |
            Q(autotpe__in=autos_tpe)
        ),
    }

    return historial


def _agrupar_actuados_por_sumario(historial, personal):
    """Agrupa los actuados de UNA persona por cada sumario, con paneles TPE/TSP
    separados — mismo formato que `militares_con_docs` de detalles_sim, pero
    invertido (un militar fijo, iterando por sumario). Permite renderizar el
    resultado de búsqueda como acordeones plegables y compactos."""
    sumarios_con_docs = []
    for sim in historial['sumarios']:
        res_primera = historial['resoluciones'].filter(sim=sim).order_by('fecha')
        rrs         = historial['segundas_resoluciones'].filter(sim=sim).order_by('fecha')
        autos       = historial['autos_tpe'].filter(sim=sim).order_by('fecha')
        raps        = historial['apelaciones_tsp'].filter(sim=sim).order_by('fecha_presentacion')

        tsp_raee    = ActuadoTSP.objects.filter(
            apelacion_tsp__in=raps, instancia='RAEE'
        ).order_by('fecha')
        tsp_nulidad = ActuadoTSP.objects.filter(
            apelacion_tsp__in=raps,
            instancia__in=['NULIDAD', 'NULIDAD_DEFECTOS_ABSOLUTOS']
        ).order_by('fecha')
        tsp_auto    = ActuadoTSP.objects.filter(
            apelacion_tsp__in=raps, instancia='AUTO_TSP'
        ).order_by('fecha')

        sumarios_con_docs.append({
            'sim':             sim,
            'resoluciones':    res_primera,
            'rrs':             rrs,
            'autos_tpe':       autos,
            'apelaciones_tsp': raps,
            'tsp_raee':        tsp_raee,
            'tsp_nulidad':     tsp_nulidad,
            'tsp_auto':        tsp_auto,
            'has_tsp':         raps.exists(),
        })
    return sumarios_con_docs


def _compilar_documentos_lotes(sim, historial):
    """Compila documentos coordinados para reportes por lote
    Retorna string formateado con tipo, numero, fecha y resolutiva"""
    documentos = []

    # Resoluciones
    for res in historial['resoluciones'].filter(sim=sim):
        fecha_str = _format_date_safe(res.fecha)
        resolutiva = (res.texto or 'N/A').upper() if res.texto else 'N/A'
        documentos.append(('RES', res.numero or 'S/N', fecha_str, resolutiva, None))

    # Segundas Resoluciones
    for rr in historial.get('segundas_resoluciones', Resolucion.objects.none()).filter(sim=sim):
        fecha_str = _format_date_safe(rr.fecha)
        resolutiva = (rr.texto or 'N/A').upper() if rr.texto else 'N/A'
        documentos.append(('RR', rr.numero or 'S/N', fecha_str, resolutiva, None))

    # Autos TPE
    for auto in historial['autos_tpe'].filter(sim=sim):
        fecha_str = _format_date_safe(auto.fecha)
        resolutiva = (auto.texto or (auto.get_tipo_display() if auto.tipo else 'N/A')).upper()
        memo = auto.memorandums.first()
        if memo:
            entrega = _format_date_safe(memo.fecha_entrega) if memo.fecha_entrega else 'PENDIENTE'
            memo_fecha = _format_date_safe(memo.fecha)
            memo_str = f"MEMO N° {memo.numero}  |  FECHA: {memo_fecha}  |  ENTREGA: {entrega}"
        else:
            memo_str = None
        documentos.append(('AUTO TPE', auto.numero or 'S/N', fecha_str, resolutiva, memo_str))


    # Ordenar por fecha
    return documentos


def _obtener_estado_actual(personal_id):
    """Obtiene el estado actual del personal con estadísticas simplificadas.
    Solo cuenta documentos emitidos por el TPE: RES, RR, AUTOTPE"""
    historial = _obtener_historial_completo(personal_id)
    if not historial:
        return None

    return {
        'total_sumarios': historial['sumarios'].count(),
        'total_resoluciones': (historial['resoluciones'].count() +
                               historial['segundas_resoluciones'].count()),
        'total_autos_tpe': historial['autos_tpe'].count(),
        'estado_actual': 'Historial disponible'
    }


@rol_requerido(*ROLES_OPERATIVOS)
def buscador_dashboard(request):
    """Dashboard para búsqueda unificada - búsqueda por CI, código SIM, nombre, apellidos"""

    query     = request.GET.get('q', '').strip()
    promocion = request.GET.get('promocion', '').strip()
    personal_seleccionado = None
    historial = None
    estado = None
    resultados_pm = []
    resultados_sim = []

    # Búsqueda por año de promoción (lista todos los militares de esa promoción)
    if promocion and promocion.isdigit():
        resultados_pm = list(
            PM.objects.filter(anio_promocion=int(promocion))
            .order_by('paterno', 'nombre')
        )

    if query:
        # Normalizamos el query: quitamos tildes y ñ → 'alarcón'→'ALARCON', 'siñani'→'SINANI'
        q_norm = _normalizar(query)

        # 1. Intentar búsqueda por CI exacto (es muy específico)
        resultados_pm = list(
            PM.objects.filter(ci__iexact=query).distinct()[:20]
        )

        # 2. Si no hay resultados por CI, verificar si es búsqueda por "apellido_paterno, apellido_materno"
        if not resultados_pm and ',' in query:
            partes = [p.strip() for p in query.split(',', 1)]
            if len(partes) == 2:
                ap, am = partes
                ap_norm = _normalizar(ap) if ap else ''
                am_norm = _normalizar(am) if am else ''

                filtro = PM.objects
                if ap_norm:
                    filtro = filtro.annotate(
                        pat_norm=Collate(_campo_sin_n('paterno'), 'utf8mb4_general_ci')
                    ).filter(pat_norm__icontains=ap_norm)
                if am_norm:
                    filtro = filtro.annotate(
                        mat_norm=Collate(_campo_sin_n('materno'), 'utf8mb4_general_ci')
                    ).filter(mat_norm__icontains=am_norm)

                resultados_pm = list(filtro.distinct()[:20])

        # 3. Si aún no hay resultados, buscar por nombre/apellido normalizando (búsqueda general)
        if not resultados_pm:
            resultados_pm = list(
                PM.objects.annotate(
                    pat_norm=Collate(_campo_sin_n('paterno'), 'utf8mb4_general_ci'),
                    nom_norm=Collate(_campo_sin_n('nombre'),  'utf8mb4_general_ci'),
                    mat_norm=Collate(_campo_sin_n('materno'), 'utf8mb4_general_ci'),
                ).filter(
                    Q(pat_norm__icontains=q_norm) |
                    Q(nom_norm__icontains=q_norm) |
                    Q(mat_norm__icontains=q_norm)
                ).distinct()[:20]
            )

        resultados_sim = list(
            SIM.objects.filter(
                Q(codigo__icontains=query) |
                Q(resumen__icontains=query) |
                Q(objeto__icontains=query)
            ).prefetch_related('abogados', 'militares').distinct()[:20]
        )

        # Si hay exactamente 1 PM, mostrar su historial completo
        if len(resultados_pm) == 1:
            personal_seleccionado = resultados_pm[0]
            historial = _obtener_historial_completo(personal_seleccionado.id)
            estado = _obtener_estado_actual(personal_seleccionado.id)
            log_acceso(request, 'VIEW_HISTORIAL', objeto_tipo='PM',
                       objeto_id=personal_seleccionado.id,
                       detalle=f'{personal_seleccionado.paterno} {personal_seleccionado.nombre}')

        log_acceso(request, 'SEARCH', detalle=query[:200])

    # Si hay búsqueda por promoción y exactamente 1 resultado, también mostrar historial
    if promocion and promocion.isdigit() and len(resultados_pm) == 1:
        personal_seleccionado = resultados_pm[0]
        historial = _obtener_historial_completo(personal_seleccionado.id)
        estado = _obtener_estado_actual(personal_seleccionado.id)

    # Agrupar actuados por sumario para mostrar acordeones plegables y compactos
    sumarios_con_docs = []
    if personal_seleccionado and historial:
        sumarios_con_docs = _agrupar_actuados_por_sumario(historial, personal_seleccionado)

    context = {
        'query': query,
        'promocion': promocion,
        'resultados_pm': resultados_pm,
        'resultados_sim': resultados_sim,
        'total_pm': len(resultados_pm),
        'total_sim': len(resultados_sim),
        'personal_seleccionado': personal_seleccionado,
        'historial': historial,
        'estado': estado,
        'sumarios_con_docs': sumarios_con_docs,
    }
    return render(request, 'tpe_app/buscador/dashboard_buscador.html', context)


@rol_requerido(*ROLES_OPERATIVOS)
def detalles_sim(request, sim_id):
    """Vista detallada de un SIM: militares, resoluciones, autos, custodia (solo Admin2), etc."""

    sim = get_object_or_404(SIM, id=sim_id)
    log_acceso(request, 'VIEW_SIM', objeto_tipo='SIM', objeto_id=sim.id, detalle=sim.codigo)

    # Obtener militares del SIM ordenados por jerarquía militar
    _orden_grado = {g: i for i, (g, _) in enumerate(PM.GRADO_CHOICES)}
    militares = sorted(
        sim.militares.all(),
        key=lambda m: _orden_grado.get(m.grado, 999)
    )

    # Obtener todos los actuados del SIM
    from ..models import Memorandum

    resoluciones    = Resolucion.objects.filter(sim=sim).select_related('abogado', 'pm')
    autos_tpe       = AUTOTPE.objects.filter(sim=sim).select_related('abogado', 'pm')
    apelaciones_tsp = ApelacionTSP.objects.filter(sim=sim).select_related('abogado', 'pm')
    # ActuadoTSP huérfanos (sin RAP de origen) — sección global al final de la página
    actuados_tsp = ActuadoTSP.objects.filter(sim=sim, apelacion_tsp=None).order_by('fecha')

    # Agrupar actuados por militar con paneles TPE y TSP separados
    militares_con_docs = []
    for pm_obj in militares:
        res_primera  = resoluciones.filter(pm=pm_obj, instancia='PRIMERA').order_by('fecha')
        rrs_del_pm   = resoluciones.filter(pm=pm_obj, instancia='RECONSIDERACION').order_by('fecha')
        autos_del_pm = autos_tpe.filter(pm=pm_obj).order_by('fecha')
        raps_del_pm  = apelaciones_tsp.filter(pm=pm_obj).order_by('fecha_presentacion')

        memos_del_pm = (
            Memorandum.objects.filter(resolucion__in=res_primera)
            | Memorandum.objects.filter(resolucion__in=rrs_del_pm)
            | Memorandum.objects.filter(autotpe__in=autos_del_pm)
        )

        # Panel TSP: actuados agrupados por sección (filtrados por RAPs de este militar)
        tsp_raee    = ActuadoTSP.objects.filter(
            apelacion_tsp__in=raps_del_pm, instancia='RAEE'
        ).order_by('fecha')
        tsp_nulidad = ActuadoTSP.objects.filter(
            apelacion_tsp__in=raps_del_pm,
            instancia__in=['NULIDAD', 'NULIDAD_DEFECTOS_ABSOLUTOS']
        ).order_by('fecha')
        tsp_auto    = ActuadoTSP.objects.filter(
            apelacion_tsp__in=raps_del_pm, instancia='AUTO_TSP'
        ).order_by('fecha')

        militares_con_docs.append({
            'pm':              pm_obj,
            'resoluciones':    res_primera,
            'rrs':             rrs_del_pm,
            'autos_tpe':       autos_del_pm,
            'memorandums':     memos_del_pm.order_by('fecha'),
            'apelaciones_tsp': raps_del_pm,
            'tsp_raee':        tsp_raee,
            'tsp_nulidad':     tsp_nulidad,
            'tsp_auto':        tsp_auto,
            'has_tsp':         raps_del_pm.exists(),
        })

    # Obtener historial de custodia (trazabilidad) - SOLO para Admin2
    custodia_historial = None
    custodia_actual = None
    es_admin2 = hasattr(request.user, 'perfilusuario') and request.user.perfilusuario.rol == 'ADMIN2_ARCHIVO'

    if es_admin2:
        custodia_historial = CustodiaSIM.objects.filter(sim=sim).select_related('abogado').order_by('fecha_recepcion')
        custodia_actual = CustodiaSIM.objects.filter(sim=sim, estado='RECIBIDA_CONFORME').select_related('abogado').first()

    context = {
        'sim': sim,
        'militares': militares,
        'militares_con_docs': militares_con_docs,
        'actuados_tsp': actuados_tsp,
        'custodia_historial': custodia_historial,
        'custodia_actual': custodia_actual,
        'es_admin2': es_admin2,
    }
    return render(request, 'tpe_app/buscador/detalles_sim.html', context)


MAX_LINEAS_BUSQUEDA_LOTES = 100


@rol_requerido(*ROLES_OPERATIVOS)
def busqueda_por_lotes(request):
    """Vista para búsqueda y reporte por lotes de múltiples militares por AP + AM"""
    militares_encontrados = []

    if request.method == 'POST':
        lista_apellidos = request.POST.get('lista_apellidos', '').strip()

        if lista_apellidos:
            # Procesar cada línea como "APELLIDO_PATERNO, APELLIDO_MATERNO"
            lineas = [l.strip() for l in lista_apellidos.split('\n') if l.strip()]

            # Tope defensivo: cada línea dispara una query a PM y N queries de historial.
            # 100 líneas ya es muy generoso para uso humano; más sugiere abuso o error.
            if len(lineas) > MAX_LINEAS_BUSQUEDA_LOTES:
                messages.error(
                    request,
                    f'❌ Máximo {MAX_LINEAS_BUSQUEDA_LOTES} apellidos por búsqueda. '
                    f'Se recibieron {len(lineas)}. Divida la búsqueda en lotes más pequeños.'
                )
                return render(request, 'tpe_app/buscador/busqueda_lotes.html', {
                    'militares_encontrados': [],
                })

            for linea in lineas:
                partes = [p.strip() for p in linea.split(',')]
                if len(partes) >= 2:
                    ap = partes[0].upper()
                    am = partes[1].upper()
                    nb = partes[2].upper() if len(partes) >= 3 else None

                    filtro = PM.objects.filter(materno__iexact=am)
                    if ap:
                        filtro = filtro.filter(paterno__iexact=ap)
                    else:
                        filtro = filtro.filter(Q(paterno='') | Q(paterno__isnull=True))
                    if nb:
                        filtro = filtro.filter(nombre__icontains=nb)

                    for pm in filtro:
                        historial = _obtener_historial_completo(pm.id)
                        if historial:
                            militares_encontrados.append({
                                'personal': pm,
                                'historial': historial,
                            })

    context = {
        'militares_encontrados': militares_encontrados,
    }
    return render(request, 'tpe_app/buscador/busqueda_lotes.html', context)


@rol_requerido(*ROLES_OPERATIVOS)
def export_batch_pdf(request):
    """Genera PDF con tabla compacta de múltiples militares"""
    log_acceso(request, 'EXPORT_BATCH', detalle='PDF lote')
    from django.http import HttpResponse
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from datetime import datetime

    # Registrar fuente Arial desde Windows
    try:
        pdfmetrics.getFont('Arial-Bold')
    except KeyError:
        try:
            pdfmetrics.registerFont(TTFont('Arial',      'C:/Windows/Fonts/arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        except Exception:
            # Si las fuentes no existen, usar Helvetica por defecto
            pass

    lista_apellidos = request.POST.get('lista_apellidos', '').strip()

    if not lista_apellidos:
        return HttpResponse("No se proporcionó lista de militares", status=400)

    militares = []
    lineas = [l.strip() for l in lista_apellidos.split('\n') if l.strip()]

    for linea in lineas:
        partes = [p.strip() for p in linea.split(',')]
        if len(partes) >= 2:
            ap = partes[0].upper()
            am = partes[1].upper()
            nb = partes[2].upper() if len(partes) >= 3 else None

            filtro = PM.objects.filter(materno__iexact=am)
            if ap:
                filtro = filtro.filter(paterno__iexact=ap)
            else:
                filtro = filtro.filter(Q(paterno='') | Q(paterno__isnull=True))
            if nb:
                filtro = filtro.filter(nombre__icontains=nb)

            for pm in filtro:
                historial = _obtener_historial_completo(pm.id)
                if historial:
                    militares.append({
                        'personal': pm,
                        'historial': historial,
                    })

    if not militares:
        return HttpResponse("No se encontraron militares con los datos proporcionados", status=404)

    buffer = BytesIO()
    page_w, _ = letter
    margin = 0.5 * inch

    def _estilo(nombre, fuente='Helvetica', tamaño=9, alineacion=TA_LEFT,
                negrita=False, color=colors.black, espacio_antes=0, espacio_despues=2,
                interlinea=11, sangria=0):
        fn = (fuente + '-Bold') if negrita else fuente
        return ParagraphStyle(nombre, fontName=fn, fontSize=tamaño,
                              alignment=alineacion, textColor=color,
                              spaceBefore=espacio_antes, spaceAfter=espacio_despues,
                              leading=interlinea, leftIndent=sangria)

    s_inst1   = _estilo('inst1',  fuente='Arial', tamaño=10, alineacion=TA_LEFT, negrita=True, espacio_despues=1, interlinea=9)
    s_inst2   = _estilo('inst2',  fuente='Arial', tamaño=10, alineacion=TA_LEFT, negrita=True, espacio_despues=1, interlinea=9, sangria=15)
    s_pais    = _estilo('pais',   fuente='Arial', tamaño=10, alineacion=TA_LEFT, negrita=True, espacio_despues=6, interlinea=9, sangria=70)
    s_seccion = _estilo('secc',   fuente='Arial', tamaño=14, alineacion=TA_CENTER, negrita=True, espacio_antes=6, espacio_despues=4, interlinea=17)
    s_th = _estilo('th', tamaño=7, alineacion=TA_CENTER, negrita=True, color=colors.black)
    s_td = _estilo('td', tamaño=7, interlinea=9)
    s_td_c = _estilo('tdc', tamaño=7, alineacion=TA_CENTER, interlinea=9)

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=margin, rightMargin=margin,
        topMargin=0.55 * inch, bottomMargin=0.75 * inch,
    )
    usable_w = page_w - 2 * margin
    story = []

    # ── ENCABEZADO INSTITUCIONAL ─────────────────────────────────────────────
    story.append(Paragraph("COMANDO GENERAL DEL EJÉRCITO", s_inst1))
    story.append(Paragraph("DEPARTAMENTO I - PERSONAL", s_inst2))
    story.append(Paragraph("<u>BOLIVIA</u>", s_pais))

    # ── REPORTE POR LOTES ─────────────────────────────────────────────────
    story.append(Paragraph("<u>ANTECEDENTES DISCIPLINARIOS TRATADOS POR EL TRIBUNAL DE PERSONAL DEL EJÉRCITO</u>", s_seccion))
    story.append(Spacer(1, 6))

    # Pie de página
    grado_usuario = ""
    espec_usuario = ""
    nombre_completo = request.user.get_full_name() or request.user.username
    if request.user.is_authenticated:
        try:
            from tpe_app.models import PerfilUsuario
            perfil = PerfilUsuario.objects.get(user=request.user)
            pm_pie = perfil.pm if perfil.pm else (perfil.vocal.pm if perfil.vocal and perfil.vocal.pm else None)
            if pm_pie:
                grado_usuario  = pm_pie.get_grado_display() or ""
                espec_usuario  = pm_pie.get_arma_display() or ""
                nombre_completo = f"{pm_pie.nombre or ''} {pm_pie.paterno or ''} {pm_pie.materno or ''}".strip()
        except Exception:
            pass

    partes_pie = [p for p in [grado_usuario, espec_usuario, nombre_completo.upper()] if p]
    texto_impreso = "  ".join(partes_pie)

    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    hora_hoy  = datetime.now().strftime("%H:%M")

    def _pie_pagina(canv, doc):
        canv.saveState()
        canv.setStrokeColor(colors.lightgrey)
        canv.setLineWidth(0.5)
        canv.line(margin, 0.52 * inch, page_w - margin, 0.52 * inch)
        canv.setFont('Helvetica', 6.5)
        canv.setFillColor(colors.grey)
        texto_pie = (f"Impreso por: {texto_impreso}   |   "
                     f"{fecha_hoy}  {hora_hoy}   |   Pág. {doc.page}")
        canv.drawCentredString(page_w / 2, 0.33 * inch, texto_pie)
        canv.restoreState()

    # Construir tabla con todos los militares
    # Ancho distribuido: GRADO Y NOMBRE=28% | SIM=8% | OBJETO=29% | ACTUADOS=25% | ESTADO=10%
    col_widths = [usable_w * p for p in (0.28, 0.08, 0.29, 0.25, 0.10)]

    filas = [[
        Paragraph('GRADO Y NOMBRE COMPLETO', s_th),
        Paragraph('SIM', s_th),
        Paragraph('OBJETO', s_th),
        Paragraph('ACTUADOS', s_th),
        Paragraph('ESTADO', s_th),
    ]]

    for mil in militares:
        pm = mil['personal']
        hist = mil['historial']

        for sim in hist['sumarios']:
            # Obtener actuados coordinados para este SIM
            documentos = _compilar_documentos_lotes(sim, hist)
            actuados_list = []
            contador = 1
            numeros_circulos = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']

            # Mapeo de tipos de documento para el PDF de lotes
            tipo_display = {
                'RES': 'RES. TPE. N.º',
                'RR': 'RR. TPE. N.º',
                'AUTO TPE': 'AUTO TPE. N.º',
            }

            for tipo, numero, fecha, resolutiva, memo in documentos:
                num_circulo = numeros_circulos[min(contador - 1, 9)]
                tipo_label = tipo_display.get(tipo, tipo)
                linea = f"{num_circulo} {tipo_label} {numero} ({fecha})<br/>   {resolutiva}"
                if memo:
                    linea += f"<br/>   <i>- {memo}</i>"
                actuados_list.append(linea + "<br/><br/>")
                contador += 1

            # Unir todo con HTML y remover último <br/><br/>
            actuados_str = ''.join(actuados_list) if actuados_list else 'PENDIENTE'
            if actuados_str.endswith('<br/><br/>'):
                actuados_str = actuados_str[:-10]  # Remover último <br/><br/>

            objeto_completo = (sim.objeto or 'N/A').upper()

            codigo_sim = sim.codigo or 'N/A'
            if sim.version and sim.version > 1:
                codigo_sim = f"{codigo_sim}<br/><b>v{sim.version}</b>"

            partes_nombre = [
                pm.get_grado_display() or '',
                pm.especialidad or '',
                pm.nombre or '',
                pm.paterno or '',
                pm.materno or '',
            ]
            grado_nombre = ' '.join(p.upper() for p in partes_nombre if p).strip() or 'N/A'

            filas.append([
                Paragraph(grado_nombre, s_td),
                Paragraph(codigo_sim, s_td_c),
                Paragraph(objeto_completo, s_td),
                Paragraph(actuados_str, s_td),
                Paragraph((sim.get_estado_display() or 'N/A').upper(), s_td_c),
            ])

    tabla = Table(filas, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ]))

    story.append(tabla)

    doc.build(story, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    buffer.seek(0)

    fecha_export = datetime.now().strftime("%d-%m-%Y")
    filename = f"ANTECEDENTES_LOTE_{fecha_export}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@rol_requerido(*ROLES_OPERATIVOS)
def export_batch_excel(request):
    """Genera Excel con tabla de múltiples militares"""
    log_acceso(request, 'EXPORT_BATCH', detalle='Excel lote')
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    from django.http import HttpResponse
    from datetime import datetime

    lista_apellidos = request.POST.get('lista_apellidos', '').strip()

    if not lista_apellidos:
        return HttpResponse("No se proporcionó lista de militares", status=400)

    militares = []
    lineas = [l.strip() for l in lista_apellidos.split('\n') if l.strip()]

    for linea in lineas:
        partes = [p.strip() for p in linea.split(',')]
        if len(partes) >= 2:
            ap = partes[0].upper()
            am = partes[1].upper()
            nb = partes[2].upper() if len(partes) >= 3 else None

            filtro = PM.objects.filter(materno__iexact=am)
            if ap:
                filtro = filtro.filter(paterno__iexact=ap)
            else:
                filtro = filtro.filter(Q(paterno='') | Q(paterno__isnull=True))
            if nb:
                filtro = filtro.filter(nombre__icontains=nb)

            for pm in filtro:
                historial = _obtener_historial_completo(pm.id)
                if historial:
                    militares.append({
                        'personal': pm,
                        'historial': historial,
                    })

    if not militares:
        return HttpResponse("No se encontraron militares con los datos proporcionados", status=404)

    wb = Workbook()
    ws = wb.active
    ws.title = "ANTECEDENTES"

    # Encabezados
    headers = ['GRADO', 'NOMBRES', 'APELLIDO PATERNO', 'APELLIDO MATERNO', 'SIM', 'OBJETO', 'ACTUADOS', 'ESTADO']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill(start_color="185FA5", end_color="185FA5", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_idx = 2

    for mil in militares:
        pm = mil['personal']
        hist = mil['historial']

        for sim in hist['sumarios']:
            # Obtener actuados coordinados para este SIM
            documentos = _compilar_documentos_lotes(sim, hist)
            actuados_list = []
            contador = 1
            numeros_circulos = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']

            # Mapeo de tipos de documento para los reportes de lotes
            tipo_display = {
                'RES': 'RES. TPE. N.º',
                'RR': 'RR. TPE. N.º',
                'AUTO TPE': 'AUTO TPE. N.º',
            }

            for tipo, numero, fecha, resolutiva, memo in documentos:
                num_circulo = numeros_circulos[min(contador - 1, 9)]
                tipo_label = tipo_display.get(tipo, tipo)
                linea = f"{num_circulo} {tipo_label} {numero} ({fecha})\n   {resolutiva}"
                if memo:
                    linea += f"\n   └─ {memo}"
                actuados_list.append(linea + "\n")
                contador += 1

            # Unir todo y remover último salto de línea
            actuados_str = ''.join(actuados_list) if actuados_list else 'PENDIENTE'
            actuados_str = actuados_str.rstrip('\n')

            ws.cell(row=row_idx, column=1, value=(pm.get_grado_display() or 'N/A').upper())
            ws.cell(row=row_idx, column=2, value=(pm.nombre or 'N/A').upper())
            ws.cell(row=row_idx, column=3, value=(pm.paterno or 'N/A').upper())
            ws.cell(row=row_idx, column=4, value=(pm.materno or 'N/A').upper())
            codigo_excel = sim.codigo or 'N/A'
            if sim.version and sim.version > 1:
                codigo_excel = f"{codigo_excel} (v{sim.version})"
            ws.cell(row=row_idx, column=5, value=codigo_excel)
            ws.cell(row=row_idx, column=6, value=(sim.objeto or 'N/A').upper())
            ws.cell(row=row_idx, column=7, value=actuados_str)
            ws.cell(row=row_idx, column=8, value=(sim.get_estado_display() or 'N/A').upper())

            row_idx += 1

    # Ajustar anchos
    ws.column_dimensions['A'].width = 10
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 28
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 12

    fecha_export = datetime.now().strftime("%Y-%m-%d")
    excel_filename = f"ANTECEDENTES_LOTE_{fecha_export}.xlsx"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{excel_filename}"'
    return response


@rol_requerido(*ROLES_REGISTRO_PM)
def upload_foto_pm(request, pm_id):
    """Subir o reemplazar la foto de un Personal Militar"""
    pm = get_object_or_404(PM, pk=pm_id)

    if request.method == 'POST':
        foto = request.FILES.get('foto')
        if not foto:
            messages.error(request, '❌ No se seleccionó ningún archivo')
        else:
            try:
                validar_imagen(foto)
            except ValidationError as e:
                messages.error(request, f'❌ {"; ".join(e.messages)}')
            else:
                if pm.foto:
                    pm.foto.delete(save=False)
                pm.foto = foto
                pm.save(update_fields=['foto'])
                messages.success(request, f'✅ Foto actualizada para {pm.nombre} {pm.paterno}')

    next_url = request.POST.get('next', '').strip()
    if next_url:
        return redirect(next_url)
    referer = request.META.get('HTTP_REFERER', '')
    if 'buscador' in referer or 'q=' in referer:
        return redirect(referer)
    return redirect('buscador_dashboard')


@rol_requerido('ADMIN2_ARCHIVO')
def export_custodia_pdf(request, sim_id):
    """Descargar PDF del historial de custodia de un SIM (Solo Admin2)"""
    log_acceso(request, 'EXPORT_PDF', objeto_tipo='SIM', objeto_id=sim_id, detalle='custodia')
    from django.http import HttpResponse
    from django.utils import timezone as tz
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    # Registrar fuentes TrueType para soporte completo de acentos y ñ
    _fonts_dir = r'C:\Windows\Fonts'
    _arial      = os.path.join(_fonts_dir, 'arial.ttf')
    _arial_bold = os.path.join(_fonts_dir, 'arialbd.ttf')
    if os.path.exists(_arial):
        pdfmetrics.registerFont(TTFont('Arial', _arial))
        pdfmetrics.registerFont(TTFont('Arial-Bold', _arial_bold))
        FONT_NORMAL = 'Arial'
        FONT_BOLD   = 'Arial-Bold'
    else:
        # Fallback si no está Arial (Linux/Mac en producción)
        FONT_NORMAL = 'Helvetica'
        FONT_BOLD   = 'Helvetica-Bold'

    from reportlab.lib.pagesizes import landscape

    sim = get_object_or_404(SIM, id=sim_id)
    custodia_historial = list(
        CustodiaSIM.objects.filter(sim=sim)
        .select_related('abogado', 'abogado_destino', 'usuario')
        .order_by('fecha_recepcion')
    )

    militares = sim.militares.all()

    # PDF en landscape carta (usable ≈ 25.4 cm ancho)
    response = HttpResponse(content_type='application/pdf')
    now_local = tz.localtime(tz.now())
    response['Content-Disposition'] = f'attachment; filename="custodia_{sim.codigo}_{now_local.strftime("%d%m%Y")}.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=landscape(letter),
        topMargin=0.45*inch, bottomMargin=0.45*inch,
        leftMargin=0.5*inch, rightMargin=0.5*inch,
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontName=FONT_BOLD, fontSize=13,
        textColor=colors.HexColor('#185FA5'),
        spaceAfter=8, alignment=1,
    )
    story.append(Paragraph(f'Historial de Custodia — {sim.codigo}', title_style))
    story.append(Spacer(1, 0.1*inch))

    # ── Bloque info del SIM ──────────────────────────────────────────────────
    cell_label = ParagraphStyle('Label', parent=styles['Normal'],
                                fontName=FONT_BOLD, fontSize=8, leading=10)
    cell_val   = ParagraphStyle('Val',   parent=styles['Normal'],
                                fontName=FONT_NORMAL, fontSize=8, leading=10)

    nombres_militares = ', '.join(
        f"{pm.grado} {pm.paterno} {pm.materno}".strip()
        for pm in militares
    ) or '-'

    info_data = [
        [Paragraph('Codigo SIM', cell_label),  Paragraph(sim.codigo or '-', cell_val),
         Paragraph('Tipo', cell_label),         Paragraph(sim.get_tipo_display() or '-', cell_val)],
        [Paragraph('Estado', cell_label),       Paragraph(sim.get_estado_display() or '-', cell_val),
         Paragraph('Fase', cell_label),         Paragraph(sim.get_fase_display() or '-', cell_val)],
        [Paragraph('Ingreso', cell_label),      Paragraph(sim.fecha_ingreso.strftime('%d/%m/%Y') if sim.fecha_ingreso else '-', cell_val),
         Paragraph('Militar(es)', cell_label),  Paragraph(nombres_militares, cell_val)],
        [Paragraph('Objeto', cell_label),       Paragraph(sim.objeto or '-', cell_val), '', ''],
    ]
    # Anchos: label1 | val1 | label2 | val2  (total ≈ 25.4 cm)
    info_table = Table(info_data, colWidths=[2.8*cm, 8.5*cm, 2.8*cm, 11.3*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#E8F4F8')),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('BACKGROUND', (3, 0), (3, -1), colors.white),
        ('SPAN', (1, 3), (3, 3)),
        ('ALIGN',  (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.18*inch))

    # ── Tabla de movimientos ─────────────────────────────────────────────────
    heading_style = ParagraphStyle(
        'SectionHead', parent=styles['Heading2'],
        fontName=FONT_BOLD, fontSize=10,
        textColor=colors.HexColor('#185FA5'), spaceAfter=5,
    )
    story.append(Paragraph('Movimientos de Custodia', heading_style))

    cell_s = ParagraphStyle('Cell', parent=styles['Normal'],
                            fontName=FONT_NORMAL, fontSize=7.5, leading=9.5, wordWrap='CJK')
    cell_b = ParagraphStyle('CellB', parent=styles['Normal'],
                            fontName=FONT_BOLD,   fontSize=7.5, leading=9.5)

    def _fmt_persona(custodia):
        """Devuelve nombre legible del abogado/destino según la custodia."""
        pm = custodia.abogado_destino or custodia.abogado
        if pm:
            return f"{pm.grado} {pm.paterno} {pm.materno}".strip()
        nombre = custodia.nombre_abogado_destino or custodia.nombre_abogado
        return nombre or '-'

    def _fmt_destino(custodia):
        """Para custodias ARCHIVO: devuelve destino final + oficio + fecha oficio."""
        if custodia.tipo_custodio != 'ARCHIVO':
            return '-'
        partes = []
        if custodia.destino_final:
            partes.append(custodia.get_destino_final_display() or custodia.destino_final)
        if custodia.nro_oficio_archivo:
            partes.append(f"Of. {custodia.nro_oficio_archivo}")
        if custodia.fecha_oficio_archivo:
            partes.append(custodia.fecha_oficio_archivo.strftime('%d/%m/%Y'))
        return '\n'.join(partes) if partes else '-'

    MOTIVO_DISPLAY = {
        'AGENDA':               'Agenda',
        'REVISION':             'Revision',
        'NOTIFICACION':         'Notificacion',
        'APELACION_TSP':        'Apelacion TSP',
        'EJECUTORIA':           'Ejecutoria',
        'RESPUESTA_MEMORIAL':   'Resp. Memorial',
        'ARCHIVO':              'Archivo Final',
    }

    # Columnas (landscape carta, usable ≈ 25.4 cm):
    # N° | Fecha Recep. | Custodio | Persona | Motivo | Estado | Fecha Entrega | Destino/Oficio | Observacion
    col_widths = [0.55*cm, 2.1*cm, 3.6*cm, 4.0*cm, 2.3*cm, 2.8*cm, 2.1*cm, 3.8*cm, 4.05*cm]

    if custodia_historial:
        headers = [
            Paragraph('#',              cell_b),
            Paragraph('Fecha Recep.',   cell_b),
            Paragraph('Custodio',       cell_b),
            Paragraph('Abogado/Persona',cell_b),
            Paragraph('Motivo',         cell_b),
            Paragraph('Estado',         cell_b),
            Paragraph('Fecha Entrega',  cell_b),
            Paragraph('Destino/Oficio', cell_b),
            Paragraph('Observacion',    cell_b),
        ]
        tabla_data = [headers]

        for idx, c in enumerate(custodia_historial, start=1):
            motivo_txt  = MOTIVO_DISPLAY.get(c.motivo, c.motivo or '-')
            estado_txt  = c.get_estado_display()
            fecha_recep = tz.localtime(c.fecha_recepcion).strftime('%d/%m/%Y\n%H:%M')
            fecha_entr  = (tz.localtime(c.fecha_entrega).strftime('%d/%m/%Y\n%H:%M')
                           if c.fecha_entrega else 'Activa')
            destino_txt = _fmt_destino(c)
            persona_txt = _fmt_persona(c)
            obs_txt     = c.observacion or '-'

            tabla_data.append([
                Paragraph(str(idx),        cell_s),
                Paragraph(fecha_recep,     cell_s),
                Paragraph(c.get_tipo_custodio_display(), cell_s),
                Paragraph(persona_txt,     cell_s),
                Paragraph(motivo_txt,      cell_s),
                Paragraph(estado_txt,      cell_s),
                Paragraph(fecha_entr,      cell_s),
                Paragraph(destino_txt,     cell_s),
                Paragraph(obs_txt,         cell_s),
            ])

        tabla = Table(tabla_data, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#185FA5')),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
            ('VALIGN',        (0, 0), (-1, 0),  'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, 0),  6),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
            ('LINEBELOW',     (0, 0), (-1, 0),  1.2, colors.HexColor('#0d3a7a')),
            ('ALIGN',  (0, 1), (0, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('GRID',   (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F6FF')]),
            ('LEFTPADDING',  (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING',   (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING',(0, 1), (-1, -1), 3),
        ]))
        story.append(tabla)
    else:
        story.append(Paragraph('<i>No hay movimientos de custodia registrados.</i>', styles['Normal']))

    # ── Pie de página ────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2*inch))
    pie_style = ParagraphStyle('Footer', parent=styles['Normal'],
                               fontName=FONT_NORMAL, fontSize=7,
                               textColor=colors.HexColor('#999999'), alignment=0)
    story.append(Paragraph(f'Generado: {now_local.strftime("%d/%m/%Y %H:%M:%S")}', pie_style))

    doc.build(story)
    return response

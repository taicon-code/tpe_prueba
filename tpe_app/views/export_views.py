# ============================================================
#  VISTAS DE EXPORTACIÓN - PDF (ZIP) y EXCEL
#  Archivo: tpe_app/views/export_views.py
# ============================================================

from io import BytesIO
from datetime import datetime, date
from zipfile import ZipFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from django.contrib.auth.decorators import login_required
from tpe_app.models import PM, SIM, AUTOTPE, AUTOTSP, Resolucion, RecursoTSP, PerfilUsuario


def _format_date(date_obj):
    """Formatea una fecha como DD/MM/YYYY"""
    if not date_obj:
        return "N/A"
    return date_obj.strftime("%d/%m/%Y")


def _sanitize_filename(text):
    """Elimina caracteres inválidos para nombres de archivo"""
    if not text:
        return "SIN_NOMBRE"
    return "".join(c if c.isalnum() or c in "-_" else "" for c in text.upper())


def _obtener_historial(personal_id):
    """Obtiene historial completo de una persona"""
    try:
        personal = PM.objects.get(id=personal_id)
    except PM.DoesNotExist:
        return None, None

    sims = SIM.objects.filter(militares__id=personal_id).distinct()
    sim_ids = list(sims.values_list('id', flat=True))

    historial = {
        'personal': personal,
        'sumarios': sims,
        'resoluciones': Resolucion.objects.filter(sim__in=sim_ids, instancia='PRIMERA'),
        'segundas_resoluciones': Resolucion.objects.filter(sim__in=sim_ids, instancia='RECONSIDERACION'),
        'recursos_apelacion': RecursoTSP.objects.filter(sim__in=sim_ids, instancia='APELACION'),
        'raees': RecursoTSP.objects.filter(sim__in=sim_ids, instancia='ACLARACION_ENMIENDA'),
        'autos_tpe': AUTOTPE.objects.filter(sim__in=sim_ids),
        'autos_tsp': AUTOTSP.objects.filter(sim__in=sim_ids),
    }

    return personal, historial


@login_required
def export_person_historial_pdf(request, personal_id):
    """Genera PDF formal del historial disciplinario de un militar."""
    personal, historial = _obtener_historial(personal_id)
    if not personal or not historial:
        get_object_or_404(PM, id=personal_id)
        return HttpResponse("Personal no encontrado", status=404)

    # Registrar fuente Arial desde Windows
    try:
        pdfmetrics.getFont('Arial-Bold')
    except KeyError:
        pdfmetrics.registerFont(TTFont('Arial',      'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))

    buffer = BytesIO()
    page_w, _ = letter
    margin = 0.65 * inch


    # Estilos de párrafo
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
    s_pais    = _estilo('pais',   fuente='Arial', tamaño=10, alineacion=TA_LEFT, negrita=True, espacio_despues=6, interlinea=13, sangria=70)
    s_seccion = _estilo('secc',   fuente='Arial', tamaño=14, alineacion=TA_CENTER, negrita=True, espacio_antes=6, espacio_despues=4, interlinea=17)
    s_dato    = _estilo('dato',   tamaño=8.5)
    s_objeto  = _estilo('obj',    tamaño=8,  alineacion=TA_JUSTIFY, interlinea=10)
    s_sim_tit = _estilo('simtit', tamaño=9,  negrita=True, color=colors.black, espacio_antes=4, espacio_despues=2)
    s_th      = _estilo('th',     tamaño=7.5, alineacion=TA_CENTER, negrita=True, color=colors.black)
    s_td      = _estilo('td',     tamaño=7,  interlinea=9)
    s_td_c    = _estilo('tdc',    tamaño=7,  alineacion=TA_CENTER, interlinea=9)
    s_stat_h  = _estilo('sth',    tamaño=8,  alineacion=TA_CENTER, negrita=True, color=colors.black)
    s_stat_v  = _estilo('stv',    tamaño=18, alineacion=TA_CENTER, negrita=True, color=colors.black, interlinea=22)


    # Obtener datos del usuario que imprime
    nombre_usuario = request.user.get_full_name() or request.user.username
    grado_usuario = ""
    espec_usuario = ""
    if request.user.is_authenticated:
        try:
            perfil = request.user.perfilusuario
            if perfil.abogado:
                grado_usuario = perfil.abogado.grado or ""
                espec_usuario = perfil.abogado.arma or ""
            elif perfil.vocal and perfil.vocal.pm:
                grado_usuario = perfil.vocal.pm.get_grado_display() or ""
                espec_usuario = perfil.vocal.pm.get_arma_display() or ""
        except Exception:
            pass

    partes_pie = [p for p in [grado_usuario, nombre_usuario.upper(), espec_usuario] if p]
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

    # ── DATOS DEL PERSONAL ───────────────────────────────────────────────────
    story.append(Paragraph("<u>DATOS DEL PERSONAL</u>", s_seccion))
    story.append(Spacer(1, 4))

    grado        = personal.get_grado_display() or 'N/A'
    especialidad = personal.get_arma_display() or 'N/A'
    nombre_comp  = f"{personal.nombre} {personal.paterno} {personal.materno or ''}".strip()
    ci           = str(personal.ci) if personal.ci else 'N/A'
    escalafon    = personal.get_escalafon_display() or 'N/A'
    estado_pm    = personal.get_estado_display()
    anio_egreso  = str(personal.anio_promocion) if personal.anio_promocion else 'N/A'
    años_serv    = personal.años_servicio
    grado_esp    = personal.grado_esperado
    no_asc_txt   = '  ⚠ No ascendió al grado correspondiente' if personal.no_ascendio else ''

    grado_line = grado
    if grado_esp and grado_esp != grado:
        grado_line = f"{grado}  (esperado: {grado_esp}{no_asc_txt})"
    elif personal.no_ascendio:
        grado_line = f"{grado}{no_asc_txt}"

    col2 = usable_w / 2
    tabla_datos = Table([
        [Paragraph(f"<b>Grado:</b>  {grado_line}",    s_dato), Paragraph(f"<b>Especialidad:</b>  {especialidad}", s_dato)],
        [Paragraph(f"<b>Nombre:</b>  {nombre_comp}",  s_dato), ''],
        [Paragraph(f"<b>C.I.:</b>  {ci}",             s_dato), Paragraph(f"<b>Escalafón:</b>  {escalafon}",     s_dato)],
        [Paragraph(f"<b>Estado:</b>  {estado_pm}",    s_dato), Paragraph(f"<b>Año Egreso:</b>  {anio_egreso}  ({años_serv} años de servicio)" if años_serv else f"<b>Año Egreso:</b>  {anio_egreso}", s_dato)],
    ], colWidths=[col2, col2])
    tabla_datos.setStyle(TableStyle([
        ('SPAN',          (0, 1), (1, 1)),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('LINEBELOW',     (0, -1), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(tabla_datos)
    story.append(Spacer(1, 10))

    # ── RESUMEN ESTADÍSTICO ──────────────────────────────────────────────────
    story.append(Paragraph("<u>RESUMEN ESTADÍSTICO</u>", s_seccion))
    story.append(Spacer(1, 4))

    n_sim  = historial['sumarios'].count()
    n_res  = historial['resoluciones'].count()
    n_auto = historial['autos_tpe'].count()
    col3 = usable_w / 3
    tabla_stats = Table([
        [Paragraph('SUMARIOS', s_stat_h), Paragraph('RESOLUCIONES', s_stat_h), Paragraph('AUTOS TPE', s_stat_h)],
        [Paragraph(str(n_sim),  s_stat_v), Paragraph(str(n_res),   s_stat_v), Paragraph(str(n_auto), s_stat_v)],
    ], colWidths=[col3, col3, col3])
    tabla_stats.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.8, colors.black),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla_stats)
    story.append(Spacer(1, 10))

    # ── ACTUADOS POR SUMARIO ─────────────────────────────────────────────────
    story.append(Paragraph("<u>ACTUADOS POR SUMARIO</u>", s_seccion))
    story.append(Spacer(1, 6))

    sumarios = historial['sumarios']
    if not sumarios.exists():
        story.append(Paragraph("No se registran sumarios para este personal.", s_dato))
    else:
        # Anchos de columna: TIPO 20% | N° 9% | FECHA 12% | RESOLUTIVA 44% | NOTIF. 15%
        cw = [usable_w * p for p in (0.20, 0.09, 0.12, 0.44, 0.15)]

        for idx, sim in enumerate(sumarios, 1):
            story.append(Paragraph(f"SUMARIO N.° {sim.codigo}", s_sim_tit))

            objeto = sim.objeto or 'N/A'
            story.append(Paragraph(f"<b>Objeto:</b> {objeto}", s_objeto))

            estado_display = (sim.get_estado_display()
                              if hasattr(sim, 'get_estado_display') else sim.estado)
            story.append(Paragraph(f"<b>Estado:</b> {estado_display}", s_dato))

            # Grado que tenía el militar cuando se tramitó este sumario
            from tpe_app.models import PM_SIM as PM_SIM_model
            pm_sim_reg = PM_SIM_model.objects.filter(sim=sim, pm=personal).first()
            if pm_sim_reg and pm_sim_reg.grado_en_fecha:
                story.append(Paragraph(
                    f"<b>Grado al momento del sumario:</b> {pm_sim_reg.grado_en_fecha}",
                    s_dato
                ))
            story.append(Spacer(1, 5))

            # Recopilar actuados
            documentos = []
            for res in historial['resoluciones'].filter(sim=sim):
                documentos.append({
                    'tipo': 'RESOLUCIÓN',
                    'numero': res.numero or 'S/N',
                    'fecha_doc': res.fecha,
                    'resolutiva': res.texto or 'N/A',
                    'notificacion': 'Sí' if getattr(res, 'notificacion', None) else 'No',
                })
            for rr in historial.get('segundas_resoluciones', Resolucion.objects.none()).filter(sim=sim):
                documentos.append({
                    'tipo': 'REC. RECONSIDERACIÓN',
                    'numero': rr.numero or 'S/N',
                    'fecha_doc': rr.fecha,
                    'resolutiva': rr.texto or 'N/A',
                    'notificacion': 'Sí' if getattr(rr, 'notificacion', None) else 'No',
                })
            for auto in historial['autos_tpe'].filter(sim=sim):
                documentos.append({
                    'tipo': 'AUTO TPE',
                    'numero': auto.numero or 'S/N',
                    'fecha_doc': auto.fecha,
                    'resolutiva': auto.get_tipo_display() if auto.tipo else 'N/A',
                    'notificacion': 'Sí' if getattr(auto, 'notificacion', None) else 'No',
                })
            documentos.sort(key=lambda x: x['fecha_doc'] or date.min)

            if documentos:
                filas = [[Paragraph(h, s_th) for h in ('TIPO', 'N°', 'FECHA', 'RESOLUTIVA', 'NOTIF.')]]
                for actuado in documentos:
                    filas.append([
                        Paragraph(actuado['tipo'],                    s_td),
                        Paragraph(str(actuado['numero']),             s_td_c),
                        Paragraph(_format_date(actuado['fecha_doc']), s_td_c),
                        Paragraph(actuado['resolutiva'],              s_td),
                        Paragraph(actuado['notificacion'],            s_td_c),
                    ])

                ts = [
                    ('BOX',           (0, 0), (-1, -1), 0.5, colors.black),
                    ('INNERGRID',     (0, 0), (-1, -1), 0.3, colors.black),
                    ('LINEBELOW',     (0, 0), (-1, 0), 0.8, colors.black),
                    ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING',    (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
                ]

                t = Table(filas, colWidths=cw, repeatRows=1)
                t.setStyle(TableStyle(ts))
                story.append(t)
            else:
                story.append(Paragraph("Sin actuados registrados.", s_dato))

            story.append(Spacer(1, 8))
            if idx < sumarios.count():
                story.append(HRFlowable(width="100%", thickness=0.4, color=colors.lightgrey))
                story.append(Spacer(1, 4))

    doc.build(story, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    buffer.seek(0)

    fecha_export = datetime.now().strftime("%d-%m-%Y")
    filename = f"HISTORIAL_{personal.ci}_{fecha_export}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_person_pdfs_zip(request, personal_id):
    """
    DEPRECATED: Mantener por compatibilidad. Redirige a export_person_historial_pdf.
    """
    return export_person_historial_pdf(request, personal_id)


def _generar_pdf_sumario(personal, sim, historial):
    """
    Genera un PDF para un sumario específico (o resumen si sim es None).
    Retorna BytesIO con contenido PDF.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Márgenes
    x_margin = 0.5 * inch
    y_position = height - 0.5 * inch
    line_height = 0.2 * inch

    # ===== ENCABEZADO =====
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y_position, "SUMARIO DISCIPLINARIO")
    y_position -= 1.5 * line_height

    # Línea separadora
    c.setLineWidth(1)
    c.line(x_margin, y_position, width - x_margin, y_position)
    y_position -= line_height

    # ===== DATOS PERSONALES =====
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_margin, y_position, "PERSONAL MILITAR:")
    y_position -= line_height

    c.setFont("Helvetica", 9)
    datos_personales = [
        f"Nombre: {personal.nombre} {personal.paterno} {personal.materno or ''}",
        f"CI: {personal.ci}",
        f"Grado: {personal.get_grado_display() or 'N/A'}",
        f"Arma: {personal.get_arma_display() or 'N/A'}",
        f"Estado: {personal.get_estado_display()}"
    ]

    for dato in datos_personales:
        c.drawString(x_margin + 0.2 * inch, y_position, dato)
        y_position -= line_height

    y_position -= 0.5 * line_height

    # ===== SUMARIO =====
    if sim:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y_position, f"SUMARIO: {sim.codigo}")
        y_position -= line_height

        c.setFont("Helvetica", 9)
        sim_data = [
            f"Tipo: {sim.get_tipo_display() if sim.tipo else 'N/A'}",
            f"Objeto: {sim.objeto[:100]}..." if len(sim.objeto or '') > 100 else f"Objeto: {sim.objeto or 'N/A'}",
            f"Resumen: {sim.resumen or 'N/A'}",
            f"Fecha Ingreso: {_format_date(sim.fecha_ingreso)}",
            f"Estado: {sim.get_estado_display() if hasattr(sim, 'get_estado_display') else sim.estado}"
        ]

        for dato in sim_data:
            if y_position < 1.5 * inch:  # Nueva página si falta espacio
                c.showPage()
                y_position = height - 0.5 * inch
            c.drawString(x_margin + 0.2 * inch, y_position, dato)
            y_position -= line_height

        y_position -= 0.5 * line_height

        # ===== RESOLUCIONES (RES) =====
        resoluciones = historial['resoluciones'].filter(sim=sim)
        if resoluciones.exists():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_margin, y_position, f"RESOLUCIONES: ({resoluciones.count()})")
            y_position -= line_height

            c.setFont("Helvetica", 8)
            for res in resoluciones:
                if y_position < 1.5 * inch:
                    c.showPage()
                    y_position = height - 0.5 * inch

                res_text = f"• {res.numero} ({_format_date(res.fecha)}) — {res.get_tipo_display()}"
                c.drawString(x_margin + 0.3 * inch, y_position, res_text)
                y_position -= line_height * 0.8

                # Referencia a PDF en OneDrive
                pdf_ref = f"  Ref: RES. {res.numero} (OneDrive)"
                c.drawString(x_margin + 0.5 * inch, y_position, pdf_ref)
                y_position -= line_height * 0.8

        y_position -= 0.3 * line_height

        # ===== RECURSOS Y AUTOS =====
        rr = historial['segundas_resoluciones'].filter(sim=sim)
        rap = historial['recursos_apelacion'].filter(sim=sim)
        raee = historial['raees'].filter(sim=sim)
        autos_tpe = historial['autos_tpe'].filter(sim=sim)
        autos_tsp = historial['autos_tsp'].filter(sim=sim)

        if rr.exists() or rap.exists() or raee.exists() or autos_tpe.exists() or autos_tsp.exists():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_margin, y_position, "RECURSOS Y AUTOS:")
            y_position -= line_height

            c.setFont("Helvetica", 9)
            recursos = [
                (f"Reconsideración (RR): {rr.count()} registro(s)" if rr.exists() else "Reconsideración (RR): No aplica"),
                (f"Apelación (RAP): {rap.count()} registro(s)" if rap.exists() else "Apelación (RAP): No aplica"),
                (f"RAEE: {raee.count()} registro(s)" if raee.exists() else "RAEE: No aplica"),
                (f"Autos TPE: {autos_tpe.count()} registro(s)" if autos_tpe.exists() else "Autos TPE: No"),
                (f"Autos TSP: {autos_tsp.count()} registro(s)" if autos_tsp.exists() else "Autos TSP: No"),
            ]

            for recurso in recursos:
                if y_position < 1.5 * inch:
                    c.showPage()
                    y_position = height - 0.5 * inch
                c.drawString(x_margin + 0.2 * inch, y_position, recurso)
                y_position -= line_height

    else:
        # Sin sumarios
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_position, "NO HAY SUMARIOS REGISTRADOS PARA ESTE PERSONAL")

    c.save()
    buffer.seek(0)
    return buffer


@login_required
def export_person_excel(request, personal_id):
    """
    Genera un Excel con 4 hojas: Personal, Sumarios, Resoluciones, Cronología.
    """
    personal, historial = _obtener_historial(personal_id)

    if not personal or not historial:
        personal = get_object_or_404(PM, id=personal_id)
        return HttpResponse("Personal no encontrado", status=404)

    if not historial:
        return HttpResponse("Personal no encontrado", status=404)

    # Crear workbook
    wb = Workbook()
    wb.remove(wb.active)  # Eliminar hoja por defecto

    # ===== HOJA 1: PERSONAL =====
    ws_personal = wb.create_sheet("PERSONAL")
    ws_personal['A1'] = "INFORMACIÓN PERSONAL"
    ws_personal['A1'].font = Font(bold=True, size=12)

    personal_data = [
        ("CI:", str(personal.ci)),
        ("Nombre:", f"{personal.nombre} {personal.paterno} {personal.materno or ''}"),
        ("Grado:", personal.get_grado_display() or "N/A"),
        ("Escalafón:", personal.get_escalafon_display() or "N/A"),
        ("Arma:", personal.get_arma_display() or "N/A"),
        ("Especialidad:", personal.especialidad or "N/A"),
        ("Estado:", personal.get_estado_display()),
        ("Fecha Promoción:", _format_date(personal.anio_promocion)),
    ]

    for idx, (label, value) in enumerate(personal_data, start=2):
        ws_personal[f'A{idx}'] = label
        ws_personal[f'A{idx}'].font = Font(bold=True)
        ws_personal[f'B{idx}'] = value

    ws_personal.column_dimensions['A'].width = 20
    ws_personal.column_dimensions['B'].width = 40

    # ===== HOJA 2: SUMARIOS =====
    ws_sumarios = wb.create_sheet("SUMARIOS")
    headers_sim = ["DJE", "Tipo", "Objeto", "Resumen", "Fecha Ingreso", "Estado"]
    for col, header in enumerate(headers_sim, 1):
        cell = ws_sumarios.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="185FA5", end_color="185FA5", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    for row_idx, sim in enumerate(historial['sumarios'], 2):
        ws_sumarios.cell(row=row_idx, column=1, value=sim.codigo)
        ws_sumarios.cell(row=row_idx, column=2, value=sim.get_tipo_display() if sim.tipo else "N/A")
        ws_sumarios.cell(row=row_idx, column=3, value=sim.objeto[:50] + "..." if len(sim.objeto or '') > 50 else sim.objeto)
        ws_sumarios.cell(row=row_idx, column=4, value=sim.resumen or "N/A")
        ws_sumarios.cell(row=row_idx, column=5, value=_format_date(sim.fecha_ingreso))
        ws_sumarios.cell(row=row_idx, column=6, value=sim.estado)

    for col in range(1, len(headers_sim) + 1):
        ws_sumarios.column_dimensions[chr(64 + col)].width = 25

    # ===== HOJA 3: RESOLUCIONES =====
    ws_docs = wb.create_sheet("RESOLUCIONES")
    headers_docs = ["SIM", "Tipo Documento", "Número", "Fecha", "Notificación", "Fecha Notificación"]
    for col, header in enumerate(headers_docs, 1):
        cell = ws_docs.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="185FA5", end_color="185FA5", fill_type="solid")

    row_idx = 2
    # Resoluciones (RES)
    for res in historial['resoluciones']:
        ws_docs.cell(row=row_idx, column=1, value=res.sim.codigo)
        ws_docs.cell(row=row_idx, column=2, value="Resolución TPE (RES)")
        ws_docs.cell(row=row_idx, column=3, value=res.numero)
        ws_docs.cell(row=row_idx, column=4, value=_format_date(res.fecha))
        notif_res = getattr(res, 'notificacion', None)
        ws_docs.cell(row=row_idx, column=5, value=notif_res.tipo if notif_res else "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(notif_res.fecha if notif_res else None))
        row_idx += 1

    # Segundas Resoluciones (RR) — Resolucion RECONSIDERACION
    for rr in historial['segundas_resoluciones']:
        ws_docs.cell(row=row_idx, column=1, value=rr.sim.codigo)
        ws_docs.cell(row=row_idx, column=2, value="Recurso Reconsideración (RR)")
        ws_docs.cell(row=row_idx, column=3, value=rr.numero or "N/A")
        ws_docs.cell(row=row_idx, column=4, value=_format_date(rr.fecha))
        notif_rr = getattr(rr, 'notificacion', None)
        ws_docs.cell(row=row_idx, column=5, value=notif_rr.notificado_a if notif_rr else "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(notif_rr.fecha if notif_rr else None))
        row_idx += 1

    # Recursos de Apelación (RAP) — RecursoTSP APELACION
    for rap in historial['recursos_apelacion']:
        ws_docs.cell(row=row_idx, column=1, value=rap.sim.codigo)
        ws_docs.cell(row=row_idx, column=2, value="Recurso Apelación (RAP)")
        ws_docs.cell(row=row_idx, column=3, value=rap.numero or "N/A")
        ws_docs.cell(row=row_idx, column=4, value=_format_date(rap.fecha))
        notif_rap = getattr(rap, 'notificacion', None)
        ws_docs.cell(row=row_idx, column=5, value=notif_rap.tipo if notif_rap else "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(notif_rap.fecha if notif_rap else None))
        row_idx += 1

    # RAEE — RecursoTSP ACLARACION_ENMIENDA
    for raee in historial['raees']:
        ws_docs.cell(row=row_idx, column=1, value=raee.sim.codigo)
        ws_docs.cell(row=row_idx, column=2, value="Recurso RAEE")
        ws_docs.cell(row=row_idx, column=3, value=raee.numero or "N/A")
        ws_docs.cell(row=row_idx, column=4, value=_format_date(raee.fecha))
        notif_raee = getattr(raee, 'notificacion', None)
        ws_docs.cell(row=row_idx, column=5, value=notif_raee.tipo if notif_raee else "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(notif_raee.fecha if notif_raee else None))
        row_idx += 1

    for col in range(1, len(headers_docs) + 1):
        ws_docs.column_dimensions[chr(64 + col)].width = 22

    # ===== HOJA 4: CRONOLOGÍA =====
    ws_crono = wb.create_sheet("CRONOLOGÍA")
    headers_crono = ["Fecha", "Tipo Evento", "Descripción"]
    for col, header in enumerate(headers_crono, 1):
        cell = ws_crono.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="185FA5", end_color="185FA5", fill_type="solid")

    # Crear timeline ordenada
    eventos = []
    for sim in historial['sumarios']:
        eventos.append((sim.fecha_ingreso, "Sumario Ingreso", f"SIM {sim.codigo}: {sim.resumen}"))

    for res in historial['resoluciones']:
        eventos.append((res.fecha, "Resolución TPE", f"RES {res.numero}: {res.get_tipo_display()}"))

    for rap in historial['recursos_apelacion']:
        eventos.append((rap.fecha, "Apelación TSP", f"RAP {rap.numero or 'Pendiente'}: {rap.tipo or 'N/A'}"))

    # Ordenar por fecha
    eventos = sorted([e for e in eventos if e[0]], key=lambda x: x[0])

    for row_idx, (fecha, tipo, desc) in enumerate(eventos, 2):
        ws_crono.cell(row=row_idx, column=1, value=_format_date(fecha))
        ws_crono.cell(row=row_idx, column=2, value=tipo)
        ws_crono.cell(row=row_idx, column=3, value=desc)

    for col in range(1, len(headers_crono) + 1):
        ws_crono.column_dimensions[chr(64 + col)].width = 25

    # Guardar
    fecha_export = datetime.now().strftime("%Y-%m-%d")
    excel_filename = f"HISTORIAL_{personal.ci}_{fecha_export}.xlsx"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{excel_filename}"'
    return response


# ============================================================
# EXPORTACIÓN DE SIM COMPLETO
# ============================================================

@login_required
def export_sim_pdf(request, sim_id):
    """Exporta un SIM completo a PDF con militares y actuados"""
    sim = get_object_or_404(SIM, id=sim_id)
    militares = sim.militares.all()
    resoluciones = Resolucion.objects.filter(sim=sim)
    autos_tpe = AUTOTPE.objects.filter(sim=sim)
    autos_tsp = AUTOTSP.objects.filter(sim=sim)
    recursos_tsp = RecursoTSP.objects.filter(sim=sim)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.5 * inch
    y_position = height - 0.5 * inch
    line_height = 0.2 * inch

    # ENCABEZADO
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y_position, "REPORTE DE SUMARIO")
    y_position -= 1.2 * line_height

    c.setFont("Helvetica", 8)
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.now().strftime("%H:%M:%S")
    usuario = request.user.get_full_name() or request.user.username if request.user.is_authenticated else "Usuario"

    c.drawString(x_margin, y_position, f"Impreso por: {usuario.upper()} — Fecha: {fecha_hoy} — Hora: {hora_hoy}")
    y_position -= line_height * 0.8

    c.setLineWidth(1)
    c.line(x_margin, y_position, width - x_margin, y_position)
    y_position -= 1 * line_height

    # INFORMACIÓN DEL SIM
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y_position, "INFORMACIÓN DEL SUMARIO")
    y_position -= line_height

    c.setFont("Helvetica", 9)
    info_sim = [
        f"Código: {sim.codigo}",
        f"Tipo: {sim.get_tipo_display()}",
        f"Objeto: {sim.objeto}",
        f"Resumen: {sim.resumen}",
        f"Fecha Ingreso: {_format_date(sim.fecha_ingreso)}",
        f"Estado: {sim.get_estado_display()}",
    ]

    for info in info_sim:
        if y_position < 2 * inch:
            c.showPage()
            y_position = height - 0.5 * inch
        c.drawString(x_margin + 0.2 * inch, y_position, info)
        y_position -= line_height

    y_position -= 0.5 * line_height

    # MILITARES INVESTIGADOS
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y_position, f"MILITARES INVESTIGADOS ({militares.count()})")
    y_position -= line_height

    c.setFont("Helvetica", 8)
    for militar in militares:
        if y_position < 2 * inch:
            c.showPage()
            y_position = height - 0.5 * inch
        nombre_completo = f"{militar.grado} {militar.nombre} {militar.paterno} {militar.materno or ''}"
        c.drawString(x_margin + 0.2 * inch, y_position, f"• {nombre_completo} (CI: {militar.ci or 'N/A'})")
        y_position -= line_height

    y_position -= 0.5 * line_height

    # RESOLUCIONES
    if resoluciones.exists():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, f"RESOLUCIONES ({resoluciones.count()})")
        y_position -= line_height

        c.setFont("Helvetica", 8)
        for res in resoluciones:
            if y_position < 2 * inch:
                c.showPage()
                y_position = height - 0.5 * inch
            res_info = f"• RES {res.numero} ({_format_date(res.fecha)}) — {res.get_tipo_display()}"
            c.drawString(x_margin + 0.2 * inch, y_position, res_info)
            y_position -= line_height

        y_position -= 0.3 * line_height

    # AUTOS TPE
    if autos_tpe.exists():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, f"AUTOS TPE ({autos_tpe.count()})")
        y_position -= line_height

        c.setFont("Helvetica", 8)
        for auto in autos_tpe:
            if y_position < 2 * inch:
                c.showPage()
                y_position = height - 0.5 * inch
            auto_info = f"• AUTO {auto.numero} ({_format_date(auto.fecha)}) — {auto.get_tipo_display()}"
            c.drawString(x_margin + 0.2 * inch, y_position, auto_info)
            y_position -= line_height

        y_position -= 0.3 * line_height

    # RECURSOS TSP
    if recursos_tsp.exists():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, f"RECURSOS TSP ({recursos_tsp.count()})")
        y_position -= line_height

        c.setFont("Helvetica", 8)
        for recurso in recursos_tsp:
            if y_position < 2 * inch:
                c.showPage()
                y_position = height - 0.5 * inch
            recurso_info = f"• {recurso.get_instancia_display()} ({_format_date(recurso.fecha)})"
            c.drawString(x_margin + 0.2 * inch, y_position, recurso_info)
            y_position -= line_height

    c.save()
    buffer.seek(0)

    fecha_export = datetime.now().strftime("%Y-%m-%d")
    filename = f"SIM_{_sanitize_filename(sim.codigo)}_{fecha_export}.pdf"

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_sim_excel(request, sim_id):
    """Exporta un SIM completo a Excel con 3 hojas: SIM, Militares, Actuados"""
    sim = get_object_or_404(SIM, id=sim_id)
    militares = sim.militares.all()
    resoluciones = Resolucion.objects.filter(sim=sim)
    autos_tpe = AUTOTPE.objects.filter(sim=sim)
    autos_tsp = AUTOTSP.objects.filter(sim=sim)
    recursos_tsp = RecursoTSP.objects.filter(sim=sim)

    wb = Workbook()
    wb.remove(wb.active)

    # ===== HOJA 1: INFORMACIÓN DEL SIM =====
    ws_sim = wb.create_sheet("SIM")
    ws_sim['A1'] = "INFORMACIÓN DEL SUMARIO"
    ws_sim['A1'].font = Font(bold=True, size=12)

    sim_data = [
        ("Código:", sim.codigo),
        ("Tipo:", sim.get_tipo_display()),
        ("Objeto:", sim.objeto),
        ("Resumen:", sim.resumen),
        ("Fecha Ingreso:", _format_date(sim.fecha_ingreso)),
        ("Estado:", sim.get_estado_display()),
    ]

    for idx, (label, value) in enumerate(sim_data, start=2):
        ws_sim[f'A{idx}'] = label
        ws_sim[f'A{idx}'].font = Font(bold=True)
        ws_sim[f'B{idx}'] = value

    ws_sim.column_dimensions['A'].width = 20
    ws_sim.column_dimensions['B'].width = 50

    # ===== HOJA 2: MILITARES =====
    ws_militares = wb.create_sheet("MILITARES")
    headers_militares = ["Grado", "Nombre", "Apellido Paterno", "Apellido Materno", "CI", "Arma", "Escalafón"]
    for col, header in enumerate(headers_militares, 1):
        cell = ws_militares.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="185FA5", end_color="185FA5", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    for idx, militar in enumerate(militares, start=2):
        ws_militares.cell(row=idx, column=1, value=militar.grado)
        ws_militares.cell(row=idx, column=2, value=militar.nombre)
        ws_militares.cell(row=idx, column=3, value=militar.paterno)
        ws_militares.cell(row=idx, column=4, value=militar.materno or "")
        ws_militares.cell(row=idx, column=5, value=str(militar.ci) if militar.ci else "")
        ws_militares.cell(row=idx, column=6, value=militar.get_arma_display() or "")
        ws_militares.cell(row=idx, column=7, value=militar.get_escalafon_display() or "")

    for col in range(1, len(headers_militares) + 1):
        ws_militares.column_dimensions[chr(64 + col)].width = 18

    # ===== HOJA 3: ACTUADOS =====
    ws_actuados = wb.create_sheet("ACTUADOS")
    headers_actuados = ["Tipo", "Número", "Fecha", "Descripción", "Notificación", "Fecha Notificación"]
    for col, header in enumerate(headers_actuados, 1):
        cell = ws_actuados.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="185FA5", end_color="185FA5", fill_type="solid")

    row_idx = 2

    # Resoluciones
    for res in resoluciones:
        ws_actuados.cell(row=row_idx, column=1, value="Resolución TPE")
        ws_actuados.cell(row=row_idx, column=2, value=res.numero or "N/A")
        ws_actuados.cell(row=row_idx, column=3, value=_format_date(res.fecha))
        ws_actuados.cell(row=row_idx, column=4, value=res.get_tipo_display() or "")
        n_res = getattr(res, 'notificacion', None)
        ws_actuados.cell(row=row_idx, column=5, value=n_res.tipo if n_res else "")
        ws_actuados.cell(row=row_idx, column=6, value=_format_date(n_res.fecha if n_res else None))
        row_idx += 1

    # Autos TPE
    for auto in autos_tpe:
        ws_actuados.cell(row=row_idx, column=1, value="Auto TPE")
        ws_actuados.cell(row=row_idx, column=2, value=auto.numero or "N/A")
        ws_actuados.cell(row=row_idx, column=3, value=_format_date(auto.fecha))
        ws_actuados.cell(row=row_idx, column=4, value=auto.get_tipo_display() or "")
        n_auto = getattr(auto, 'notificacion', None)
        ws_actuados.cell(row=row_idx, column=5, value=n_auto.tipo if n_auto else "")
        ws_actuados.cell(row=row_idx, column=6, value=_format_date(n_auto.fecha if n_auto else None))
        row_idx += 1

    # Autos TSP
    for auto in autos_tsp:
        ws_actuados.cell(row=row_idx, column=1, value="Auto TSP")
        ws_actuados.cell(row=row_idx, column=2, value=auto.numero or "N/A")
        ws_actuados.cell(row=row_idx, column=3, value=_format_date(auto.fecha))
        ws_actuados.cell(row=row_idx, column=4, value=auto.get_tipo_display() or "")
        n_tsp = getattr(auto, 'notificacion', None)
        ws_actuados.cell(row=row_idx, column=5, value=n_tsp.tipo if n_tsp else "")
        ws_actuados.cell(row=row_idx, column=6, value=_format_date(n_tsp.fecha if n_tsp else None))
        row_idx += 1

    # Recursos TSP
    for recurso in recursos_tsp:
        ws_actuados.cell(row=row_idx, column=1, value=recurso.get_instancia_display())
        ws_actuados.cell(row=row_idx, column=2, value=recurso.numero or "N/A")
        ws_actuados.cell(row=row_idx, column=3, value=_format_date(recurso.fecha))
        ws_actuados.cell(row=row_idx, column=4, value=recurso.get_instancia_display() or "")
        n_rec = getattr(recurso, 'notificacion', None)
        ws_actuados.cell(row=row_idx, column=5, value=n_rec.tipo if n_rec else "")
        ws_actuados.cell(row=row_idx, column=6, value=_format_date(n_rec.fecha if n_rec else None))
        row_idx += 1

    for col in range(1, len(headers_actuados) + 1):
        ws_actuados.column_dimensions[chr(64 + col)].width = 18

    # Guardar
    fecha_export = datetime.now().strftime("%Y-%m-%d")
    excel_filename = f"SIM_{_sanitize_filename(sim.codigo)}_{fecha_export}.xlsx"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{excel_filename}"'
    return response

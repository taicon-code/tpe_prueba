# ============================================================
#  VISTAS DE EXPORTACIÓN - PDF (ZIP) y EXCEL
#  Archivo: tpe_app/views/export_views.py
# ============================================================

from io import BytesIO
from datetime import datetime
from zipfile import ZipFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from tpe_app.models import PM, SIM, AUTOTPE, AUTOTSP, Resolucion, RecursoTSP


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
        personal = PM.objects.get(pm_id=personal_id)
    except PM.DoesNotExist:
        return None, None

    sims = SIM.objects.filter(militares__pm_id=personal_id).distinct()
    sim_ids = list(sims.values_list('id', flat=True))

    historial = {
        'personal': personal,
        'sumarios': sims,
        'resoluciones': Resolucion.objects.filter(sim__in=sim_ids, RES_INSTANCIA='PRIMERA'),
        'segundas_resoluciones': Resolucion.objects.filter(sim__in=sim_ids, RES_INSTANCIA='RECONSIDERACION'),
        'recursos_apelacion': RecursoTSP.objects.filter(sim__in=sim_ids, TSP_INSTANCIA='APELACION'),
        'raees': RecursoTSP.objects.filter(sim__in=sim_ids, TSP_INSTANCIA='ACLARACION_ENMIENDA'),
        'autos_tpe': AUTOTPE.objects.filter(sim__in=sim_ids),
        'autos_tsp': AUTOTSP.objects.filter(sim__in=sim_ids),
    }

    return personal, historial


def export_person_historial_pdf(request, personal_id):
    """
    Genera un PDF único con el historial completo de una persona.
    Incluye estadísticas, todos los sumarios y sus actuados.
    """
    personal, historial = _obtener_historial(personal_id)

    if not personal or not historial:
        personal = get_object_or_404(PM, pm_id=personal_id)
        return HttpResponse("Personal no encontrado", status=404)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.5 * inch
    y_position = height - 0.5 * inch
    line_height = 0.2 * inch

    # ===== ENCABEZADO =====
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y_position, "REPORTE DE HISTORIAL - SUMARIOS DISCIPLINARIOS")
    y_position -= 1.5 * line_height

    c.setFont("Helvetica", 9)
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    c.drawString(x_margin, y_position, f"Generado: {fecha_hoy}")
    y_position -= line_height

    c.setLineWidth(1)
    c.line(x_margin, y_position, width - x_margin, y_position)
    y_position -= 1.2 * line_height

    # ===== DATOS PERSONALES =====
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y_position, "PERSONAL MILITAR")
    y_position -= line_height

    c.setFont("Helvetica", 9)
    datos = [
        f"Nombre: {personal.PM_NOMBRE} {personal.PM_PATERNO} {personal.PM_MATERNO or ''}",
        f"CI: {personal.PM_CI}",
        f"Grado: {personal.get_PM_GRADO_display() or 'N/A'}",
        f"Arma: {personal.get_PM_ARMA_display() or 'N/A'}",
        f"Estado: {personal.get_PM_ESTADO_display()}"
    ]
    for dato in datos:
        c.drawString(x_margin + 0.2 * inch, y_position, dato)
        y_position -= line_height

    y_position -= 0.5 * line_height

    # ===== ESTADÍSTICAS =====
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y_position, "ESTADÍSTICAS")
    y_position -= line_height

    c.setFont("Helvetica", 9)
    total_autos = historial['autos_tpe'].count() + historial['autos_tsp'].count()
    stats = [
        f"Total Sumarios: {historial['sumarios'].count()}",
        f"Total Resoluciones: {historial['resoluciones'].count()}",
        f"Total Autos TPE: {historial['autos_tpe'].count()}",
        f"Total Autos TSP: {historial['autos_tsp'].count()}",
        f"Total Autos: {total_autos}",
        f"Total Recursos Reconsideración: {historial['segundas_resoluciones'].count()}",
        f"Total Apelaciones TSP: {historial['recursos_apelacion'].count()}",
        f"Total RAEE: {historial['raees'].count()}"
    ]
    for stat in stats:
        c.drawString(x_margin + 0.2 * inch, y_position, stat)
        y_position -= line_height

    y_position -= 0.7 * line_height

    # ===== ACTUADOS POR SUMARIO =====
    sumarios = historial['sumarios']
    if sumarios.exists():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y_position, "ACTUADOS POR SUMARIO")
        y_position -= line_height * 1.3

        for idx, sim in enumerate(sumarios, 1):
            if y_position < 2 * inch:
                c.showPage()
                y_position = height - 0.5 * inch

            # Encabezado del sumario
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_margin, y_position, f"SUMARIO {idx}: {sim.SIM_COD}")
            y_position -= line_height

            c.setFont("Helvetica", 8)
            c.drawString(x_margin + 0.2 * inch, y_position, f"Tipo: {sim.get_SIM_TIPO_display() if sim.SIM_TIPO else 'N/A'}")
            y_position -= line_height * 0.7

            c.drawString(x_margin + 0.2 * inch, y_position, f"Objeto: {sim.SIM_OBJETO[:80] if sim.SIM_OBJETO else 'N/A'}")
            y_position -= line_height * 0.7

            c.drawString(x_margin + 0.2 * inch, y_position, f"Fecha Ingreso: {_format_date(sim.SIM_FECING)}")
            y_position -= line_height * 0.7

            c.drawString(x_margin + 0.2 * inch, y_position, f"Estado Actual: {sim.SIM_ESTADO if hasattr(sim, 'SIM_ESTADO') else 'N/A'}")
            y_position -= line_height

            # Resoluciones de este sumario
            resoluciones = historial['resoluciones'].filter(sim=sim)
            if resoluciones.exists():
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x_margin + 0.3 * inch, y_position, f"Resoluciones ({resoluciones.count()}):")
                y_position -= line_height * 0.8

                c.setFont("Helvetica", 8)
                for res in resoluciones:
                    if y_position < 1.5 * inch:
                        c.showPage()
                        y_position = height - 0.5 * inch

                    c.drawString(x_margin + 0.5 * inch, y_position, f"• Nº {res.RES_NUM} ({_format_date(res.RES_FEC)})")
                    y_position -= line_height * 0.7

                    c.drawString(x_margin + 0.7 * inch, y_position, f"Tipo: {res.get_RES_TIPO_display() if res.RES_TIPO else 'N/A'}")
                    y_position -= line_height * 0.7

                    if res.RES_TIPO_NOTIF:
                        c.drawString(x_margin + 0.7 * inch, y_position, f"Notificación: {res.RES_TIPO_NOTIF}")
                        y_position -= line_height * 0.7

                    if res.RES_FECNOT:
                        c.drawString(x_margin + 0.7 * inch, y_position, f"Fecha Notificación: {_format_date(res.RES_FECNOT)}")
                        y_position -= line_height * 0.7

                y_position -= line_height * 0.5

            # Autos TPE de este sumario
            autos_tpe = historial['autos_tpe'].filter(sim=sim)
            if autos_tpe.exists():
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x_margin + 0.3 * inch, y_position, f"Autos TPE ({autos_tpe.count()}):")
                y_position -= line_height * 0.8

                c.setFont("Helvetica", 8)
                for auto in autos_tpe:
                    if y_position < 1.5 * inch:
                        c.showPage()
                        y_position = height - 0.5 * inch

                    c.drawString(x_margin + 0.5 * inch, y_position, f"• Nº {auto.TPE_NUM or 'S/N'} ({_format_date(auto.TPE_FEC)})")
                    y_position -= line_height * 0.7

                    c.drawString(x_margin + 0.7 * inch, y_position, f"Tipo: {auto.get_TPE_TIPO_display() if auto.TPE_TIPO else 'N/A'}")
                    y_position -= line_height * 0.7

                y_position -= line_height * 0.5

            # Recursos de este sumario
            rr = historial['segundas_resoluciones'].filter(sim=sim)
            rap = historial['recursos_apelacion'].filter(sim=sim)
            autos_tsp = historial['autos_tsp'].filter(sim=sim)
            raee = historial['raees'].filter(sim=sim)

            if rr.exists() or rap.exists() or autos_tsp.exists() or raee.exists():
                if y_position < 1.5 * inch:
                    c.showPage()
                    y_position = height - 0.5 * inch

                c.setFont("Helvetica-Bold", 9)
                c.drawString(x_margin + 0.3 * inch, y_position, "Recursos y Autos Posteriores:")
                y_position -= line_height * 0.8

                c.setFont("Helvetica", 8)
                if rr.exists():
                    for res2 in rr:
                        c.drawString(x_margin + 0.5 * inch, y_position, f"• Reconsideración Nº {res2.RES_NUM or 'S/N'} ({_format_date(res2.RES_FEC)})")
                        y_position -= line_height * 0.7

                if rap.exists():
                    for apel in rap:
                        c.drawString(x_margin + 0.5 * inch, y_position, f"• Apelación Nº {apel.TSP_NUM or 'S/N'} ({_format_date(apel.TSP_FEC)})")
                        y_position -= line_height * 0.7

                if autos_tsp.exists():
                    for auto_tsp in autos_tsp:
                        c.drawString(x_margin + 0.5 * inch, y_position, f"• Auto TSP Nº {auto_tsp.TSP_NUM or 'S/N'} ({_format_date(auto_tsp.TSP_FEC)})")
                        y_position -= line_height * 0.7

                if raee.exists():
                    for r in raee:
                        c.drawString(x_margin + 0.5 * inch, y_position, f"• RAEE Nº {r.TSP_NUM or 'S/N'} ({_format_date(r.TSP_FEC)})")
                        y_position -= line_height * 0.7

            y_position -= line_height

    c.save()
    buffer.seek(0)

    fecha_export = datetime.now().strftime("%d-%m-%Y")
    filename = f"HISTORIAL_{personal.PM_CI}_{fecha_export}.pdf"

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


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
        f"Nombre: {personal.PM_NOMBRE} {personal.PM_PATERNO} {personal.PM_MATERNO or ''}",
        f"CI: {personal.PM_CI}",
        f"Grado: {personal.get_PM_GRADO_display() or 'N/A'}",
        f"Arma: {personal.get_PM_ARMA_display() or 'N/A'}",
        f"Estado: {personal.get_PM_ESTADO_display()}"
    ]

    for dato in datos_personales:
        c.drawString(x_margin + 0.2 * inch, y_position, dato)
        y_position -= line_height

    y_position -= 0.5 * line_height

    # ===== SUMARIO =====
    if sim:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y_position, f"SUMARIO: {sim.SIM_COD}")
        y_position -= line_height

        c.setFont("Helvetica", 9)
        sim_data = [
            f"Tipo: {sim.get_SIM_TIPO_display() if sim.SIM_TIPO else 'N/A'}",
            f"Objeto: {sim.SIM_OBJETO[:100]}..." if len(sim.SIM_OBJETO or '') > 100 else f"Objeto: {sim.SIM_OBJETO or 'N/A'}",
            f"Resumen: {sim.SIM_RESUM or 'N/A'}",
            f"Fecha Ingreso: {_format_date(sim.SIM_FECING)}",
            f"Estado: {sim.get_SIM_ESTADO_display() if hasattr(sim, 'get_SIM_ESTADO_display') else sim.SIM_ESTADO}"
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

                res_text = f"• {res.RES_NUM} ({_format_date(res.RES_FEC)}) — {res.get_RES_TIPO_display()}"
                c.drawString(x_margin + 0.3 * inch, y_position, res_text)
                y_position -= line_height * 0.8

                # Referencia a PDF en OneDrive
                pdf_ref = f"  Ref: RES. {res.RES_NUM} (OneDrive)"
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


def export_person_excel(request, personal_id):
    """
    Genera un Excel con 4 hojas: Personal, Sumarios, Resoluciones, Cronología.
    """
    personal, historial = _obtener_historial(personal_id)

    if not personal or not historial:
        personal = get_object_or_404(PM, pm_id=personal_id)
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
        ("CI:", str(personal.PM_CI)),
        ("Nombre:", f"{personal.PM_NOMBRE} {personal.PM_PATERNO} {personal.PM_MATERNO or ''}"),
        ("Grado:", personal.get_PM_GRADO_display() or "N/A"),
        ("Escalafón:", personal.get_PM_ESCALAFON_display() or "N/A"),
        ("Arma:", personal.get_PM_ARMA_display() or "N/A"),
        ("Especialidad:", personal.PM_ESPEC or "N/A"),
        ("Estado:", personal.get_PM_ESTADO_display()),
        ("Fecha Promoción:", _format_date(personal.PM_PROMOCION)),
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
        ws_sumarios.cell(row=row_idx, column=1, value=sim.SIM_COD)
        ws_sumarios.cell(row=row_idx, column=2, value=sim.get_SIM_TIPO_display() if sim.SIM_TIPO else "N/A")
        ws_sumarios.cell(row=row_idx, column=3, value=sim.SIM_OBJETO[:50] + "..." if len(sim.SIM_OBJETO or '') > 50 else sim.SIM_OBJETO)
        ws_sumarios.cell(row=row_idx, column=4, value=sim.SIM_RESUM or "N/A")
        ws_sumarios.cell(row=row_idx, column=5, value=_format_date(sim.SIM_FECING))
        ws_sumarios.cell(row=row_idx, column=6, value=sim.SIM_ESTADO)

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
        ws_docs.cell(row=row_idx, column=1, value=res.sim.SIM_COD)
        ws_docs.cell(row=row_idx, column=2, value="Resolución TPE (RES)")
        ws_docs.cell(row=row_idx, column=3, value=res.RES_NUM)
        ws_docs.cell(row=row_idx, column=4, value=_format_date(res.RES_FEC))
        ws_docs.cell(row=row_idx, column=5, value=res.RES_TIPO_NOTIF or "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(res.RES_FECNOT))
        row_idx += 1

    # Segundas Resoluciones (RR) — Resolucion RECONSIDERACION
    for rr in historial['segundas_resoluciones']:
        ws_docs.cell(row=row_idx, column=1, value=rr.sim.SIM_COD)
        ws_docs.cell(row=row_idx, column=2, value="Recurso Reconsideración (RR)")
        ws_docs.cell(row=row_idx, column=3, value=rr.RES_NUM or "N/A")
        ws_docs.cell(row=row_idx, column=4, value=_format_date(rr.RES_FEC))
        ws_docs.cell(row=row_idx, column=5, value=rr.RES_NOT or "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(rr.RES_FECNOT))
        row_idx += 1

    # Recursos de Apelación (RAP) — RecursoTSP APELACION
    for rap in historial['recursos_apelacion']:
        ws_docs.cell(row=row_idx, column=1, value=rap.sim.SIM_COD)
        ws_docs.cell(row=row_idx, column=2, value="Recurso Apelación (RAP)")
        ws_docs.cell(row=row_idx, column=3, value=rap.TSP_NUM or "N/A")
        ws_docs.cell(row=row_idx, column=4, value=_format_date(rap.TSP_FEC))
        ws_docs.cell(row=row_idx, column=5, value=rap.TSP_TIPO_NOTIF or "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(rap.TSP_FECNOT))
        row_idx += 1

    # RAEE — RecursoTSP ACLARACION_ENMIENDA
    for raee in historial['raees']:
        ws_docs.cell(row=row_idx, column=1, value=raee.sim.SIM_COD)
        ws_docs.cell(row=row_idx, column=2, value="Recurso RAEE")
        ws_docs.cell(row=row_idx, column=3, value=raee.TSP_NUM or "N/A")
        ws_docs.cell(row=row_idx, column=4, value=_format_date(raee.TSP_FEC))
        ws_docs.cell(row=row_idx, column=5, value=raee.TSP_TIPO_NOTIF or "N/A")
        ws_docs.cell(row=row_idx, column=6, value=_format_date(raee.TSP_FECNOT))
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
        eventos.append((sim.SIM_FECING, "Sumario Ingreso", f"SIM {sim.SIM_COD}: {sim.SIM_RESUM}"))

    for res in historial['resoluciones']:
        eventos.append((res.RES_FEC, "Resolución TPE", f"RES {res.RES_NUM}: {res.get_RES_TIPO_display()}"))

    for rap in historial['recursos_apelacion']:
        eventos.append((rap.TSP_FEC, "Apelación TSP", f"RAP {rap.TSP_NUM or 'Pendiente'}: {rap.TSP_TIPO or 'N/A'}"))

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
    excel_filename = f"HISTORIAL_{personal.PM_CI}_{fecha_export}.xlsx"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{excel_filename}"'
    return response

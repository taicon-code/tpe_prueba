# tpe_app/views/buscador_views.py
import unicodedata
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Value
from django.db.models.functions import Replace, Collate
from ..decorators import rol_requerido
from ..models import SIM, PM, AUTOTPE, AUTOTSP, Resolucion, RecursoTSP, DocumentoAdjunto, CustodiaSIM


def _normalizar(texto):
    """Quita acentos y ñ para búsqueda flexible. 'alarcón' → 'ALARCON', 'siñani' → 'SINANI'."""
    nfkd = unicodedata.normalize('NFKD', texto)
    sin_acentos = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.upper()


def _campo_sin_n(campo):
    """Reemplaza Ñ→N en el campo de BD para comparación. Los datos están en mayúsculas."""
    return Replace(campo, Value('Ñ'), Value('N'))


def _obtener_historial_completo(personal_id):
    """Obtiene el historial completo de un personal"""
    try:
        personal = PM.objects.get(pm_id=personal_id)
    except PM.DoesNotExist:
        return None

    # Obtener todos los SIM donde participa este personal
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

    return historial


def _obtener_estado_actual(personal_id):
    """Obtiene el estado actual del personal con estadísticas simplificadas"""
    historial = _obtener_historial_completo(personal_id)
    if not historial:
        return None

    return {
        'total_sumarios': historial['sumarios'].count(),
        'total_resoluciones': historial['resoluciones'].count(),
        'total_autos_tpe': historial['autos_tpe'].count(),
        'estado_actual': 'Historial disponible'
    }


def buscador_dashboard(request):
    """Dashboard para búsqueda unificada - búsqueda por código SIM, nombre, apellido paterno, materno"""

    query = request.GET.get('q', '').strip()
    personal_seleccionado = None
    historial = None
    estado = None
    resultados_pm = []
    resultados_sim = []

    if query:
        # Normalizamos el query: quitamos tildes y ñ → 'alarcón'→'ALARCON', 'siñani'→'SINANI'
        q_norm = _normalizar(query)

        # Buscamos con anotaciones que normalizan el campo en la BD (Ñ→N),
        # y usamos collation accent-insensitive para que á=a, é=e, etc.
        resultados_pm = list(
            PM.objects.annotate(
                pat_norm=Collate(_campo_sin_n('PM_PATERNO'), 'utf8mb4_general_ci'),
                nom_norm=Collate(_campo_sin_n('PM_NOMBRE'),  'utf8mb4_general_ci'),
                mat_norm=Collate(_campo_sin_n('PM_MATERNO'), 'utf8mb4_general_ci'),
            ).filter(
                Q(pat_norm__icontains=q_norm) |
                Q(nom_norm__icontains=q_norm) |
                Q(mat_norm__icontains=q_norm)
            ).distinct()[:20]
        )

        resultados_sim = list(
            SIM.objects.filter(
                Q(SIM_COD__icontains=query) |
                Q(SIM_RESUM__icontains=query) |
                Q(SIM_OBJETO__icontains=query)
            ).prefetch_related('abogados', 'militares').distinct()[:20]
        )

        # Si hay exactamente 1 PM, mostrar su historial completo
        if len(resultados_pm) == 1:
            personal_seleccionado = resultados_pm[0]
            historial = _obtener_historial_completo(personal_seleccionado.pm_id)
            estado = _obtener_estado_actual(personal_seleccionado.pm_id)

    context = {
        'query': query,
        'resultados_pm': resultados_pm,
        'resultados_sim': resultados_sim,
        'total_pm': len(resultados_pm),
        'total_sim': len(resultados_sim),
        'personal_seleccionado': personal_seleccionado,
        'historial': historial,
        'estado': estado,
    }
    return render(request, 'tpe_app/buscador/dashboard_buscador.html', context)


def detalles_sim(request, sim_id):
    """Vista detallada de un SIM: militares, resoluciones, autos, custodia (solo Admin2), etc."""
    from ..decorators import rol_requerido

    sim = get_object_or_404(SIM, id=sim_id)

    # Obtener todos los militares del SIM
    militares = sim.militares.all()

    # Obtener todos los actuados del SIM
    resoluciones = Resolucion.objects.filter(sim=sim).select_related('abog', 'pm')
    autos_tpe = AUTOTPE.objects.filter(sim=sim).select_related('abog')
    autos_tsp = AUTOTSP.objects.filter(sim=sim)
    recursos_tsp = RecursoTSP.objects.filter(sim=sim).select_related('abog')

    # Obtener historial de custodia (trazabilidad) - SOLO para Admin2
    custodia_historial = None
    custodia_actual = None
    es_admin2 = hasattr(request.user, 'perfilusuario') and request.user.perfilusuario.rol == 'ADMIN2_ARCHIVO'

    if es_admin2:
        custodia_historial = CustodiaSIM.objects.filter(sim=sim).select_related('abog').order_by('fecha_recepcion')
        custodia_actual = CustodiaSIM.objects.filter(sim=sim, estado='RECIBIDA_CONFORME').select_related('abog').first()

    context = {
        'sim': sim,
        'militares': militares,
        'resoluciones': resoluciones,
        'autos_tpe': autos_tpe,
        'autos_tsp': autos_tsp,
        'recursos_tsp': recursos_tsp,
        'custodia_historial': custodia_historial,
        'custodia_actual': custodia_actual,
        'es_admin2': es_admin2,
    }
    return render(request, 'tpe_app/buscador/detalles_sim.html', context)


def upload_foto_pm(request, pm_id):
    """Subir o reemplazar la foto de un Personal Militar"""
    pm = get_object_or_404(PM, pk=pm_id)

    if request.method == 'POST':
        foto = request.FILES.get('foto')
        if foto:
            # Validar que sea imagen
            content_type = foto.content_type or ''
            if not content_type.startswith('image/'):
                messages.error(request, '❌ El archivo debe ser una imagen (JPG, PNG, etc.)')
            else:
                # Eliminar foto anterior si existe
                if pm.PM_FOTO:
                    pm.PM_FOTO.delete(save=False)
                pm.PM_FOTO = foto
                pm.save(update_fields=['PM_FOTO'])
                messages.success(request, f'✅ Foto actualizada para {pm.PM_NOMBRE} {pm.PM_PATERNO}')
        else:
            messages.error(request, '❌ No se seleccionó ningún archivo')

    # Volver al buscador con la misma búsqueda si venía de ahí
    referer = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if 'buscador' in referer or 'q=' in referer:
        return redirect(referer)
    return redirect('buscador_dashboard')


def export_custodia_pdf(request, sim_id):
    """Descargar PDF del historial de custodia de un SIM (Solo Admin2)"""
    from django.http import HttpResponse
    from django.utils import timezone as tz
    from reportlab.lib.pagesizes import A4
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

    # Verificar que sea Admin2
    if not (hasattr(request.user, 'perfilusuario') and request.user.perfilusuario.rol == 'ADMIN2_ARCHIVO'):
        messages.error(request, '❌ No tienes permiso para descargar este archivo')
        return redirect('admin2_dashboard')

    sim = get_object_or_404(SIM, id=sim_id)
    custodia_historial = CustodiaSIM.objects.filter(sim=sim).select_related('abog').order_by('fecha_recepcion')

    # Crear PDF en orientación vertical (portrait)
    response = HttpResponse(content_type='application/pdf')
    now_local = tz.localtime(tz.now())
    response['Content-Disposition'] = f'attachment; filename="custodia_{sim.SIM_COD}_{now_local.strftime("%d%m%Y")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.5*inch, rightMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()

    # Título (sin emoji para evitar caracteres mezclados en reportlab)
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=13,
        textColor=colors.HexColor('#185FA5'),
        spaceAfter=10,
        alignment=1
    )
    story.append(Paragraph(f'Historial de Custodia de Carpeta - {sim.SIM_COD}', title_style))
    story.append(Spacer(1, 0.15*inch))

    # Información del SIM — ancho ajustado a portrait (A4 usable ≈ 7.17 in)
    info_data = [
        ['Codigo', sim.SIM_COD],
        ['Tipo', sim.get_SIM_TIPO_display()],
        ['Estado', sim.get_SIM_ESTADO_display()],
        ['Ingreso', sim.SIM_FECING.strftime('%d/%m/%Y') if sim.SIM_FECING else '-'],
    ]
    info_table = Table(info_data, colWidths=[1.4*inch, 5.77*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))

    # Historial de custodia
    heading_style = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#185FA5'),
        spaceAfter=6,
    )
    story.append(Paragraph('Movimientos de Custodia', heading_style))

    # Estilo para celdas con texto largo (permite salto de línea automático)
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName=FONT_NORMAL,
        fontSize=8,
        leading=10,
        wordWrap='CJK',
    )

    # Anchos para portrait A4 (usable ≈ 18.46 cm)
    # Fecha Recep | Custodio | Abogado | Estado | Fecha Entrega | Observacion
    col_widths = [2.2*cm, 3.7*cm, 2.5*cm, 3.2*cm, 2.2*cm, 4.66*cm]

    if custodia_historial:
        custodia_data = [
            ['Fecha Recep.', 'Custodio', 'Abogado', 'Estado', 'Fecha Entrega', 'Observacion']
        ]

        for custodia in custodia_historial:
            observacion = custodia.observacion if custodia.observacion else '-'

            custodia_data.append([
                tz.localtime(custodia.fecha_recepcion).strftime('%d/%m/%Y\n%H:%M'),
                custodia.get_tipo_custodio_display(),
                custodia.abog.AB_PATERNO if custodia.abog else '-',
                custodia.get_estado_display(),
                tz.localtime(custodia.fecha_entrega).strftime('%d/%m/%Y\n%H:%M') if custodia.fecha_entrega else 'Activa',
                Paragraph(observacion, cell_style),
            ])

        custodia_table = Table(custodia_data, colWidths=col_widths)

        custodia_table.setStyle(TableStyle([
            # Cabecera: fondo blanco, texto negro en negrita (sin relleno azul)
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 0), (-1, 0), 7),
            # Línea inferior de la cabecera más gruesa para separar visualmente
            ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor('#185FA5')),
            # Filas de datos
            ('ALIGN', (0, 1), (4, -1), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('FONTNAME', (0, 1), (-1, -1), FONT_NORMAL),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))

        story.append(custodia_table)
    else:
        story.append(Paragraph('<i>No hay movimientos de custodia registrados.</i>', styles['Normal']))

    # Pie de página
    story.append(Spacer(1, 0.25*inch))
    pie_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#999999'),
        alignment=0,
    )
    generated_time = now_local.strftime('%d/%m/%Y %H:%M:%S')
    story.append(Paragraph(f'Generado: {generated_time}', pie_style))

    doc.build(story)
    return response

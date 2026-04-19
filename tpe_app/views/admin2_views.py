# tpe_app/views/admin2_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from ..decorators import rol_requerido
from ..models import SIM, ABOG, CustodiaSIM, DocumentoAdjunto, Resolucion, ABOG_SIM


# ============================================================
# DASHBOARD ADMIN2 (ARCHIVO SIM)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_dashboard(request):
    """Dashboard para Admin2 - Gestión de custodia de carpetas"""

    # Carpetas actualmente en poder de Admin2: obtener solo la custodia actual de cada SIM
    # Estrategia: obtener todos los SIM que tienen custodia en Admin2, luego filtrar por su custodio actual
    sims_con_custodia_admin2 = SIM.objects.filter(
        custodias__tipo_custodio='ADMIN2_ARCHIVO',
        custodias__estado='ACTIVA'
    ).distinct().prefetch_related('custodias', 'militares', 'abogados')

    # Filtrar en Python para obtener solo la custodia actual de cada SIM que cumpla las condiciones
    carpetas_en_poder = []
    for sim in sims_con_custodia_admin2:
        custodia_actual = sim.custodio_actual()
        if custodia_actual and custodia_actual.tipo_custodio == 'ADMIN2_ARCHIVO' and custodia_actual.estado == 'ACTIVA':
            # Abogados de primera instancia (ABOG_SIM)
            abog_primera = ABOG_SIM.objects.filter(sim=sim).select_related('abog')
            custodia_actual.abog_primera_list = [a.abog for a in abog_primera]

            # Abogado de RR si existe
            rr = Resolucion.objects.filter(
                sim=sim, RES_INSTANCIA='RECONSIDERACION', abog__isnull=False
            ).select_related('abog').last()
            custodia_actual.abog_rr = rr.abog if rr else None

            carpetas_en_poder.append(custodia_actual)

    # Ordenar por fecha de recepción descendente
    carpetas_en_poder.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # Carpetas entregadas pendientes de confirmar recepción (solo la custodia actual de cada SIM)
    sims_con_custodia_pend = SIM.objects.filter(
        custodias__tipo_custodio='ADMIN2_ARCHIVO',
        custodias__estado='PENDIENTE_CONFIRMACION'
    ).distinct().prefetch_related('custodias', 'militares')

    carpetas_pendientes = []
    for sim in sims_con_custodia_pend:
        custodia_actual = sim.custodio_actual()
        if custodia_actual and custodia_actual.tipo_custodio == 'ADMIN2_ARCHIVO' and custodia_actual.estado == 'PENDIENTE_CONFIRMACION':
            carpetas_pendientes.append(custodia_actual)

    carpetas_pendientes.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # Carpetas prestadas (en poder de otros, aún activas) - solo la custodia actual de cada SIM
    sims_con_custodia_prest = SIM.objects.filter(
        custodias__fecha_entrega__isnull=True
    ).exclude(
        custodias__tipo_custodio__in=['ADMIN2_ARCHIVO', 'ARCHIVO']
    ).distinct().prefetch_related('custodias', 'militares')

    carpetas_prestadas = []
    for sim in sims_con_custodia_prest:
        custodia_actual = sim.custodio_actual()
        if custodia_actual and custodia_actual.tipo_custodio not in ['ADMIN2_ARCHIVO', 'ARCHIVO']:
            carpetas_prestadas.append(custodia_actual)

    carpetas_prestadas.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # Filtro de historial por código SIM o militar
    from django.db.models import Q

    query = (request.GET.get('q') or '').strip()
    historial_sim = None

    if query:
        try:
            # Buscar en SIM_COD, militares paterno/materno/nombre
            filtros_q = (
                Q(SIM_COD__icontains=query) |
                Q(militares__PM_PATERNO__icontains=query) |
                Q(militares__PM_MATERNO__icontains=query) |
                Q(militares__PM_NOMBRE__icontains=query)
            )
            sims = SIM.objects.filter(filtros_q).distinct()
            historial_sim = CustodiaSIM.objects.filter(sim__in=sims).select_related('abog').order_by('fecha_recepcion')
        except Exception:
            historial_sim = []

    context = {
        'carpetas_en_poder': carpetas_en_poder,
        'total_en_poder': len(carpetas_en_poder),
        'carpetas_pendientes': carpetas_pendientes,
        'total_pendientes': len(carpetas_pendientes),
        'carpetas_prestadas': carpetas_prestadas,
        'total_prestadas': len(carpetas_prestadas),
        'query': query,
        'historial_sim': historial_sim,
    }

    return render(request, 'tpe_app/admin2_dashboard.html', context)


# ============================================================
# ADMIN2: Gestión de custodia y entregas (v3.1+)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_entregar_carpeta(request, sim_id):
    """Admin2 entrega la carpeta a un abogado (RR, RAP, ejecutoria, etc.)"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que la carpeta esté en poder de Admin2
    if not custodio_actual or custodio_actual.tipo_custodio != 'ADMIN2_ARCHIVO':
        messages.error(request, "❌ La carpeta no está registrada en poder de Archivo SIM")
        return redirect('admin2_dashboard')

    if request.method == 'POST':
        abog_id = request.POST.get('abogado')
        tipo_custodio = request.POST.get('tipo_custodio')
        motivo = request.POST.get('motivo')
        observacion = request.POST.get('observacion', '').strip()
        nro_oficio = request.POST.get('nro_oficio', '').strip() if tipo_custodio == 'TSP' else None
        fecha_oficio_str = request.POST.get('fecha_oficio') if tipo_custodio == 'TSP' else None

        if not tipo_custodio:
            messages.error(request, '❌ Debe seleccionar tipo de custodia')
        elif tipo_custodio != 'ARCHIVO' and not abog_id:
            messages.error(request, '❌ Debe seleccionar abogado (excepto para Archivado)')
        else:
            try:
                abog = ABOG.objects.get(pk=abog_id) if abog_id else None
                fecha_oficio = None
                if fecha_oficio_str:
                    fecha_oficio = datetime.strptime(fecha_oficio_str, '%Y-%m-%d').date()

                with transaction.atomic():
                    # Cerrar custodia actual (Admin2)
                    custodio_actual.fecha_entrega = timezone.now()
                    custodio_actual.save()

                    # Crear nueva custodia (pendiente de confirmación del abogado si es entrega a abogado)
                    estado_custodia = 'PENDIENTE_CONFIRMACION' if tipo_custodio.startswith('ABOG_') else 'ACTIVA'
                    custodia_nueva = CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio=tipo_custodio,
                        abog=abog,
                        usuario=request.user,
                        observacion=observacion or None,
                        motivo=motivo,
                        nro_oficio=nro_oficio,
                        fecha_oficio=fecha_oficio,
                        estado=estado_custodia
                    )

                    messages.success(request, f'✅ Carpeta entregada correctamente')
                    return redirect('admin2_dashboard')
            except ABOG.DoesNotExist:
                messages.error(request, '❌ Abogado no encontrado')
            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')

    # Obtener abogados disponibles
    abogados = ABOG.objects.all().order_by('AB_PATERNO')

    # Tipos de custodia disponibles para entregar
    TIPOS_CUSTODIA = [
        ('ABOG_ASESOR', 'Abogado 1 - Asesor (1ra Resolución)'),
        ('ABOG_RR', 'Abogado 2 - Recurso de Reconsideración'),
        ('ABOG_AUTOS', 'Abogado 3 - Autos/Ejecutoria'),
        ('ADMIN3', 'Admin3 - Notificador'),
        ('TSP', 'Tribunal Supremo Policial (TSP)'),
        ('ARCHIVO', 'Archivado / Concluido'),
    ]

    # Motivos disponibles
    MOTIVOS = [
        ('AGENDA', 'Para agenda del tribunal'),
        ('REVISION', 'Revisión del abogado'),
        ('NOTIFICACION', 'Para notificación'),
        ('APELACION_TSP', 'Elevado al TSP'),
        ('ARCHIVO', 'Archivado / Concluido'),
    ]

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
        'abogados': abogados,
        'tipos_custodia': TIPOS_CUSTODIA,
        'motivos': MOTIVOS,
    }

    return render(request, 'tpe_app/admin2/entregar_carpeta.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_recibir_carpeta(request, sim_id):
    """Admin2 recibe la carpeta devuelta por un abogado"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que la carpeta esté en poder de un abogado
    if not custodio_actual or not custodio_actual.abog:
        messages.error(request, "❌ La carpeta no está en poder de un abogado")
        return redirect('admin2_dashboard')

    if request.method == 'POST':
        observacion = request.POST.get('observacion', '').strip()

        try:
            with transaction.atomic():
                # Cerrar custodia del abogado
                custodio_actual.fecha_entrega = timezone.now()
                custodio_actual.save()

                # Crear nueva custodia con Admin2
                CustodiaSIM.objects.create(
                    sim=sim,
                    tipo_custodio='ADMIN2_ARCHIVO',
                    usuario=request.user,
                    observacion=observacion or None
                )

                messages.success(
                    request,
                    f'✅ Carpeta recibida de {custodio_actual.abog.AB_GRADO} {custodio_actual.abog.AB_PATERNO}'
                )
                return redirect('admin2_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
    }

    return render(request, 'tpe_app/admin2/recibir_carpeta.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_confirmar_recepcion(request, sim_id):
    """Admin2 confirma que recibió la carpeta conforme (entregada por abogado)"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que hay una custodia pendiente de confirmación
    if (not custodio_actual or
        custodio_actual.tipo_custodio != 'ADMIN2_ARCHIVO' or
        custodio_actual.estado != 'PENDIENTE_CONFIRMACION'):
        messages.error(request, "❌ No hay recepción pendiente para este sumario")
        return redirect('admin2_dashboard')

    if request.method == 'POST':
        observacion = request.POST.get('observacion', '').strip()

        try:
            with transaction.atomic():
                # Cambiar estado a ACTIVA
                custodio_actual.estado = 'ACTIVA'
                if observacion:
                    custodia_obs = (custodio_actual.observacion or '') + f' | Recibido conforme: {observacion}'
                    custodio_actual.observacion = custodia_obs
                custodio_actual.save()

                messages.success(
                    request,
                    f'✅ Carpeta {sim.SIM_COD} recibida conforme y en su poder'
                )
                return redirect('admin2_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
    }

    return render(request, 'tpe_app/admin2/confirmar_recepcion.html', context)


# ============================================================
# SUBIR PDF DE RESOLUCIONES (RES)
# ============================================================

@rol_requerido('AYUDANTE', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def subir_pdf_res(request, res_id):
    """Sube PDF de una Resolución (RES) - Ayudante o Administrativos específicos"""

    res = get_object_or_404(Resolucion, pk=res_id)

    if request.method == 'POST':
        archivo_pdf = request.FILES.get('archivo_pdf')

        if not archivo_pdf:
            messages.error(request, '❌ Selecciona un archivo PDF')
            return redirect('subir_pdf_res', res_id=res.pk)

        if not archivo_pdf.name.lower().endswith('.pdf'):
            messages.error(request, '❌ Solo se permiten archivos PDF')
            return redirect('subir_pdf_res', res_id=res.pk)

        try:
            with transaction.atomic():
                # Eliminar PDF anterior si existe
                DocumentoAdjunto.objects.filter(
                    DOC_TABLA='resolucion',
                    DOC_ID_REG=res.pk
                ).delete()

                # Crear nuevo documento
                DocumentoAdjunto.objects.create(
                    DOC_TABLA='resolucion',
                    DOC_ID_REG=res.pk,
                    DOC_TIPO='resolucion',
                    DOC_RUTA=archivo_pdf,
                    DOC_NOMBRE=f'RES {res.RES_NUM} - {res.pm.PM_GRADO} {res.pm.PM_PATERNO}'
                )

                messages.success(
                    request,
                    f'✅ PDF de la Resolución {res.RES_NUM} subido correctamente'
                )
                return redirect('administrativo_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error al subir PDF: {str(e)}')

    # Verificar si ya tiene PDF
    pdf_existente = DocumentoAdjunto.objects.filter(
        DOC_TABLA='resolucion',
        DOC_ID_REG=res.pk
    ).first()

    context = {
        'res': res,
        'pdf_existente': pdf_existente,
    }

    return render(request, 'tpe_app/administrativo/subir_pdf_res.html', context)


# ============================================================
# VER HISTORIAL DE CUSTODIA DE UN SIM
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def ver_historial_custodia_sim(request, sim_id):
    """Ver dónde está un SIM actualmente y su historial de custodia"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodia_actual = sim.custodio_actual()

    # Obtener historial completo de custodia
    historial = list(CustodiaSIM.objects.filter(sim=sim).select_related('abog', 'usuario').order_by('fecha_recepcion'))

    # Enriquecer datos de historial con nombre legible del custodio
    TIPO_CUSTODIO_DISPLAY = {
        'ADMIN1': 'Admin1 - Agendador',
        'ADMIN2_ARCHIVO': 'Admin2 - Archivo SIM',
        'ADMIN3': 'Admin3 - Notificador',
        'ABOG_ASESOR': 'Abogado 1 - Asesor',
        'ABOG_RR': 'Abogado 2 - RR',
        'ABOG_AUTOS': 'Abogado 3 - Autos',
        'TSP': 'Tribunal Supremo Policial',
        'ARCHIVO': 'Archivado / Concluido',
    }

    for custodia in historial:
        custodia.tipo_custodio_display = TIPO_CUSTODIO_DISPLAY.get(custodia.tipo_custodio, custodia.tipo_custodio)

    if custodia_actual:
        custodia_actual.tipo_custodio_display = TIPO_CUSTODIO_DISPLAY.get(custodia_actual.tipo_custodio, custodia_actual.tipo_custodio)

    context = {
        'sim': sim,
        'custodia_actual': custodia_actual,
        'historial': historial,
    }

    return render(request, 'tpe_app/ver_historial_custodia.html', context)

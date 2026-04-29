# tpe_app/views/admin2_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from ..decorators import rol_requerido
from ..models import SIM, PM, CustodiaSIM, DocumentoAdjunto, Resolucion, ABOG_SIM, AUTOTPE


# ============================================================
# DASHBOARD ADMIN2 (ARCHIVO SIM)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_dashboard(request):
    """Dashboard para Admin2 - Gestión de custodia de carpetas

    Garantiza que TODOS los SIM registrados aparezcan en ALGUNA sección del dashboard.
    Cada SIM se muestra según su custodia actual.
    """

    # ✅ 1. PENDIENTES DE CONFIRMAR RECEPCIÓN (Admin2 recibió de vuelta)
    # Son custodias ADMIN2_ARCHIVO en estado PENDIENTE_CONFIRMACION
    # Esto ocurre cuando Admin2 recibe un sumario de vuelta de un abogado/vocal
    custodias_admin2_pendientes = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        estado='PENDIENTE_CONFIRMACION',
        fecha_entrega__isnull=True
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_admin2_pendientes = []
    for custodia in custodias_admin2_pendientes:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            carpetas_admin2_pendientes.append(custodia)

    carpetas_admin2_pendientes.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 2. CARPETAS EN PODER DE ADMIN2 (Activas)
    # Son custodias ADMIN2_ARCHIVO en estado ACTIVA (excepto ejecutoria)
    custodias_admin2_activas = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True
    ).exclude(
        motivo='EJECUTORIA'  # Las de ejecutoria van en otra sección
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_en_poder = []
    for custodia in custodias_admin2_activas:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            # Abogados de primera instancia (ABOG_SIM)
            abog_primera = ABOG_SIM.objects.filter(sim=custodia.sim).select_related('abogado')
            custodia.abog_primera_list = [a.abogado for a in abog_primera]

            # Abogado de RR si existe
            rr = Resolucion.objects.filter(
                sim=custodia.sim, instancia='RECONSIDERACION', abogado__isnull=False
            ).select_related('abogado').last()
            custodia.abog_rr = rr.abogado if rr else None

            carpetas_en_poder.append(custodia)

    carpetas_en_poder.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 3. PARA EJECUTORIA
    # Son custodias ADMIN2_ARCHIVO con motivo='EJECUTORIA'
    custodias_ejecutoria = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        motivo='EJECUTORIA',
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True
    ).select_related('sim', 'abogado_destino').order_by('-fecha_recepcion')

    para_ejecutoria = []
    for custodia in custodias_ejecutoria:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            para_ejecutoria.append(custodia)

    # ✅ 4. PENDIENTES DE CONFIRMACIÓN (Abogados/Vocales)
    # Son custodias de otros tipos en estado PENDIENTE_CONFIRMACION
    custodias_otros_pendientes = CustodiaSIM.objects.filter(
        estado='PENDIENTE_CONFIRMACION',
        fecha_entrega__isnull=True
    ).exclude(
        tipo_custodio='ADMIN2_ARCHIVO'
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_pendientes = []
    for custodia in custodias_otros_pendientes:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            carpetas_pendientes.append(custodia)

    carpetas_pendientes.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 5. CARPETAS PRESTADAS (En poder de abogados/vocales/otros)
    # Son custodias de otros tipos en estado ACTIVA
    custodias_otros_activas = CustodiaSIM.objects.filter(
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True
    ).exclude(
        tipo_custodio__in=['ADMIN2_ARCHIVO', 'ARCHIVO']
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_prestadas = []
    for custodia in custodias_otros_activas:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            carpetas_prestadas.append(custodia)

    carpetas_prestadas.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 6. PENDIENTES DE ENTREGAR
    # Son SIM asignados a abogados pero sin custodia activa aún
    sims_asignados = SIM.objects.filter(
        abogados__isnull=False
    ).exclude(
        custodias__estado='RECIBIDA_CONFORME'
    ).exclude(
        custodias__estado='PENDIENTE_CONFIRMACION'
    ).distinct().prefetch_related('militares', 'abogados')

    sims_pendientes_entregar = []
    for sim in sims_asignados:
        # Verificar que no haya custodia activa ni pendiente
        has_active_custody = sim.custodias.filter(
            estado__in=['RECIBIDA_CONFORME', 'PENDIENTE_CONFIRMACION']
        ).exists()

        # No incluir archivados/concluidos
        if not has_active_custody and sim.estado not in ['PROCESO_CONCLUIDO_TPE', 'PROCESO_EJECUTADO']:
            abog_primera = ABOG_SIM.objects.filter(sim=sim).select_related('abogado')
            sim.abogados_asignados = [a.abogado for a in abog_primera]
            sims_pendientes_entregar.append(sim)

    # Ordenar por fecha de ingreso descendente
    sims_pendientes_entregar.sort(key=lambda x: x.fecha_ingreso if x.fecha_ingreso else timezone.now(), reverse=True)

    # ✅ 7. PENDIENTE ARCHIVO SPRODA (Admin1 ordenó el archivo final)
    sims_pendiente_archivo = list(
        SIM.objects.filter(fase='PENDIENTE_ARCHIVO')
        .prefetch_related('militares')
        .order_by('-fecha_ingreso')
    )
    for sim_pa in sims_pendiente_archivo:
        sim_pa.auto_ejecutoria = AUTOTPE.objects.filter(
            sim=sim_pa, tipo='AUTO_EJECUTORIA'
        ).order_by('-fecha').first()

    # ✅ 8. PROCESO_CONCLUIDO_TPE con memorándum pendiente de retorno
    sims_memo_pendiente = list(
        SIM.objects.filter(estado='PROCESO_CONCLUIDO_TPE')
        .prefetch_related('militares')
        .order_by('-fecha_ingreso')
    )
    sims_con_memo_pendiente = []
    for sim_m in sims_memo_pendiente:
        auto = AUTOTPE.objects.filter(
            sim=sim_m, tipo='AUTO_EJECUTORIA',
            memorandum__isnull=False,
            memorandum__fecha_entrega__isnull=True,
        ).select_related('memorandum').first()
        if auto:
            sim_m.auto_ejecutoria = auto
            sims_con_memo_pendiente.append(sim_m)

    # Filtro de historial por código SIM o militar
    from django.db.models import Q

    query = (request.GET.get('q') or '').strip()
    historial_sim = None

    if query:
        try:
            # Buscar en codigo, militares paterno/materno/nombre
            filtros_q = (
                Q(codigo__icontains=query) |
                Q(militares__paterno__icontains=query) |
                Q(militares__materno__icontains=query) |
                Q(militares__nombre__icontains=query)
            )
            sims = SIM.objects.filter(filtros_q).distinct()
            historial_sim = CustodiaSIM.objects.filter(sim__in=sims).select_related('abogado').order_by('fecha_recepcion')
        except Exception:
            historial_sim = []

    context = {
        'carpetas_admin2_pendientes': carpetas_admin2_pendientes,
        'total_admin2_pendientes': len(carpetas_admin2_pendientes),
        'carpetas_en_poder': carpetas_en_poder,
        'total_en_poder': len(carpetas_en_poder),
        'carpetas_pendientes': carpetas_pendientes,
        'total_pendientes': len(carpetas_pendientes),
        'carpetas_prestadas': carpetas_prestadas,
        'total_prestadas': len(carpetas_prestadas),
        'para_ejecutoria': para_ejecutoria,
        'total_ejecutoria': len(para_ejecutoria),
        'sims_pendientes_entregar': sims_pendientes_entregar,
        'total_sin_entregar': len(sims_pendientes_entregar),
        'sims_pendiente_archivo': sims_pendiente_archivo,
        'total_pendiente_archivo': len(sims_pendiente_archivo),
        'sims_con_memo_pendiente': sims_con_memo_pendiente,
        'total_memo_pendiente': len(sims_con_memo_pendiente),
        'query': query,
        'historial_sim': historial_sim,
    }

    return render(request, 'tpe_app/admin2/admin2_dashboard.html', context)


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
                abog = PM.objects.filter(
                    pk=abog_id,
                    perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO']
                ).first() if abog_id else None
                if abog_id and not abog:
                    messages.error(request, '❌ El personal seleccionado no tiene rol de abogado en el sistema.')
                    return redirect('admin2_dashboard')
                fecha_oficio = None
                if fecha_oficio_str:
                    fecha_oficio = datetime.strptime(fecha_oficio_str, '%Y-%m-%d').date()

                with transaction.atomic():
                    # Cerrar custodia actual (Admin2)
                    custodio_actual.fecha_entrega = timezone.now()
                    custodio_actual.save()

                    # Crear nueva custodia (pendiente de confirmación del abogado si es entrega a abogado)
                    estado_custodia = 'PENDIENTE_CONFIRMACION' if tipo_custodio.startswith('ABOG_') else 'RECIBIDA_CONFORME'
                    custodia_nueva = CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio=tipo_custodio,
                        abogado=abog,
                        usuario=request.user,
                        observacion=observacion or None,
                        motivo=motivo,
                        nro_oficio=nro_oficio,
                        fecha_oficio=fecha_oficio,
                        estado=estado_custodia
                    )

                    messages.success(request, f'✅ Carpeta entregada correctamente')
                    return redirect('admin2_dashboard')
            except PM.DoesNotExist:
                messages.error(request, '❌ Abogado no encontrado')
            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')

    # Obtener abogados disponibles
    abogados = PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno')

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
        ('EJECUTORIA', 'Para ejecutoria/cumplimiento'),
        ('ARCHIVO', 'Archivado / Concluido'),
    ]

    # Detectar si hay una orden de ejecutoria previa
    orden_ejecutoria = CustodiaSIM.objects.filter(
        sim=sim,
        motivo='EJECUTORIA',
        fecha_entrega__isnull=True
    ).select_related('abog_destino').first()

    # Pre-llenar si hay orden de ejecutoria
    pre_llenar_tipo = None
    pre_llenar_abog = None
    mensaje_orden = None

    if orden_ejecutoria and orden_ejecutoria.abogado_destino:
        pre_llenar_tipo = 'ABOG_AUTOS'
        pre_llenar_abog = orden_ejecutoria.abogado_destino.pk
        mensaje_orden = f'Orden: Entregar a ABOG2 ({orden_ejecutoria.abogado_destino.paterno}) para Ejecutoria'

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
        'abogados': abogados,
        'tipos_custodia': TIPOS_CUSTODIA,
        'motivos': MOTIVOS,
        'orden_ejecutoria': orden_ejecutoria,
        'mensaje_orden': mensaje_orden,
        'pre_llenar_tipo': pre_llenar_tipo,
        'pre_llenar_abog': pre_llenar_abog,
    }

    return render(request, 'tpe_app/admin2/entregar_carpeta.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_recibir_carpeta(request, sim_id):
    """Admin2 recibe la carpeta devuelta por un abogado"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que la carpeta esté en poder de un abogado
    if not custodio_actual or not custodio_actual.abogado:
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
                    abogado=custodio_actual.abogado,
                    usuario=request.user,
                    observacion=observacion or None
                )

                messages.success(
                    request,
                    f'✅ Carpeta recibida de {custodio_actual.abogado.grado} {custodio_actual.abogado.paterno}'
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
                # Cambiar estado a RECIBIDA_CONFORME
                custodio_actual.estado = 'RECIBIDA_CONFORME'
                if observacion:
                    custodia_obs = (custodio_actual.observacion or '') + f' | Recibido conforme: {observacion}'
                    custodio_actual.observacion = custodia_obs
                custodio_actual.save()

                messages.success(
                    request,
                    f'✅ Carpeta {sim.codigo} recibida conforme y en su poder'
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

        next_url = request.POST.get('next', '').strip()
        try:
            with transaction.atomic():
                # Eliminar PDF anterior si existe
                DocumentoAdjunto.objects.filter(
                    resolucion_id=res.pk
                ).delete()

                # Crear nuevo documento
                DocumentoAdjunto.objects.create(
                    resolucion=res,
                    tipo='resolucion',
                    archivo=archivo_pdf,
                    nombre=f'RES {res.numero} - {res.pm.grado} {res.pm.paterno}' if res.pm else f'RES {res.numero}'
                )

                messages.success(
                    request,
                    f'✅ PDF de la Resolución {res.numero} subido correctamente'
                )
                if next_url:
                    return redirect(next_url)
                return redirect('subir_pdf_res', res_id=res.pk)
        except Exception as e:
            messages.error(request, f'❌ Error al subir PDF: {str(e)}')

    # Verificar si ya tiene PDF
    pdf_existente = DocumentoAdjunto.objects.filter(
        resolucion_id=res.pk
    ).first()

    context = {
        'res': res,
        'pdf_existente': pdf_existente,
    }

    return render(request, 'tpe_app/admin2/subir_pdf_res.html', context)


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
        'ADMIN1_AGENDADOR': 'Agendador',
        'ADMIN2_ARCHIVO': 'Archivo del Tribunal',
        'ADMIN3_NOTIFICADOR': 'Notificador',
        'ABOG_ASESOR': 'Abogado Asesor',
        'ABOG_RR': 'Abogado (Reconsideración)',
        'ABOG_AUTOS': 'Abogado (Autos)',
        'VOCAL_SESION': 'Secretario de Actas',
        'TSP': 'Tribunal Supremo Policial',
        'ARCHIVO': 'Archivo Permanente',
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

    return render(request, 'tpe_app/admin2/ver_historial_custodia.html', context)


# ============================================================
# ADMIN2: Confirmar Archivo Final a SPRODA
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_confirmar_archivo_sproda(request, sim_id):
    """Admin2 confirma que realizó el archivo final (SPRODA + copias a secciones si corresponde).
    Transiciona el SIM a CONCLUIDO → PROCESO_CONCLUIDO_TPE."""

    sim = get_object_or_404(SIM, pk=sim_id, fase='PENDIENTE_ARCHIVO')

    if request.method == 'POST':
        observacion = request.POST.get('observacion', '').strip()
        with transaction.atomic():
            sim.fase = 'CONCLUIDO'
            sim.save()
            # Registrar en historial de custodia
            CustodiaSIM.objects.create(
                sim=sim,
                tipo_custodio='ARCHIVO',
                usuario=request.user,
                motivo='ARCHIVO',
                observacion=observacion or 'Archivo final SPRODA',
                estado='RECIBIDA_CONFORME',
            )
        messages.success(
            request,
            f"✅ SIM {sim.codigo} archivado correctamente. Estado: Proceso Concluido (TPE)."
        )
        return redirect('admin2_dashboard')

    auto_ej = AUTOTPE.objects.filter(
        sim=sim, tipo='AUTO_EJECUTORIA'
    ).order_by('-fecha').first()

    return render(request, 'tpe_app/admin2/confirmar_archivo_sproda.html', {
        'sim': sim,
        'auto': auto_ej,
        'militares': sim.militares.all(),
    })


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_registrar_retorno_memo(request, auto_id):
    """Admin2 registra el retorno del memorándum del Auto de Ejecutoria.
    Cuando el memo retorna, el SIM pasa a PROCESO_EJECUTADO."""

    auto = get_object_or_404(AUTOTPE, id=auto_id, tipo='AUTO_EJECUTORIA')

    if request.method == 'POST':
        fecha_entrega = request.POST.get('fecha_entrega')
        if not fecha_entrega:
            messages.error(request, "Debe ingresar la fecha de retorno del memorándum.")
        else:
            from datetime import datetime as dt
            try:
                fecha = dt.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Formato de fecha inválido.")
                fecha = None

            if fecha:
                with transaction.atomic():
                    auto.memorandum.fecha_entrega = fecha
                    auto.memorandum.save(update_fields=['fecha_entrega'])
                    sim = auto.sim
                    sim.fase = 'MEMORANDUM_RETORNADO'
                    sim.save()
                messages.success(
                    request,
                    f"✅ Retorno de memorándum registrado. SIM {sim.codigo}: Proceso Ejecutado."
                )
                return redirect('admin2_dashboard')

    return render(request, 'tpe_app/admin2/registrar_retorno_memo.html', {
        'auto': auto,
        'sim': auto.sim,
    })

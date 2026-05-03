from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..decorators import rol_requerido
from ..models import (
    ABOG_SIM, AGENDA, AUTOTPE, DICTAMEN, DocumentoAdjunto, PM, SIM, VOCAL_TPE,
    CustodiaSIM, Resolucion, RecursoTSP, next_resolucion_num, PerfilUsuario,
)
from ..utils.numeracion import next_num_yy


def _get_abogado_or_403(request):
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or not getattr(perfil, "pm", None):
        raise PermissionDenied()
    return perfil.pm


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_sumario_detalle(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(
        SIM.objects.prefetch_related('militares'),
        pk=sim_id,
    )

    dictamenes       = DICTAMEN.objects.filter(sim=sim).select_related("agenda", "abogado").order_by("-id")
    resoluciones     = list(
        Resolucion.objects.filter(sim=sim, instancia='PRIMERA')
        .select_related("agenda", "abogado", "dictamen").order_by("-fecha")
    )
    reconsideraciones = Resolucion.objects.filter(
        sim=sim, instancia='RECONSIDERACION'
    ).select_related("resolucion_origen", "agenda", "abogado").order_by("-fecha")
    autos_tpe        = AUTOTPE.objects.filter(sim=sim).select_related("agenda", "abogado").order_by("-fecha", "-id")

    # Adjuntar PDF a cada Resolucion y AUTOTPE
    for res in resoluciones:
        doc = DocumentoAdjunto.objects.filter(resolucion_id=res.pk).first()
        res.pdf_url = doc.archivo.url if doc else None

    autos_tpe = list(autos_tpe)
    for auto in autos_tpe:
        doc = DocumentoAdjunto.objects.filter(autotpe_id=auto.pk).first()
        auto.pdf_url = doc.archivo.url if doc else None

    # Determinar el rol del abogado en este SIM:
    # es_via_sim → asignado directamente al SIM (Etapa 1, acceso completo)
    # rrs_asignados → asignado por RR (Etapa 2, solo puede operar sobre sus propios documentos)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    rrs_asignados = list(
        Resolucion.objects.filter(sim=sim, instancia='RECONSIDERACION', abogado=abogado)
        .select_related("resolucion_origen").order_by("-fecha")
    )

    # Verificar si este abogado es el responsable de la carpeta
    es_responsable = ABOG_SIM.objects.filter(
        sim=sim, abogado=abogado, es_responsable=True
    ).exists()

    # Custodia activa (solo relevante para el responsable — botón entregar)
    tiene_custodia = CustodiaSIM.objects.filter(
        sim=sim,
        fecha_entrega__isnull=True,
        abogado=abogado
    ).exists()
    custodio_actual = sim.custodio_actual()

    # Obtener información del usuario Admin2 (para mostrar en template)
    admin2_user = None
    try:
        admin2_perfil = PerfilUsuario.objects.filter(
            rol__in=['ADMIN2_ARCHIVO', 'ADMIN2'],
            activo=True
        ).first()
        if admin2_perfil:
            admin2_user = admin2_perfil.user
    except:
        admin2_user = None

    # Documentos adjuntos al SIM (PDFs escaneados)
    documentos_sim = DocumentoAdjunto.objects.filter(
        sim_id=sim.pk
    ).order_by('-id')

    # Identificar si el abogado es ABOG2 (ejecutoria)
    perfil = getattr(request.user, 'perfilusuario', None)
    es_abog2 = perfil and perfil.rol == 'ABOG2_AUTOS'

    # Para Abog2: verificar acceso via autos asignados
    autos_asignados = [a for a in autos_tpe if a.id == abogado.pk]

    # Validar acceso: Abog2 puede ver si tiene custodia activa (aún sin autos), autos asignados, o asignación via SIM/RR
    if es_abog2 and not autos_asignados and not es_via_sim and not rrs_asignados and not tiene_custodia:
        raise PermissionDenied("No tiene custodia ni autos asignados en este sumario")

    next_url = request.GET.get('next')

    context = {
        "sim": sim,
        "abogado": abogado,
        "abogados_asignados": ABOG_SIM.objects.filter(sim=sim, es_responsable=True).select_related('abogado'),
        "investigados": sim.militares.all(),
        "dictamenes": dictamenes,
        "resoluciones": resoluciones,
        "reconsideraciones": reconsideraciones,
        "autos_tpe": autos_tpe,
        "es_via_sim": es_via_sim,
        "rrs_asignados": rrs_asignados,
        "es_responsable": es_responsable,
        "tiene_custodia": tiene_custodia,
        "custodio_actual": custodio_actual,
        "documentos_sim": documentos_sim,
        "es_abog2": es_abog2,
        "autos_asignados": autos_asignados,
        "admin2_user": admin2_user,
        "next_url": next_url,
    }
    return render(request, "tpe_app/abogado/sumario_detalle.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_dictamen_crear(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM.objects.prefetch_related('militares'), pk=sim_id)

    # Verificar que el abogado esté asignado al SIM (no requiere custodia)
    if not sim.abogados.filter(pk=abogado.pk).exists():
        rr_asignado = Resolucion.objects.filter(
            sim=sim, abogado=abogado, instancia='RECONSIDERACION'
        ).exists()
        if not rr_asignado:
            messages.error(request, "❌ No está asignado a este sumario.")
            return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    militares = list(sim.militares.all())
    agendas = AGENDA.objects.all().order_by("-fecha_prog")

    if request.method == "POST":
        agenda_id = request.POST.get("agenda") or ""

        if not agenda_id:
            messages.error(request, "Seleccione una agenda.")
        else:
            agenda = get_object_or_404(AGENDA, pk=agenda_id)
            autogenerar = request.POST.get("autogenerar_numero") == "1"

            try:
                with transaction.atomic():
                    dictamenes_creados = 0

                    if militares:
                        # Crear un dictamen por cada militar del sumario
                        for pm in militares:
                            conclusion = (request.POST.get(f"conclusion_{pm.pk}") or "").strip()
                            dic_num = None

                            if autogenerar:
                                existentes = list(
                                    DICTAMEN.objects.filter(numero__isnull=False)
                                    .values_list("numero", flat=True)
                                )
                                dic_num = next_num_yy(existentes, today=date.today())

                            DICTAMEN.objects.create(
                                agenda=agenda,
                                sim=sim,
                                abogado=abogado,
                                pm=pm,
                                numero=dic_num,
                                conclusion=conclusion or None,
                            )
                            dictamenes_creados += 1
                    else:
                        # Fallback: si no hay militares, crear un dictamen sin PM
                        conclusion = (request.POST.get("conclusion") or "").strip()
                        dic_num = None

                        if autogenerar:
                            existentes = list(
                                DICTAMEN.objects.filter(numero__isnull=False)
                                .values_list("numero", flat=True)
                            )
                            dic_num = next_num_yy(existentes, today=date.today())

                        DICTAMEN.objects.create(
                            agenda=agenda,
                            sim=sim,
                            abogado=abogado,
                            numero=dic_num,
                            conclusion=conclusion or None,
                        )
                        dictamenes_creados = 1

                messages.success(request, f"✅ {dictamenes_creados} dictamen(es) creado(s).")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except Exception as exc:
                messages.error(request, f"❌ Error al crear dictamen: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "agendas": agendas,
        "militares": militares,
    }
    return render(request, "tpe_app/abogado/dictamen_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_res_crear(request, sim_id: int, dictamen_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    dictamen = get_object_or_404(DICTAMEN, pk=dictamen_id, sim=sim)

    # Seguridad: solo puede crear RES desde un dictamen propio si accede via RR (Etapa 2)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    if not es_via_sim and dictamen.abogado != abogado:
        messages.error(request, "No tiene autorización para crear una RES desde este dictamen.")
        return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    if request.method == "POST":
        res_fec = request.POST.get("fecha") or ""
        res_tipo = request.POST.get("tipo") or ""
        res_resol = (request.POST.get("texto") or "").strip()

        if not res_fec or not res_tipo or not res_resol:
            messages.error(request, "Complete Fecha, Tipo y Resolución.")
        else:
            try:
                with transaction.atomic():
                    res_num = next_resolucion_num()

                    Resolucion.objects.create(
                        instancia='PRIMERA',
                        sim=sim,
                        abogado=abogado,
                        agenda=dictamen.agenda if dictamen.agenda_id else None,
                        dictamen=dictamen,
                        pm=dictamen.pm,
                        numero=res_num,
                        fecha=res_fec,
                        tipo=res_tipo,
                        texto=res_resol,
                    )
                messages.success(request, f"✅ RES creada ({res_num}).")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except Exception as exc:
                messages.error(request, f"❌ Error al crear RES: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "dictamen": dictamen,
        "tipos": Resolucion.TIPO_CHOICES,
    }
    return render(request, "tpe_app/abogado/res_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_rr_crear(request, sim_id: int, res_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    res = get_object_or_404(Resolucion, pk=res_id, sim=sim, instancia='PRIMERA')

    if request.method == "POST":
        rr_fec = request.POST.get("RR_FEC") or ""
        rr_resum = (request.POST.get("RR_RESUM") or "").strip() or None
        rr_resol = (request.POST.get("RR_RESOL") or "").strip()
        autogen = request.POST.get("autogenerar_numero") == "1"

        try:
            with transaction.atomic():
                rr_num = next_resolucion_num() if autogen else None

                Resolucion.objects.create(
                    instancia='RECONSIDERACION',
                    sim=sim,
                    resolucion_origen=res,
                    agenda=res.agenda,
                    abogado=abogado,
                    pm=res.pm,
                    numero=rr_num or '',
                    fecha=rr_fec or None,
                    tipo=rr_resum,
                    texto=rr_resol or None,
                )
            messages.success(request, f"✅ RR creada ({rr_num or 'S/N'}).")
            return redirect("abogado_sumario_detalle", sim_id=sim.pk)
        except Exception as exc:
            messages.error(request, f"❌ Error al crear RR: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "res": res,
    }
    return render(request, "tpe_app/abogado/rr_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_autotpe_crear(request, sim_id: int, dictamen_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    dictamen = get_object_or_404(DICTAMEN, pk=dictamen_id, sim=sim)

    # Seguridad: solo puede crear Auto desde un dictamen propio si accede via RR (Etapa 2)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    if not es_via_sim and dictamen.abogado != abogado:
        messages.error(request, "No tiene autorización para crear un Auto desde este dictamen.")
        return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    if request.method == "POST":
        tpe_fec = request.POST.get("fecha") or ""
        tpe_tipo = request.POST.get("tipo") or ""
        tpe_resol = (request.POST.get("texto") or "").strip()
        autogen = request.POST.get("autogenerar_numero") == "1"

        try:
            with transaction.atomic():
                tpe_num = None
                if autogen:
                    existentes = list(AUTOTPE.objects.values_list("numero", flat=True))
                    tpe_num = next_num_yy(existentes, today=date.today())

                AUTOTPE.objects.create(
                    sim=sim,
                    pm=dictamen.pm,
                    abogado=abogado,
                    agenda=dictamen.agenda if dictamen.agenda_id else None,
                    numero=tpe_num,
                    fecha=tpe_fec or None,
                    tipo=tpe_tipo or None,
                    texto=tpe_resol or None,
                )
            messages.success(request, f"✅ Auto TPE creado ({tpe_num or 'S/N'}).")
            return redirect("abogado_sumario_detalle", sim_id=sim.pk)
        except Exception as exc:
            messages.error(request, f"❌ Error al crear Auto TPE: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "dictamen": dictamen,
        "tipos": AUTOTPE.TIPO_CHOICES,
    }
    return render(request, "tpe_app/abogado/autotpe_form.html", context)


@rol_requerido("ABOG2_AUTOS", "ADMINISTRADOR", "MASTER")
def abogado_autotpe_ejecutoria_crear(request, sim_id: int):
    """ABOG2 crea Auto de Ejecutoria desde el dashboard del sumario"""
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    # Buscar la Resolución más reciente (PRIMERA o RECONSIDERACION)
    resolucion = (
        Resolucion.objects
        .filter(sim=sim)
        .select_related('pm')
        .order_by('-fecha')
        .first()
    )

    if not resolucion:
        messages.error(request, "❌ No hay resoluciones en este sumario para crear Auto de Ejecutoria")
        return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    if request.method == "POST":
        tpe_fec = request.POST.get("fecha") or ""
        tpe_resol = (request.POST.get("texto") or "").strip()
        autogen = request.POST.get("autogenerar_numero") == "1"

        try:
            with transaction.atomic():
                tpe_num = None
                if autogen:
                    existentes = list(AUTOTPE.objects.values_list("numero", flat=True))
                    from ..utils.numeracion import next_num_yy
                    from datetime import date
                    tpe_num = next_num_yy(existentes, today=date.today())

                AUTOTPE.objects.create(
                    sim=sim,
                    abogado=abogado,
                    pm=resolucion.pm,
                    resolucion=resolucion,
                    numero=tpe_num,
                    fecha=tpe_fec or None,
                    tipo='AUTO_EJECUTORIA',
                    texto=tpe_resol or None,
                )

                # Marcar SIM como concluido en el TPE solo si no hay otro militar
                # cuyo proceso está activo en instancia externa (TSP o cumplimiento).
                ESTADOS_ACTIVOS_EXTERNOS = {'PROCESO_EN_EL_TSP', 'CUMPLIMIENTO_EN_TPE'}
                if sim.estado not in ESTADOS_ACTIVOS_EXTERNOS:
                    sim.estado = 'PROCESO_CONCLUIDO_TPE'
                    sim.save()

                messages.success(request, f"✅ Auto de Ejecutoria {tpe_num or 'S/N'} creado correctamente")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
        except Exception as exc:
            messages.error(request, f"❌ Error: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "resolucion": resolucion,
    }
    return render(request, "tpe_app/abogado/autotpe_ejecutoria_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_auto_excusa_crear(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    # Cargar vocales activos
    vocales = VOCAL_TPE.objects.filter(activo=True).select_related("pm")
    agendas = AGENDA.objects.all().order_by("-fecha_prog")

    if request.method == "POST":
        vocal_id = request.POST.get("vocal_id") or ""
        agenda_id = request.POST.get("agenda") or ""
        fecha_str = request.POST.get("fecha") or ""
        resolucion = (request.POST.get("texto") or "").strip()

        if not vocal_id or not agenda_id or not fecha_str:
            messages.error(request, "Complete Vocal, Agenda y Fecha.")
        else:
            try:
                vocal = get_object_or_404(VOCAL_TPE, pk=vocal_id, activo=True)
                agenda = get_object_or_404(AGENDA, pk=agenda_id)

                with transaction.atomic():
                    tpe_num = None

                    if request.POST.get("autogenerar_numero") == "1":
                        existentes = list(
                            AUTOTPE.objects.filter(numero__isnull=False)
                            .values_list("numero", flat=True)
                        )
                        tpe_num = next_num_yy(existentes, today=date.today())

                    # Obtener el primer militar del sumario
                    pm = sim.militares.first()
                    if not pm:
                        messages.error(request, "❌ El sumario no tiene militares asignados.")
                        return render(request, "tpe_app/abogado/auto_excusa_form.html", context)

                    auto = AUTOTPE.objects.create(
                        sim=sim,
                        pm=pm,
                        abogado=abogado,
                        agenda=agenda,
                        vocal_excusado=vocal,
                        numero=tpe_num,
                        fecha=fecha_str,
                        tipo="AUTO_EXCUSA",
                        texto=resolucion or None,
                    )

                messages.success(request, f"✅ Auto de Excusa creado ({tpe_num or 'S/N'}).")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except Exception as exc:
                messages.error(request, f"❌ Error al crear Auto de Excusa: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "vocales": vocales,
        "agendas": agendas,
    }
    return render(request, "tpe_app/abogado/auto_excusa_form.html", context)


# ============================================================
# CUSTODIA: Confirmación y devolución de carpetas
# ============================================================

@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_confirmar_recepcion(request, sim_id: int):
    """El abogado confirma que recibió la carpeta física de Admin2"""
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    custodia = CustodiaSIM.objects.filter(
        sim=sim, abogado=abogado, estado='PENDIENTE_CONFIRMACION', fecha_entrega__isnull=True
    ).first()

    if not custodia:
        messages.error(request, "❌ No hay carpeta pendiente de confirmación")
        return redirect('abogado_sumario_detalle', sim_id=sim_id)

    if request.method == 'POST':
        try:
            custodia.estado = 'RECIBIDA_CONFORME'
            custodia.save()
            messages.success(request, "✅ Recepción confirmada. La carpeta está en su poder.")
            return redirect('abogado_sumario_detalle', sim_id=sim_id)
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")

    # Obtener información del usuario Admin2 (para mostrar en template)
    admin2_user = None
    try:
        admin2_perfil = PerfilUsuario.objects.filter(
            rol__in=['ADMIN2_ARCHIVO', 'ADMIN2'],
            activo=True
        ).first()
        if admin2_perfil:
            admin2_user = admin2_perfil.user
    except:
        admin2_user = None

    return render(request, 'tpe_app/abogado/confirmar_recepcion.html', {
        'sim': sim,
        'custodia': custodia,
        'admin2_user': admin2_user,
    })


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_devolver_carpeta(request, sim_id: int):
    """El abogado devuelve la carpeta a Admin2"""
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    custodia = CustodiaSIM.objects.filter(
        sim=sim, abogado=abogado, estado='RECIBIDA_CONFORME', fecha_entrega__isnull=True
    ).first()

    if not custodia:
        messages.error(request, "❌ No tiene la carpeta en su poder")
        return redirect('abogado_sumario_detalle', sim_id=sim_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Cerrar custodia del abogado
                custodia.fecha_entrega = timezone.now()
                custodia.save()

                # Crear nueva custodia con Admin2 pendiente de confirmación
                CustodiaSIM.objects.create(
                    sim=sim,
                    tipo_custodio='ADMIN2_ARCHIVO',
                    abogado=abogado,
                    usuario=request.user,
                    motivo='REVISION',
                    estado='PENDIENTE_CONFIRMACION',
                )

            messages.success(request, "✅ Carpeta devuelta. Admin2 debe confirmar la recepción.")
            return redirect('abogado_sumario_detalle', sim_id=sim_id)
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")

    # Obtener información del usuario Admin2 (para mostrar en template)
    admin2_user = None
    try:
        admin2_perfil = PerfilUsuario.objects.filter(
            rol__in=['ADMIN2_ARCHIVO', 'ADMIN2'],
            activo=True
        ).first()
        if admin2_perfil:
            admin2_user = admin2_perfil.user
    except:
        admin2_user = None

    return render(request, 'tpe_app/abogado/devolver_carpeta.html', {
        'sim': sim,
        'custodia': custodia,
        'admin2_user': admin2_user,
    })


# ============================================================
# Abogado: Elaborar RAP (Recurso de Apelación)
# ============================================================

@rol_requerido("ABOG1_ASESOR", "ABOG2_AUTOS")
def abogado_rap_elaborar(request, sim_id: int, rap_id: int):
    """El abogado elabora el RAP completando número, fecha y texto"""
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    rap = get_object_or_404(RecursoTSP, pk=rap_id, sim=sim, instancia='APELACION')

    # Verificar que el RAP esté en poder del abogado (custodia activa)
    custodia = sim.custodias.filter(
        tipo_custodio__in=['ABOG_ASESOR', 'ABOG_AUTOS'],
        fecha_entrega__isnull=True
    ).first()

    if not custodia or custodia.abogado != abogado:
        raise PermissionDenied("No tienes permiso para elaborar este RAP.")

    if request.method == "POST":
        numero = (request.POST.get("numero") or "").strip()
        fecha_str = request.POST.get("fecha") or ""
        texto = (request.POST.get("texto") or "").strip()
        tipo = request.POST.get("tipo") or ""

        if not numero or not fecha_str or not texto:
            messages.error(request, "❌ Número, fecha y texto del RAP son obligatorios.")
        else:
            try:
                from datetime import datetime as dt
                fecha = dt.strptime(fecha_str, '%Y-%m-%d').date()

                with transaction.atomic():
                    # Actualizar el RAP con los datos elaborados
                    rap.numero = numero
                    rap.fecha = fecha
                    rap.texto = texto
                    rap.tipo = tipo
                    rap.save()

                    # Cerrar custodia del abogado
                    custodia.fecha_entrega = timezone.now()
                    custodia.save()

                    # Crear custodia para Admin2 (RAP elaborado, pendiente envío al TSP)
                    CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio='ADMIN2_ARCHIVO',
                        usuario=request.user,
                        motivo='APELACION_TSP',
                        observacion=f'RAP {numero} elaborado, pendiente de envío al TSP',
                        estado='RECIBIDA_CONFORME'
                    )

                    messages.success(
                        request,
                        f"✅ RAP {numero} elaborado correctamente."
                    )
                    return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except ValueError:
                messages.error(request, "❌ Formato de fecha inválido.")
            except Exception as exc:
                messages.error(request, f"❌ Error al elaborar RAP: {exc}")

    context = {
        "sim": sim,
        "rap": rap,
        "abogado": abogado,
        "custodia": custodia,
    }
    return render(request, "tpe_app/abogado/rap_elaborar.html", context)

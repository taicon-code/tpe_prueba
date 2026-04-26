from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import rol_requerido
from ..models import AGENDA, AUTOTPE, DICTAMEN, Resolucion, VOCAL_TPE, VotoVocal, AsistenciaVocal


def _get_vocal_or_403(request):
    """Obtiene el VOCAL_TPE del usuario actual, o None si no está vinculado"""
    perfil = getattr(request.user, "perfilusuario", None)
    return getattr(perfil, "vocal", None) if perfil else None


@rol_requerido("VOCAL_TPE")
def vocal_dashboard(request):
    """Dashboard de vocal/secretario de actas. Lista agendas pasadas y próximas"""
    vocal = _get_vocal_or_403(request)

    # Agendas del tribunal (todas)
    agendas_proximas = AGENDA.objects.filter(
        fecha_prog__gte=date.today()
    ).order_by("fecha_prog")

    agendas_pasadas = AGENDA.objects.filter(
        fecha_prog__lt=date.today()
    ).order_by("-fecha_prog")[:10]  # Últimas 10

    # Contar dictámenes pendientes de confirmar y agregar al objeto
    for agenda in agendas_proximas:
        count = DICTAMEN.objects.filter(
            agenda=agenda, estado='PENDIENTE'
        ).count()
        agenda.pending_count = count

    context = {
        "vocal": vocal,
        "agendas_proximas": agendas_proximas,
        "agendas_pasadas": agendas_pasadas,
        "sin_vocal_vinculado": vocal is None,
    }

    return render(request, "tpe_app/vocal/dashboard_vocal.html", context)


@rol_requerido("VOCAL_TPE")
def vocal_agenda_detalle(request, ag_id: int):
    """Detalle de una agenda: dictámenes a confirmar, RR y autos a tratarse"""
    vocal = _get_vocal_or_403(request)
    agenda = get_object_or_404(AGENDA, pk=ag_id)

    # Dictámenes de esta agenda
    dictamenes = DICTAMEN.objects.filter(
        agenda=agenda
    ).select_related("sim", "pm", "abog", "secretario").order_by("sim__codigo", "pm__paterno")

    # Recursos de Reconsideración en esta agenda
    rr_en_agenda = Resolucion.objects.filter(
        agenda=agenda, instancia='RECONSIDERACION'
    ).select_related("sim", "pm", "resolucion_origen", "abog").order_by("-fecha")

    # Autos TPE en esta agenda
    autos_en_agenda = AUTOTPE.objects.filter(
        agenda=agenda
    ).select_related("sim", "pm", "abog").order_by("-fecha")

    # Agrupar dictámenes por sumario
    dictamenes_por_sim = {}
    for dic in dictamenes:
        if dic.sim.pk not in dictamenes_por_sim:
            dictamenes_por_sim[dic.sim.pk] = {
                "sim": dic.sim,
                "dictamenes": []
            }
        dictamenes_por_sim[dic.sim.pk]["dictamenes"].append(dic)

    context = {
        "vocal": vocal,
        "agenda": agenda,
        "dictamenes": dictamenes,
        "dictamenes_por_sim": dictamenes_por_sim,
        "rr_en_agenda": rr_en_agenda,
        "autos_en_agenda": autos_en_agenda,
    }

    return render(request, "tpe_app/vocal/agenda_detalle.html", context)


@rol_requerido("VOCAL_TPE")
def vocal_confirmar_dictamen(request, dic_id: int):
    """Confirmar o modificar un dictamen (solo para secretario de actas)"""
    vocal = _get_vocal_or_403(request)
    dictamen = get_object_or_404(
        DICTAMEN.objects.select_related("sim", "pm", "abog", "agenda"),
        pk=dic_id
    )

    if request.method == "GET":
        # Mostrar formulario de confirmación
        context = {
            "vocal": vocal,
            "dictamen": dictamen,
        }
        return render(request, "tpe_app/vocal/confirmar_dictamen_form.html", context)

    elif request.method == "POST":
        # Procesar confirmación o modificación
        accion = request.POST.get("accion", "").strip()  # "confirmar" o "modificar"
        concl_sec = (request.POST.get("conclusion_secretario") or "").strip()

        try:
            with transaction.atomic():
                if accion == "confirmar":
                    # Confirmar sin cambios: copia la conclusión del abogado
                    dictamen.estado = "CONFIRMADO"
                    dictamen.conclusion_secretario = dictamen.conclusion  # Mantiene original
                    msg = f"✓ Dictamen {dictamen.numero or 'S/N'} confirmado"

                elif accion == "modificar":
                    # Modificar conclusión
                    if not concl_sec:
                        messages.error(request, "Debe ingresar la conclusión modificada")
                        return redirect("vocal_confirmar_dictamen", dic_id=dictamen.pk)

                    dictamen.estado = "MODIFICADO"
                    dictamen.conclusion_secretario = concl_sec.upper()
                    msg = f"✓ Dictamen {dictamen.numero or 'S/N'} modificado"

                else:
                    messages.error(request, "Acción inválida")
                    return redirect("vocal_confirmar_dictamen", dic_id=dictamen.pk)

                dictamen.secretario = vocal
                dictamen.fecha_confirmacion = date.today()
                dictamen.save()

                messages.success(request, msg)

        except Exception as e:
            messages.error(request, f"Error al confirmar: {str(e)}")
            return redirect("vocal_confirmar_dictamen", dic_id=dictamen.pk)

        # Redirigir a la agenda para confirmar el siguiente
        return redirect("vocal_agenda_detalle", ag_id=dictamen.agenda.pk)


@rol_requerido("VOCAL_TPE")
def vocal_registrar_asistencia(request, ag_id: int):
    """Registrar asistencia de vocales en una sesión"""
    vocal = _get_vocal_or_403(request)
    agenda = get_object_or_404(AGENDA, pk=ag_id)

    # Todos los vocales activos
    vocales_activos = VOCAL_TPE.objects.filter(activo=True).order_by("cargo", "pm__paterno")

    if request.method == "GET":
        # Cargar asistencias existentes (si las hay)
        asistencias_existentes = {
            a.vocal.pk: a
            for a in AsistenciaVocal.objects.filter(agenda=agenda)
        }

        context = {
            "vocal": vocal,
            "agenda": agenda,
            "vocales_activos": vocales_activos,
            "asistencias": asistencias_existentes,
        }
        return render(request, "tpe_app/vocal/registrar_asistencia.html", context)

    elif request.method == "POST":
        # Procesar asistencia de cada vocal
        try:
            with transaction.atomic():
                # Borrar asistencias anteriores y crear nuevas
                AsistenciaVocal.objects.filter(agenda=agenda).delete()

                for vocal_obj in vocales_activos:
                    estado = request.POST.get(f"estado_{vocal_obj.pk}", "PRESENTE").strip()
                    justificacion = request.POST.get(f"justificacion_{vocal_obj.pk}", "").strip()

                    # Validar estado
                    if estado not in ["PRESENTE", "AUSENTE", "EXCUSADO"]:
                        estado = "PRESENTE"

                    AsistenciaVocal.objects.create(
                        agenda=agenda,
                        vocal=vocal_obj,
                        estado=estado,
                        justificacion=justificacion if justificacion else None,
                    )

                messages.success(request, f"✓ Asistencia registrada para agenda {agenda.numero}")

        except Exception as e:
            messages.error(request, f"Error al registrar asistencia: {str(e)}")
            return redirect("vocal_registrar_asistencia", ag_id=agenda.pk)

        return redirect("vocal_agenda_detalle", ag_id=agenda.pk)


@rol_requerido("VOCAL_TPE")
def vocal_registrar_votos(request, dic_id: int):
    """Registrar votos de vocales en un dictamen"""
    vocal = _get_vocal_or_403(request)
    dictamen = get_object_or_404(
        DICTAMEN.objects.select_related("sim", "pm", "abog", "agenda"),
        pk=dic_id
    )

    agenda = dictamen.agenda

    # Vocales presentes en esa sesión (según asistencia)
    asistencias = AsistenciaVocal.objects.filter(
        agenda=agenda,
        estado="PRESENTE"
    ).select_related("vocal")

    vocales_presentes = [a.vocal for a in asistencias]

    if request.method == "GET":
        # Cargar votos existentes
        votos_existentes = {
            v.vocal.pk: v.voto
            for v in VotoVocal.objects.filter(dictamen=dictamen)
        }

        context = {
            "vocal": vocal,
            "dictamen": dictamen,
            "agenda": agenda,
            "vocales_presentes": vocales_presentes,
            "votos": votos_existentes,
        }
        return render(request, "tpe_app/vocal/registrar_votos.html", context)

    elif request.method == "POST":
        try:
            with transaction.atomic():
                # Borrar votos anteriores y crear nuevos
                VotoVocal.objects.filter(dictamen=dictamen).delete()

                aprueba_count = 0
                rechaza_count = 0

                for vocal_obj in vocales_presentes:
                    voto = request.POST.get(f"voto_{vocal_obj.pk}", "").strip()
                    observacion = request.POST.get(f"observacion_{vocal_obj.pk}", "").strip()

                    # Validar voto
                    if voto not in ["APRUEBA", "RECHAZA", "ABSTIENE", "AUSENTE"]:
                        voto = "ABSTIENE"

                    if voto == "APRUEBA":
                        aprueba_count += 1
                    elif voto == "RECHAZA":
                        rechaza_count += 1

                    VotoVocal.objects.create(
                        dictamen=dictamen,
                        vocal=vocal_obj,
                        voto=voto,
                        observacion=observacion if observacion else None,
                    )

                # Calcular resultado del tribunal
                if aprueba_count > rechaza_count:
                    resultado = "PROCEDENTE"
                elif rechaza_count > aprueba_count:
                    resultado = "IMPROCEDENTE"
                else:
                    resultado = "MIXTO"

                # Guardar resultado en el dictamen
                dictamen.resultado_tribunal = resultado
                dictamen.save()

                messages.success(
                    request,
                    f"✓ Votos registrados. Resultado: {resultado} ({aprueba_count} a favor, {rechaza_count} en contra)"
                )

        except Exception as e:
            messages.error(request, f"Error al registrar votos: {str(e)}")
            return redirect("vocal_registrar_votos", dic_id=dictamen.pk)

        return redirect("vocal_agenda_detalle", ag_id=agenda.pk)

from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import rol_requerido
from ..models import AGENDA, AUTOTPE, DICTAMEN, RES, RR, VOCAL_TPE


def _get_vocal_or_403(request):
    """Obtiene el VOCAL_TPE del usuario actual o lanza 403"""
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or not getattr(perfil, "vocal", None):
        raise Http404
    return perfil.vocal


@rol_requerido("VOCAL_TPE")
def vocal_dashboard(request):
    """Dashboard de vocal/secretario de actas. Lista agendas pasadas y próximas"""
    vocal = _get_vocal_or_403(request)

    # Agendas del tribunal (todas)
    agendas_proximas = AGENDA.objects.filter(
        AG_FECPROG__gte=date.today()
    ).order_by("AG_FECPROG")

    agendas_pasadas = AGENDA.objects.filter(
        AG_FECPROG__lt=date.today()
    ).order_by("-AG_FECPROG")[:10]  # Últimas 10

    # Contar dictámenes pendientes de confirmar y agregar al objeto
    for agenda in agendas_proximas:
        count = DICTAMEN.objects.filter(
            agenda=agenda, DIC_ESTADO='PENDIENTE'
        ).count()
        agenda.pending_count = count

    context = {
        "vocal": vocal,
        "agendas_proximas": agendas_proximas,
        "agendas_pasadas": agendas_pasadas,
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
    ).select_related("sim", "pm", "abog", "secretario").order_by("sim__SIM_COD", "pm__PM_PATERNO")

    # Recursos de Reconsideración en esta agenda
    rr_en_agenda = RR.objects.filter(
        agenda=agenda
    ).select_related("sim", "pm", "res", "abog").order_by("-RR_FEC")

    # Autos TPE en esta agenda
    autos_en_agenda = AUTOTPE.objects.filter(
        agenda=agenda
    ).select_related("sim", "pm", "abog").order_by("-TPE_FEC")

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
        concl_sec = (request.POST.get("DIC_CONCL_SEC") or "").strip()

        try:
            with transaction.atomic():
                if accion == "confirmar":
                    # Confirmar sin cambios: copia la conclusión del abogado
                    dictamen.DIC_ESTADO = "CONFIRMADO"
                    dictamen.DIC_CONCL_SEC = dictamen.DIC_CONCL  # Mantiene original
                    msg = f"✓ Dictamen {dictamen.DIC_NUM or 'S/N'} confirmado"

                elif accion == "modificar":
                    # Modificar conclusión
                    if not concl_sec:
                        messages.error(request, "Debe ingresar la conclusión modificada")
                        return redirect("vocal_confirmar_dictamen", dic_id=dictamen.pk)

                    dictamen.DIC_ESTADO = "MODIFICADO"
                    dictamen.DIC_CONCL_SEC = concl_sec.upper()
                    msg = f"✓ Dictamen {dictamen.DIC_NUM or 'S/N'} modificado"

                else:
                    messages.error(request, "Acción inválida")
                    return redirect("vocal_confirmar_dictamen", dic_id=dictamen.pk)

                dictamen.secretario = vocal
                dictamen.DIC_CONFIR_FEC = date.today()
                dictamen.save()

                messages.success(request, msg)

        except Exception as e:
            messages.error(request, f"Error al confirmar: {str(e)}")
            return redirect("vocal_confirmar_dictamen", dic_id=dictamen.pk)

        # Redirigir a la agenda para confirmar el siguiente
        return redirect("vocal_agenda_detalle", ag_id=dictamen.agenda.pk)

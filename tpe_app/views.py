# ============================================================
#  VISTAS DJANGO PARA BUSCAR HISTORIAL DE PERSONAL
#  Archivo: tpe_app/views.py
# ============================================================

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from tpe_app.models import PM
from tpe_app.queries.historial_personal import ConsultasHistorialPersonal


@require_http_methods(["GET", "POST"])
def buscar_historial_view(request):
    """
    Vista principal para buscar historial de personal militar.
    GET: Muestra el formulario de búsqueda
    POST: Procesa la búsqueda y muestra resultados
    """
    
    context = {
        'titulo': 'Consulta de Historial Disciplinario',
        'personales': [],
        'historial': None,
        'estado': None,
        'error': None,
        'multiples_resultados': False,
        'busqueda_realizada': False,
    }
    
    # Si se envió el formulario (POST)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        cedula = request.POST.get('cedula', '').strip()
        
        context['nombre'] = nombre
        context['apellido_paterno'] = apellido_paterno
        context['apellido_materno'] = apellido_materno
        context['cedula'] = cedula
        context['busqueda_realizada'] = True
        
        # Validar que se ingresó al menos un criterio
        if not any([nombre, apellido_paterno, apellido_materno, cedula]):
            context['error'] = '⚠️ Por favor ingresa al menos un criterio de búsqueda (nombre, apellido o cédula).'
            return render(request, 'tpe_app/historial/buscar.html', context)
        
        try:
            # Buscar personal
            personales = ConsultasHistorialPersonal.buscar_personal(
                nombre=nombre if nombre else None,
                apellido_paterno=apellido_paterno if apellido_paterno else None,
                apellido_materno=apellido_materno if apellido_materno else None,
                ci=cedula if cedula else None,
            )
            
            if not personales.exists():
                context['error'] = '❌ No se encontró ningún personal con esos criterios.'
                return render(request, 'tpe_app/historial/buscar.html', context)
            
            # Si hay un solo resultado
            if personales.count() == 1:
                personal = personales.first()
                historial = ConsultasHistorialPersonal.obtener_historial_completo(personal.id)
                estado = ConsultasHistorialPersonal.obtener_estado_actual(personal.id)
                
                context['personales'] = [personal]
                context['personal_seleccionado'] = personal
                context['historial'] = historial
                context['estado'] = estado
                context['multiples_resultados'] = False
                
                return render(request, 'tpe_app/historial/resultado.html', context)
            
            else:
                # Si hay múltiples resultados
                context['personales'] = personales
                context['multiples_resultados'] = True
                context['cantidad_resultados'] = personales.count()
                
                return render(request, 'tpe_app/historial/resultado.html', context)
        
        except Exception as e:
            context['error'] = f'❌ Error al buscar: {str(e)}'
            return render(request, 'tpe_app/historial/buscar.html', context)
    
    # GET: Mostrar formulario vacío
    return render(request, 'tpe_app/historial/buscar.html', context)


def historial_personal_detalle(request, personal_id):
    """
    Vista para ver el historial detallado de un personal específico.
    """
    try:
        personal = PM.objects.get(id=personal_id)
    except PM.DoesNotExist:
        context = {
            'error': '❌ Personal no encontrado.',
            'titulo': 'Historial Disciplinario',
        }
        return render(request, 'tpe_app/historial/resultado.html', context)
    
    historial = ConsultasHistorialPersonal.obtener_historial_completo(personal.id)
    estado = ConsultasHistorialPersonal.obtener_estado_actual(personal.id)
    
    context = {
        'titulo': f'Historial: {personal.PM_NOMBRE} {personal.PM_PATERNO}',
        'personales': [personal],
        'personal_seleccionado': personal,
        'historial': historial,
        'estado': estado,
        'busqueda_realizada': True,
    }
    
    return render(request, 'tpe_app/historial/resultado.html', context)
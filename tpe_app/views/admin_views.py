# tpe_app/views/admin_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods
from ..decorators import rol_requerido
from ..models import SIM, PM, ABOG, PerfilUsuario, VOCAL_TPE
from datetime import date

@rol_requerido('ADMINISTRADOR')
def admin_dashboard(request):
    """Dashboard principal para administradores"""

    # Estadísticas generales
    context = {
        'total_sumarios': SIM.objects.count(),
        'sumarios_para_agenda': SIM.objects.filter(SIM_ESTADO='PARA_AGENDA').count(),
        'sumarios_en_tpe': SIM.objects.filter(SIM_ESTADO='PROCESO_EN_EL_TPE').count(),
        'sumarios_en_tsp': SIM.objects.filter(SIM_ESTADO='EN_APELACION_TSP').count(),
        'total_personal': PM.objects.count(),
        'total_abogados': ABOG.objects.count(),
        'total_usuarios': PerfilUsuario.objects.filter(activo=True).count(),

        # Sumarios recientes
        'sumarios_recientes': SIM.objects.order_by('-SIM_FECREG')[:10],

        # Lista de usuarios y sus roles
        'usuarios_activos': PerfilUsuario.objects.filter(activo=True).select_related('user', 'abogado').order_by('user__username'),
        'usuarios_inactivos': PerfilUsuario.objects.filter(activo=False).select_related('user', 'abogado').order_by('user__username'),
        'rol_choices': PerfilUsuario.ROL_CHOICES,
        'abogados': ABOG.objects.all().order_by('AB_PATERNO', 'AB_MATERNO'),
    }

    return render(request, 'tpe_app/dashboard_admin.html', context)


@rol_requerido('ADMINISTRADOR')
@require_http_methods(["GET", "POST"])
def crear_usuario_con_rol(request):
    """Vista para crear usuarios y asignarles roles desde el panel de admin personalizado"""

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        primera_contrasena = password
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        rol = request.POST.get('rol', '').strip()
        abogado_id = request.POST.get('abogado', None)
        vocal_id = request.POST.get('vocal', None)

        # Validaciones
        errores = []
        if not username:
            errores.append('El nombre de usuario es requerido')
        if User.objects.filter(username=username).exists():
            errores.append(f'El usuario "{username}" ya existe')
        if not email:
            errores.append('El email es requerido')
        if User.objects.filter(email=email).exists():
            errores.append(f'El email "{email}" ya está en uso')
        if len(password) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres')
        if not rol:
            errores.append('Debe seleccionar un rol')
        if rol == 'ABOGADO' and not abogado_id:
            errores.append('Para rol ABOGADO, debe asignar un abogado')
        if rol == 'VOCAL_TPE' and not vocal_id:
            errores.append('Para rol VOCAL_TPE, debe asignar un vocal del tribunal')

        if errores:
            context = {
                'errores': errores,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'rol': rol,
                'rol_choices': PerfilUsuario.ROL_CHOICES,
                'abogados': ABOG.objects.all().order_by('AB_PATERNO', 'AB_MATERNO'),
                'vocales': VOCAL_TPE.objects.all().order_by('pm__PM_PATERNO', 'pm__PM_MATERNO'),
            }
            return render(request, 'tpe_app/crear_usuario.html', context)

        try:
            # Crear usuario
            usuario = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Asignar rol
            abogado = None
            vocal = None
            if rol == 'ABOGADO' and abogado_id:
                abogado = ABOG.objects.get(id=abogado_id)
            elif rol == 'VOCAL_TPE' and vocal_id:
                vocal = VOCAL_TPE.objects.get(id=vocal_id)

            perfil = PerfilUsuario.objects.create(
                user=usuario,
                rol=rol,
                abogado=abogado,
                vocal=vocal,
                activo=True
            )

            messages.success(
                request,
                f'✓ Usuario "{username}" creado exitosamente con rol {perfil.get_rol_display()}'
            )
            return redirect('admin_dashboard')

        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
            context = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'rol': rol,
                'rol_choices': PerfilUsuario.ROL_CHOICES,
                'abogados': ABOG.objects.all().order_by('AB_PATERNO', 'AB_MATERNO'),
                'vocales': VOCAL_TPE.objects.all().order_by('pm__PM_PATERNO', 'pm__PM_MATERNO'),
            }
            return render(request, 'tpe_app/crear_usuario.html', context)

    # GET: mostrar formulario
    context = {
        'rol_choices': PerfilUsuario.ROL_CHOICES,
        'abogados': ABOG.objects.all().order_by('AB_PATERNO', 'AB_MATERNO'),
        'vocales': VOCAL_TPE.objects.all().order_by('pm__PM_PATERNO', 'pm__PM_MATERNO'),
    }
    return render(request, 'tpe_app/crear_usuario.html', context)
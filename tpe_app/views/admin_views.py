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
        'sumarios_para_agenda': SIM.objects.filter(estado='PARA_AGENDA').count(),
        'sumarios_en_tpe': SIM.objects.filter(estado='PROCESO_EN_EL_TPE').count(),
        'sumarios_en_tsp': SIM.objects.filter(estado='PROCESO_EN_EL_TSP').count(),
        'total_personal': PM.objects.count(),
        'total_abogados': ABOG.objects.count(),
        'total_usuarios': PerfilUsuario.objects.filter(activo=True).count(),

        # Sumarios recientes
        'sumarios_recientes': SIM.objects.order_by('-fecha_registro')[:10],

        # Lista de usuarios y sus roles
        'usuarios_activos': PerfilUsuario.objects.filter(activo=True).select_related('user', 'abogado', 'vocal__pm', 'pm').order_by('user__username'),
        'usuarios_inactivos': PerfilUsuario.objects.filter(activo=False).select_related('user', 'abogado', 'vocal__pm', 'pm').order_by('user__username'),
        'rol_choices': PerfilUsuario.ROL_CHOICES,
        'abogados': ABOG.objects.all().order_by('paterno', 'materno'),
    }

    return render(request, 'tpe_app/dashboard_admin.html', context)


@rol_requerido('ADMINISTRADOR')
@require_http_methods(["GET", "POST"])
def crear_usuario_con_rol(request):
    """Vista para crear usuarios y asignarles roles desde el panel de admin personalizado"""

    def _base_context():
        return {
            'rol_choices': PerfilUsuario.ROL_CHOICES,
            'abogados':    ABOG.objects.all().order_by('paterno', 'materno'),
            'vocales':     VOCAL_TPE.objects.filter(activo=True).select_related('pm').order_by('pm__paterno'),
            'personal':    PM.objects.filter(estado='ACTIVO').order_by('paterno', 'materno'),
            'roles_con_pm': PerfilUsuario.ROLES_CON_PM,
        }

    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        password  = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        rol        = request.POST.get('rol', '').strip()
        abogado_id = request.POST.get('abogado') or None
        vocal_id   = request.POST.get('vocal') or None
        pm_id      = request.POST.get('pm') or None

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
        if rol in ('ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO') and not abogado_id:
            errores.append('Para rol Abogado, debe asignar el registro de abogado correspondiente')
        if rol == 'SECRETARIO_ACTAS' and not vocal_id:
            errores.append('Para rol VOCAL_TPE, debe asignar un vocal del tribunal')
        if rol in PerfilUsuario.ROLES_CON_PM and not pm_id:
            errores.append('Para este rol, debe seleccionar el registro de Personal Militar')

        if errores:
            ctx = _base_context()
            ctx.update({'errores': errores, 'username': username, 'email': email,
                        'first_name': first_name, 'last_name': last_name, 'rol': rol})
            return render(request, 'tpe_app/crear_usuario.html', ctx)

        try:
            usuario = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first_name, last_name=last_name,
            )

            abogado = ABOG.objects.get(id=abogado_id) if abogado_id else None
            vocal   = VOCAL_TPE.objects.get(id=vocal_id) if vocal_id else None
            pm      = PM.objects.get(id=pm_id) if pm_id else None

            perfil = PerfilUsuario.objects.create(
                user=usuario, rol=rol,
                abogado=abogado, vocal=vocal, pm=pm,
                activo=True,
            )

            messages.success(request,
                f'Usuario "{username}" creado con rol {perfil.get_rol_display()}')
            return redirect('admin_dashboard')

        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
            ctx = _base_context()
            ctx.update({'username': username, 'email': email,
                        'first_name': first_name, 'last_name': last_name, 'rol': rol})
            return render(request, 'tpe_app/crear_usuario.html', ctx)

    return render(request, 'tpe_app/crear_usuario.html', _base_context())
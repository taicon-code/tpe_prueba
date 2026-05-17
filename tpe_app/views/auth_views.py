# tpe_app/views/auth_views.py
import logging

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.contrib import messages
from tpe_app.models import PerfilUsuario

security_log = logging.getLogger('tpe_app.security')


def _client_ip(request):
    """IP del cliente respetando proxy (X-Forwarded-For tiene prioridad)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '-')


def _terminar_sesiones_previas(user, request):
    """Elimina todas las sesiones activas del usuario salvo la actual.

    Politica: 1 sesion concurrente por usuario. Evita compartir credenciales
    y reduce ventana de exposicion ante robo de session-id.

    Solo se ejecuta despues de un `login(request, user)` exitoso, asi que
    request.session.session_key ya es el de la nueva sesion.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    current_key = request.session.session_key
    sesiones_eliminadas = 0
    for s in Session.objects.filter(expire_date__gt=timezone.now()):
        try:
            data = s.get_decoded()
        except Exception:
            continue
        # auth.SESSION_KEY guarda el user.pk como string
        if str(data.get('_auth_user_id', '')) == str(user.pk) and s.session_key != current_key:
            s.delete()
            sesiones_eliminadas += 1

    if sesiones_eliminadas:
        security_log.info(
            'SESSION_PREEMPTED user=%s eliminadas=%s ip=%s',
            user.username, sesiones_eliminadas, _client_ip(request),
        )
    return sesiones_eliminadas


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        ip = _client_ip(request)

        if user is not None:
            login(request, user)
            _terminar_sesiones_previas(user, request)
            security_log.info('LOGIN_OK user=%s ip=%s', user.username, ip)
            
            # Redirigir según el rol
            try:
                perfil = user.perfilusuario
                if perfil.rol in ('MASTER', 'ADMINISTRADOR'):
                    return redirect('admin_dashboard')
                elif perfil.rol == 'AYUDANTE':
                    return redirect('ayudante_dashboard')
                elif perfil.rol in ('ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO'):
                    return redirect('abogado_dashboard')
                elif perfil.rol in ('BUSCADOR', 'ABOG3_BUSCADOR'):
                    return redirect('buscador_dashboard')
                elif perfil.rol == 'ADMIN1_AGENDADOR':
                    return redirect('admin1_dashboard')
                elif perfil.rol == 'ADMIN2_ARCHIVO':
                    return redirect('admin2_dashboard')
                elif perfil.rol == 'ADMIN3_NOTIFICADOR':
                    return redirect('admin3_dashboard')
                elif perfil.rol == 'SECRETARIO_ACTAS':
                    return redirect('vocal_dashboard')
                elif perfil.rol == 'ASESOR_JURIDICO':
                    return redirect('buscador_dashboard')
                elif perfil.rol == 'ASESOR_JEFE':
                    return redirect('asesor_jefe_dashboard')
                else:
                    messages.error(request, f'Rol no reconocido: {perfil.rol}')
                    logout(request)
                    return redirect('login')
            except PerfilUsuario.DoesNotExist:
                messages.error(request, 'Tu usuario no tiene un perfil asignado')
                logout(request)
                return redirect('login')
        else:
            # No loguear el password ni stacks; solo username intentado e IP.
            security_log.warning('LOGIN_FAIL user=%s ip=%s', username, ip)
            messages.error(request, 'Usuario o contraseña incorrectos')

    return render(request, 'tpe_app/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')


@login_required
def cambiar_password(request):
    if request.method == 'POST':
        password_actual  = request.POST.get('password_actual', '')
        password_nueva   = request.POST.get('password_nueva', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not request.user.check_password(password_actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
        elif password_nueva != password_confirm:
            messages.error(request, 'La nueva contraseña y la confirmación no coinciden.')
        else:
            # Aplica TODOS los validadores de AUTH_PASSWORD_VALIDATORS
            # (longitud, complejidad, similitud al user, contrasenas comunes, etc.)
            try:
                validate_password(password_nueva, user=request.user)
            except ValidationError as e:
                for msg in e.messages:
                    messages.error(request, msg)
            else:
                request.user.set_password(password_nueva)
                request.user.save()
                update_session_auth_hash(request, request.user)  # mantiene la sesión activa
                security_log.info(
                    'PASSWORD_CHANGED user=%s ip=%s',
                    request.user.username, _client_ip(request),
                )
                messages.success(request, 'Contraseña cambiada correctamente.')
                return redirect('cambiar_password')

    return render(request, 'tpe_app/cambiar_password.html')
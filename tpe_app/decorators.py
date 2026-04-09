# tpe_app/decorators.py
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps

def rol_requerido(*roles_permitidos):
    """
    Decorador para proteger vistas según el rol del usuario.
    Uso: @rol_requerido('ADMINISTRADOR', 'ABOGADO')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                perfil = request.user.perfilusuario
                if perfil.rol not in roles_permitidos:
                    raise PermissionDenied("No tienes permisos para acceder a esta página")
                if not perfil.activo:
                    raise PermissionDenied("Tu cuenta está desactivada")
                return view_func(request, *args, **kwargs)
            except AttributeError:
                raise PermissionDenied("No tienes un perfil asignado")
        return wrapper
    return decorator

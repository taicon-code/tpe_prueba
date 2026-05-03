# tpe_app/decorators.py
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps

def rol_requerido(*roles_permitidos):
    """
    Decorador para proteger vistas según el rol del usuario.
    Uso: @rol_requerido('ADMINISTRADOR', 'ABOGADO')

    MASTER tiene acceso automático a todas las vistas.
    Adjunta el perfil a request.perfil para acceso fácil en las vistas.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            from tpe_app.models import PerfilUsuario

            if request.user.is_superuser:
                # Para superusuarios, crear un perfil simulado
                class PerfirFake:
                    rol = 'MASTER'
                    activo = True
                request.perfil = PerfirFake()
                return view_func(request, *args, **kwargs)

            try:
                # Buscar explícitamente el perfil en lugar de usar la relación inversa
                perfil = PerfilUsuario.objects.get(user=request.user)

                # Verificar que el perfil esté activo
                if not perfil.activo:
                    raise PermissionDenied("Tu cuenta está desactivada. Contacta al administrador.")

                # MASTER tiene acceso a todo
                if perfil.rol == 'MASTER':
                    request.perfil = perfil  # Adjuntar perfil a request
                    return view_func(request, *args, **kwargs)

                # Otros roles requieren estar en la lista de permitidos
                if perfil.rol not in roles_permitidos:
                    roles_requeridos = ', '.join(roles_permitidos) if roles_permitidos else 'ninguno'
                    raise PermissionDenied(
                        f"Tu rol ({perfil.get_rol_display()}) no tiene acceso a esta página. "
                        f"Se requiere uno de: {roles_requeridos}"
                    )

                request.perfil = perfil  # Adjuntar perfil a request
                return view_func(request, *args, **kwargs)

            except PerfilUsuario.DoesNotExist:
                raise PermissionDenied(
                    "Tu usuario no tiene un perfil asignado. "
                    "Contacta al administrador del sistema para que te cree un perfil."
                )
            except AttributeError as e:
                raise PermissionDenied(f"Error en la configuración del usuario: {str(e)}")
        return wrapper
    return decorator

# tpe_app/decorators.py
import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps

logger = logging.getLogger(__name__)


# ============================================================
# Conjuntos de roles reutilizables
# ============================================================
# NOTA: MASTER y superusers tienen acceso automatico via rol_requerido(),
# por lo que NO es necesario incluirlos en estas tuplas.

# Whitelist amplia: todos los roles operativos del TPE.
# Usar para endpoints de exportacion (PDF/Excel) y consulta de datos sensibles
# donde queremos excluir solo a usuarios sin rol o desactivados.
ROLES_OPERATIVOS = (
    'ADMINISTRADOR',
    'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR',
    'ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR',
    'SECRETARIO_ACTAS', 'ASESOR_JEFE', 'ASESOR_JURIDICO',
    'AYUDANTE', 'BUSCADOR',
)

# Roles autorizados a modificar datos de Personal Militar (foto, edicion).
ROLES_REGISTRO_PM = (
    'AYUDANTE', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMINISTRADOR',
)

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

            logger.debug(f"[{view_func.__name__}] Usuario: {request.user.username}, Autenticado: {request.user.is_authenticated}, Superuser: {request.user.is_superuser}")

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

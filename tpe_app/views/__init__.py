# tpe_app/views/__init__.py
from .auth_views import login_view, logout_view
from .admin_views import admin_dashboard, crear_usuario_con_rol
from .abogado_views import abogado_dashboard
from .abogado_documentos_views import (
    abogado_auto_excusa_crear,
    abogado_autotpe_crear,
    abogado_dictamen_crear,
    abogado_res_crear,
    abogado_rr_crear,
    abogado_sumario_detalle,
)
from .buscador_views import buscador_dashboard, upload_foto_pm
from .administrativo_views import (
    administrativo_dashboard,
    registrar_sumario,
    agendar_sumario,
    registrar_rr,
    agendar_rr,
    crear_agenda,
    lista_agendas,
    editar_agenda_resultado,
)
from .export_views import export_person_pdfs_zip, export_person_excel
from .vocal_views import vocal_dashboard, vocal_agenda_detalle, vocal_confirmar_dictamen

# tpe_app/views/__init__.py
from .auth_views import login_view, logout_view
from .admin_views import admin_dashboard, crear_usuario_con_rol
from .abogado_views import abogado_dashboard, abogado_entregar_carpeta
from .abogado_documentos_views import (
    abogado_auto_excusa_crear,
    abogado_autotpe_crear,
    abogado_autotpe_ejecutoria_crear,
    abogado_dictamen_crear,
    abogado_res_crear,
    abogado_rr_crear,
    abogado_sumario_detalle,
    abogado_confirmar_recepcion,
    abogado_devolver_carpeta,
)
from .buscador_views import buscador_dashboard, upload_foto_pm
from .admin1_views import (
    admin1_dashboard,
    registrar_sumario,
    autocomplete_pm,
    agendar_sumario,
    registrar_rr,
    agendar_rr,
    crear_agenda,
    lista_agendas,
    ver_agenda_detalle,
    editar_agenda_resultado,
    gestionar_abogados_sim,
    admin1_ordenar_ejecutoria,
)
from .admin2_views import (
    admin2_dashboard,
    admin2_entregar_carpeta,
    admin2_recibir_carpeta,
    admin2_confirmar_recepcion,
    subir_pdf_res,
    ver_historial_custodia_sim,
)
from .admin3_views import (
    admin3_dashboard,
)
from .export_views import export_person_pdfs_zip, export_person_excel, export_person_historial_pdf
from .vocal_views import vocal_dashboard, vocal_agenda_detalle, vocal_confirmar_dictamen
from .ayudante_views import (
    ayudante_dashboard,
    ayudante_lista_res,
    ayudante_lista_res_sin_pdf,
    ayudante_registrar_res,
    ayudante_registrar_notificacion,
    ayudante_registrar_notificacion_rr,
    ayudante_registrar_rap,
    ayudante_registrar_raee,
    ayudante_registrar_autotpe,
)
from .ejecutoria_views import (
    pendientes_ejecutoria,
    crear_auto_ejecutoria,
)

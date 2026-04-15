from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards por rol
    path('panel-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel-admin/usuarios/crear/', views.crear_usuario_con_rol, name='crear_usuario'),
    path('abogado/dashboard/', views.abogado_dashboard, name='abogado_dashboard'),
    path('abogado/sumarios/<int:sim_id>/', views.abogado_sumario_detalle, name='abogado_sumario_detalle'),
    path('abogado/sumarios/<int:sim_id>/dictamen/nuevo/', views.abogado_dictamen_crear, name='abogado_dictamen_crear'),
    path('abogado/sumarios/<int:sim_id>/dictamen/<int:dictamen_id>/res/nueva/', views.abogado_res_crear, name='abogado_res_crear'),
    path('abogado/sumarios/<int:sim_id>/res/<int:res_id>/rr/nueva/', views.abogado_rr_crear, name='abogado_rr_crear'),
    path('abogado/sumarios/<int:sim_id>/dictamen/<int:dictamen_id>/autotpe/nuevo/', views.abogado_autotpe_crear, name='abogado_autotpe_crear'),
    path('abogado/sumarios/<int:sim_id>/auto-excusa/crear/', views.abogado_auto_excusa_crear, name='abogado_auto_excusa_crear'),
    path('buscador/dashboard/', views.buscador_dashboard, name='buscador_dashboard'),
    path('administrativo/dashboard/', views.administrativo_dashboard, name='administrativo_dashboard'),

    # Vocal TPE - Secretario de Actas
    path('vocal/dashboard/', views.vocal_dashboard, name='vocal_dashboard'),
    path('vocal/agenda/<int:ag_id>/', views.vocal_agenda_detalle, name='vocal_agenda_detalle'),
    path('vocal/dictamen/<int:dic_id>/confirmar/', views.vocal_confirmar_dictamen, name='vocal_confirmar_dictamen'),

    # Administrativo - Sumarios
    path('administrativo/sumarios/registrar/', views.registrar_sumario, name='registrar_sumario'),
    path('administrativo/sumarios/agendar/', views.agendar_sumario, name='agendar_sumario'),
    path('administrativo/rr/registrar/', views.registrar_rr, name='registrar_rr'),
    path('administrativo/rr/agendar/', views.agendar_rr, name='agendar_rr'),

    # ✅ NUEVO v3.1: Custodia de carpetas (Admin2)
    # path('administrativo/custodia/<int:sim_id>/entregar/', views.admin2_entregar_carpeta, name='entregar_carpeta'),
    # path('administrativo/custodia/<int:sim_id>/devolucion/', views.admin2_recibir_carpeta, name='devolucion_carpeta'),
    # path('administrativo/custodia/<int:sim_id>/historial/', views.historial_custodia, name='historial_custodia'),

    # ✅ NUEVO v3.1: Historial de sumarios (interno y externo)
    # path('sim/<int:sim_id>/historial/', views.historial_externo_sim, name='historial_externo_sim'),
    # path('admin/sim/<int:sim_id>/auditoria/', views.historial_auditoria_sim, name='historial_auditoria_sim'),
    
    # Buscador - subir foto de PM
    path('buscador/pm/<int:pm_id>/foto/', views.upload_foto_pm, name='upload_foto_pm'),

    # Exportación de historial (desde buscador_dashboard)
    path('buscador/dashboard/<int:personal_id>/exportar/pdfs/', views.export_person_pdfs_zip, name='export_pdfs_zip'),
    path('buscador/dashboard/<int:personal_id>/exportar/excel/', views.export_person_excel, name='export_excel'),
    
    # Redirección por defecto (opcional)
    path('', views.login_view, name='index'),
]

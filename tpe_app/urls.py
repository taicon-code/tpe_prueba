from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cuenta/cambiar-password/', views.cambiar_password, name='cambiar_password'),
    
    # Dashboards por rol
    path('panel-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel-admin/usuarios/crear/', views.crear_usuario_con_rol, name='crear_usuario'),
    path('abogado/dashboard/', views.abogado_dashboard, name='abogado_dashboard'),
    path('abogado/sumarios/<int:sim_id>/', views.abogado_sumario_detalle, name='abogado_sumario_detalle'),
    path('abogado/sumarios/<int:sim_id>/entregar-carpeta/', views.abogado_entregar_carpeta, name='abogado_entregar_carpeta'),
    path('abogado/sumarios/<int:sim_id>/confirmar-recepcion/', views.abogado_confirmar_recepcion, name='abogado_confirmar_recepcion'),
    path('abogado/sumarios/<int:sim_id>/devolver-carpeta/', views.abogado_devolver_carpeta, name='abogado_devolver_carpeta'),
    path('abogado/sumarios/<int:sim_id>/dictamen/nuevo/', views.abogado_dictamen_crear, name='abogado_dictamen_crear'),
    path('abogado/sumarios/<int:sim_id>/dictamen/<int:dictamen_id>/res/nueva/', views.abogado_res_crear, name='abogado_res_crear'),
    path('abogado/sumarios/<int:sim_id>/res/<int:res_id>/rr/nueva/', views.abogado_rr_crear, name='abogado_rr_crear'),
    path('abogado/sumarios/<int:sim_id>/dictamen/<int:dictamen_id>/autotpe/nuevo/', views.abogado_autotpe_crear, name='abogado_autotpe_crear'),
    path('abogado/sumarios/<int:sim_id>/auto-excusa/crear/', views.abogado_auto_excusa_crear, name='abogado_auto_excusa_crear'),
    path('abogado/sumarios/<int:sim_id>/auto-ejecutoria/crear/', views.abogado_autotpe_ejecutoria_crear, name='abogado_autotpe_ejecutoria_crear'),
    path('buscador/dashboard/', views.buscador_dashboard, name='buscador_dashboard'),
    path('admin1/dashboard/', views.admin1_dashboard, name='admin1_dashboard'),
    path('admin2/dashboard/', views.admin2_dashboard, name='admin2_dashboard'),
    path('admin3/dashboard/', views.admin3_dashboard, name='admin3_dashboard'),

    # Vocal TPE - Secretario de Actas
    path('vocal/dashboard/', views.vocal_dashboard, name='vocal_dashboard'),
    path('vocal/agenda/<int:ag_id>/', views.vocal_agenda_detalle, name='vocal_agenda_detalle'),
    path('vocal/dictamen/<int:dic_id>/confirmar/', views.vocal_confirmar_dictamen, name='vocal_confirmar_dictamen'),

    # ✅ NUEVO: Ayudante - Registro de datos históricos
    path('ayudante/', views.ayudante_dashboard, name='ayudante_dashboard'),
    path('ayudante/res/', views.ayudante_lista_res, name='ayudante_lista_res'),
    path('ayudante/res/sin-pdf/', views.ayudante_lista_res_sin_pdf, name='ayudante_lista_res_sin_pdf'),
    path('ayudante/res/nueva/', views.ayudante_registrar_res, name='ayudante_registrar_res'),
    path('ayudante/res/<int:res_id>/notificar/', views.ayudante_registrar_notificacion, name='ayudante_registrar_notificacion'),
    path('ayudante/rr/<int:rr_id>/notificar/', views.ayudante_registrar_notificacion_rr, name='ayudante_registrar_notificacion_rr'),
    path('ayudante/auto/<int:auto_id>/notificar/', views.ayudante_registrar_notificacion_auto, name='ayudante_registrar_notificacion_auto'),
    path('ayudante/rap/nuevo/', views.ayudante_registrar_rap, name='ayudante_registrar_rap'),
    path('ayudante/raee/nuevo/', views.ayudante_registrar_raee, name='ayudante_registrar_raee'),
    path('ayudante/autotpe/nuevo/', views.ayudante_registrar_autotpe, name='ayudante_registrar_autotpe'),

    # ✅ NUEVO v3.3: Wizard de ingreso rápido histórico (4 pasos)
    path('ayudante/wizard/paso1/', views.ayudante_wizard_paso1, name='ayudante_wizard_paso1'),
    path('ayudante/wizard/<int:sim_id>/paso2/', views.ayudante_wizard_paso2, name='ayudante_wizard_paso2'),
    path('ayudante/wizard/<int:sim_id>/paso3/', views.ayudante_wizard_paso3, name='ayudante_wizard_paso3'),
    path('ayudante/wizard/<int:sim_id>/paso4/', views.ayudante_wizard_paso4, name='ayudante_wizard_paso4'),
    path('ayudante/wizard/<int:sim_id>/resumen/', views.ayudante_wizard_resumen, name='ayudante_wizard_resumen'),
    path('ayudante/wizard/buscar-sim/', views.ayudante_wizard_buscar_sim, name='ayudante_wizard_buscar_sim'),

    # Admin1 - Sumarios y Agendas
    path('admin1/sumarios/registrar/', views.registrar_sumario, name='registrar_sumario'),
    path('admin1/sumarios/autocomplete-pm/', views.autocomplete_pm, name='autocomplete_pm'),
    path('admin1/sumarios/agendar/', views.agendar_sumario, name='agendar_sumario'),
    path('admin1/rr/registrar/', views.registrar_rr, name='registrar_rr'),
    path('admin1/rr/agendar/', views.agendar_rr, name='agendar_rr'),
    path('admin1/sumarios/<int:sim_id>/abogados/', views.gestionar_abogados_sim, name='gestionar_abogados_sim'),

    # ✅ NUEVO v3.2: Gestión de Agendas (Admin1)
    path('admin1/agendas/crear/', views.crear_agenda, name='crear_agenda'),
    path('admin1/agendas/', views.lista_agendas, name='lista_agendas'),
    path('admin1/agendas/<int:ag_id>/', views.ver_agenda_detalle, name='ver_agenda_detalle'),
    path('admin1/agendas/<int:ag_id>/resultado/', views.editar_agenda_resultado, name='agenda_resultado'),

    # ✅ NUEVO v3.1: Custodia de carpetas (Admin2)
    path('admin2/custodia/<int:sim_id>/entregar/', views.admin2_entregar_carpeta, name='admin2_entregar_carpeta'),
    path('admin2/custodia/<int:sim_id>/recibir/', views.admin2_recibir_carpeta, name='admin2_recibir_carpeta'),
    path('admin2/custodia/<int:sim_id>/confirmar/', views.admin2_confirmar_recepcion, name='admin2_confirmar_recepcion'),
    path('admin2/custodia/<int:sim_id>/historial/', views.ver_historial_custodia_sim, name='ver_historial_custodia'),

    # ✅ NUEVO: Subir PDF de Resoluciones (Administrador)
    path('admin1/res/<int:res_id>/subir-pdf/', views.subir_pdf_res, name='subir_pdf_res'),
    # path('admin1/custodia/<int:sim_id>/historial/', views.historial_custodia, name='historial_custodia'),

    # ✅ NUEVO v3.1: Historial de sumarios (interno y externo)
    # path('sim/<int:sim_id>/historial/', views.historial_externo_sim, name='historial_externo_sim'),
    # path('admin/sim/<int:sim_id>/auditoria/', views.historial_auditoria_sim, name='historial_auditoria_sim'),
    
    # Buscador - Detalle de SIM y subir foto
    path('buscador/sim/<int:sim_id>/', views.detalles_sim, name='detalles_sim'),
    path('buscador/sim/<int:sim_id>/exportar/pdf/', views.export_sim_pdf, name='export_sim_pdf'),
    path('buscador/sim/<int:sim_id>/exportar/excel/', views.export_sim_excel, name='export_sim_excel'),
    path('buscador/sim/<int:sim_id>/custodia/pdf/', views.export_custodia_pdf, name='export_custodia_pdf'),
    path('buscador/pm/<int:pm_id>/foto/', views.upload_foto_pm, name='upload_foto_pm'),

    # Exportación de historial (desde buscador_dashboard)
    path('buscador/dashboard/<int:personal_id>/exportar/pdfs/', views.export_person_pdfs_zip, name='export_pdfs_zip'),
    path('buscador/dashboard/<int:personal_id>/exportar/excel/', views.export_person_excel, name='export_excel'),
    
    # Auto de Ejecutoria (semi-automático)
    path('ejecutoria/pendientes/', views.pendientes_ejecutoria, name='pendientes_ejecutoria'),
    path('ejecutoria/crear/<str:origen>/<int:origen_id>/', views.crear_auto_ejecutoria, name='crear_auto_ejecutoria'),
    path('admin1/ejecutoria/<int:res_id>/entregar/', views.admin1_ordenar_ejecutoria, name='admin1_ordenar_ejecutoria'),

    # Archivo final SPRODA (flujo post-ejecutoria notificada)
    path('admin1/sim/<int:sim_id>/ordenar-archivo/', views.admin1_ordenar_archivo_sproda, name='admin1_ordenar_archivo_sproda'),
    path('admin2/sim/<int:sim_id>/confirmar-archivo/', views.admin2_confirmar_archivo_sproda, name='admin2_confirmar_archivo_sproda'),
    path('admin2/auto/<int:auto_id>/retorno-memo/', views.admin2_registrar_retorno_memo, name='admin2_registrar_retorno_memo'),

    # Redirección por defecto (opcional)
    path('', views.login_view, name='index'),
]

from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards por rol
    path('panel-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('abogado/dashboard/', views.abogado_dashboard, name='abogado_dashboard'),
    path('abogado/sumarios/<int:sim_id>/', views.abogado_sumario_detalle, name='abogado_sumario_detalle'),
    path('abogado/sumarios/<int:sim_id>/dictamen/nuevo/', views.abogado_dictamen_crear, name='abogado_dictamen_crear'),
    path('abogado/sumarios/<int:sim_id>/dictamen/<int:dictamen_id>/res/nueva/', views.abogado_res_crear, name='abogado_res_crear'),
    path('abogado/sumarios/<int:sim_id>/res/<int:res_id>/rr/nueva/', views.abogado_rr_crear, name='abogado_rr_crear'),
    path('abogado/sumarios/<int:sim_id>/dictamen/<int:dictamen_id>/autotpe/nuevo/', views.abogado_autotpe_crear, name='abogado_autotpe_crear'),
    path('buscador/dashboard/', views.buscador_dashboard, name='buscador_dashboard'),
    path('auxiliar/dashboard/', views.auxiliar_dashboard, name='auxiliar_dashboard'),

    # Auxiliar - Sumarios
    path('auxiliar/sumarios/registrar/', views.registrar_sumario, name='registrar_sumario'),
    path('auxiliar/sumarios/agendar/', views.agendar_sumario, name='agendar_sumario'),
    path('auxiliar/rr/registrar/', views.registrar_rr, name='registrar_rr'),
    path('auxiliar/rr/agendar/', views.agendar_rr, name='agendar_rr'),
    
    # Buscador - subir foto de PM
    path('buscador/pm/<int:pm_id>/foto/', views.upload_foto_pm, name='upload_foto_pm'),

    # Historial y Búsqueda
    path('historial/buscar/', views.buscar_historial_view, name='buscar_historial'),
    path('historial/<int:personal_id>/', views.historial_personal_detalle, name='historial_detalle'),
    
    # Redirección por defecto (opcional)
    path('', views.login_view, name='index'),
]

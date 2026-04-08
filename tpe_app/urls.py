from django.urls import path
from . import views



urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards por rol
    path('panel-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('abogado/dashboard/', views.abogado_dashboard, name='abogado_dashboard'),
    path('buscador/dashboard/', views.buscador_dashboard, name='buscador_dashboard'),
    path('auxiliar/dashboard/', views.auxiliar_dashboard, name='auxiliar_dashboard'),
    
    # Historial y Búsqueda
    path('historial/buscar/', views.buscar_historial_view, name='buscar_historial'),
    path('historial/<int:personal_id>/', views.historial_personal_detalle, name='historial_detalle'),
    
    # Redirección por defecto (opcional, por ahora lo dejamos como login si entras a la raíz de la app)
    path('', views.login_view, name='index'),
]
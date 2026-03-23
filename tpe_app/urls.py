from django.urls import path
from . import views

app_name = 'tpe_app'

urlpatterns = [
    path('', views.buscar_historial_view, name='buscar_historial'),
    path('<int:personal_id>/', views.historial_personal_detalle, name='historial_detalle'),
]
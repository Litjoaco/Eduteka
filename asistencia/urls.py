from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_asistencia_view, name='registrar_asistencia'),
    path('registrar/<int:seccion_id>/', views.registrar_asistencia_seccion_view, name='registrar_asistencia_seccion'),
    path('historial/', views.historial_asistencia_view, name='historial_asistencia'),
    path('historial/<int:seccion_id>/', views.historial_seccion_view, name='historial_seccion'),
    path('exportar/<int:seccion_id>/', views.exportar_asistencia_excel, name='exportar_asistencia_excel'),
]

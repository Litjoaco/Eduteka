from django.urls import path
from . import views

urlpatterns = [
    path('', views.libro_calificaciones_view, name='libro_calificaciones'),
    path('evaluacion/crear/', views.crear_evaluacion_view, name='crear_evaluacion'),
    path('evaluacion/eliminar/<int:evaluacion_id>/', views.eliminar_evaluacion_view, name='eliminar_evaluacion'),
    path('guardar/', views.guardar_notas_view, name='guardar_notas'),
    path('exportar/<int:seccion_id>/<int:asignatura_id>/', views.exportar_notas_excel_view, name='exportar_notas_excel'),
    path('boletin/<int:estudiante_id>/', views.boletin_estudiante_view, name='boletin_estudiante'),
]


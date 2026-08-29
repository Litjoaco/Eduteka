from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_asistencia_view, name='registrar_asistencia'),
    path('registrar/<int:seccion_id>/', views.registrar_asistencia_seccion_view, name='registrar_asistencia_seccion'),
    path('historial/', views.historial_asistencia_view, name='historial_asistencia'),
    path('historial/<int:seccion_id>/', views.historial_seccion_view, name='historial_seccion'),
    path('exportar/<int:seccion_id>/', views.exportar_asistencia_excel, name='exportar_asistencia_excel'),

    # Asistencia Inteligente por Código QR
    path('qr/sala/<int:seccion_id>/', views.asistencia_qr_sala_view, name='asistencia_qr_sala'),
    path('qr/express/', views.asistencia_qr_express_view, name='asistencia_qr_express'),
    path('qr/carteles/', views.asistencia_qr_carteles_view, name='asistencia_qr_carteles'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard_profesor'),
    path('solicitudes/<int:solicitud_id>/aprobar/', views.aprobar_solicitud, name='aprobar_solicitud'),
    path('solicitudes/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
]
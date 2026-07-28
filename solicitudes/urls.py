from django.urls import path
from . import views

urlpatterns = [
    path('solicitar-acceso/', views.solicitar_acceso_view, name='solicitar_acceso'),
    path('solicitud-enviada/', views.solicitud_enviada_view, name='solicitud_enviada'),
]
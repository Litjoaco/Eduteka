from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_personal_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_usuarios_view, name='dashboard_usuario'),
    path('perfil/', views.perfil_usuario_view, name='perfil_usuario'),
    
    # Rutas para el Sistema de Firma Electrónica / PIN de 4 Dígitos
    path('pin/estado/', views.api_estado_pin, name='api_estado_pin'),
    path('pin/verificar/', views.api_verificar_pin, name='api_verificar_pin'),
    path('pin/establecer/', views.api_establecer_pin, name='api_establecer_pin'),
    path('pin/solicitar-reset/', views.api_solicitar_reset_pin, name='api_solicitar_reset_pin'),
    path('pin/verificar-reset/', views.api_verificar_reset_pin, name='api_verificar_reset_pin'),

    # Rutas para Recuperación de Contraseña por Correo
    path('password-reset/', views.solicitar_recuperacion_password_view, name='password_reset_solicitar'),
    path('password-reset/confirmar/<str:uidb64>/<str:token>/', views.confirmar_recuperacion_password_view, name='password_reset_confirmar'),
]
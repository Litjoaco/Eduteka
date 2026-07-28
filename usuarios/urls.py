from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_personal_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_usuarios_view, name='dashboard_usuario'),
]
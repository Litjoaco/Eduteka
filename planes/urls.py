from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.crear_plan, name='crear_plan'),
    path('editar/<int:pk>/', views.editar_plan, name='editar_plan'),
    path('eliminar/<int:pk>/', views.eliminar_plan, name='eliminar_plan'),
]



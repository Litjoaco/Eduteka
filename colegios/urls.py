from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_colegio_paso1_view, name='registro_colegio'),
    path('registro/paso-2/<int:colegio_id>/', views.registro_colegio_paso2_view, name='registro_colegio_paso2'),
    path('configuracion/paso-1/<int:colegio_id>/', views.configuracion_colegio_paso1_view, name='configuracion_colegio_paso1'),
    path('configuracion/paso-2/<int:colegio_id>/', views.configuracion_colegio_paso2_view, name='configuracion_colegio_paso2'),
    path('configuracion/paso-3/<int:colegio_id>/', views.configuracion_colegio_paso3_view, name='configuracion_colegio_paso3'),
    path('configuracion/paso-4/<int:colegio_id>/', views.configuracion_colegio_paso4_view, name='configuracion_colegio_paso4'),
    path('configuracion/paso-5/<int:colegio_id>/', views.configuracion_colegio_paso5_view, name='configuracion_colegio_paso5'),
]
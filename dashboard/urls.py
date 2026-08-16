from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard_profesor'),
    path('superadmin/', views.dashboard_superadmin_view, name='dashboard_superadmin'),
    path('superadmin/colegios/', views.dashboard_superadmin_colegios_view, name='dashboard_superadmin_colegios'),
    path('superadmin/planes/', views.dashboard_superadmin_planes_view, name='dashboard_superadmin_planes'),
    path('superadmin/facturacion/', views.dashboard_superadmin_facturacion_view, name='dashboard_superadmin_facturacion'),
    path('superadmin/ordenes/', views.dashboard_superadmin_ordenes_view, name='dashboard_superadmin_ordenes'),
    path('superadmin/modulos-erp/', views.dashboard_superadmin_modulos_erp_view, name='dashboard_superadmin_modulos_erp'),
    path('superadmin/configuracion/', views.dashboard_superadmin_configuracion_view, name='dashboard_superadmin_configuracion'),
    path('superadmin/estadisticas/', views.dashboard_superadmin_estadisticas_view, name='dashboard_superadmin_estadisticas'),
    # Control de Accesos
    path('superadmin/roles/', views.dashboard_superadmin_roles_view, name='dashboard_superadmin_roles'),
    path('superadmin/usuarios/', views.dashboard_superadmin_usuarios_view, name='dashboard_superadmin_usuarios'),
    path('superadmin/solicitudes-global/', views.dashboard_superadmin_solicitudes_view, name='dashboard_superadmin_solicitudes'),
    # Éxito del Cliente (CSM)
    path('superadmin/onboarding/', views.dashboard_superadmin_onboarding_view, name='dashboard_superadmin_onboarding'),
    # Comunicación
    path('superadmin/comunicados/', views.dashboard_superadmin_comunicados_view, name='dashboard_superadmin_comunicados'),
    path('solicitudes/<int:solicitud_id>/aprobar/', views.aprobar_solicitud, name='aprobar_solicitud'),
    path('solicitudes/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
]
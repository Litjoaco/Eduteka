from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard_profesor'),
    path('superadmin/', views.dashboard_superadmin_view, name='dashboard_superadmin'),
    path('superadmin/colegios/', views.dashboard_superadmin_colegios_view, name='dashboard_superadmin_colegios'),
    path('superadmin/planes/', views.dashboard_superadmin_planes_view, name='dashboard_superadmin_planes'),
    path('superadmin/facturacion/', views.dashboard_superadmin_facturacion_view, name='dashboard_superadmin_facturacion'),
    path('superadmin/facturacion/emitir-manual/', views.dashboard_superadmin_factura_manual_view, name='emitir_factura_manual'),
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
    # Seguridad y Auditoría
    path('superadmin/auditoria/', TemplateView.as_view(template_name='dashboard_superadmin_auditoria.html'), name='dashboard_superadmin_auditoria'),
    # Gestión Académica Global
    path('superadmin/academico/', views.dashboard_superadmin_academico_view, name='dashboard_superadmin_academico'),
    # Generador de Reportes Personalizables (openpyxl)
    path('superadmin/reportes/', TemplateView.as_view(template_name='dashboard_superadmin_reportes.html'), name='dashboard_superadmin_reportes'),
    path('superadmin/reportes/descargar/', views.exportar_reporte_colegios_excel, name='descargar_excel'),
    path('solicitudes/<int:solicitud_id>/aprobar/', views.aprobar_solicitud, name='aprobar_solicitud'),
    path('solicitudes/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
]
from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard_profesor'),
    path('superadmin/', views.dashboard_superadmin_view, name='dashboard_superadmin'),
    path('superadmin/colegios/', views.dashboard_superadmin_colegios_view, name='dashboard_superadmin_colegios'),
    path('superadmin/planes/', views.dashboard_superadmin_planes_view, name='dashboard_superadmin_planes'),
    path('superadmin/facturacion/', views.dashboard_superadmin_facturacion_view, name='dashboard_superadmin_facturacion'),
    path('superadmin/facturacion/<int:factura_id>/pdf/', views.superadmin_descargar_factura_pdf_view, name='superadmin_descargar_factura_pdf'),
    path('superadmin/facturacion/<int:factura_id>/xml/', views.superadmin_descargar_factura_xml_view, name='superadmin_descargar_factura_xml'),
    path('superadmin/facturacion/<int:factura_id>/reenviar-sii/', views.superadmin_reenviar_factura_sii_view, name='superadmin_reenviar_factura_sii'),
    path('superadmin/facturacion/emitir-manual/', views.dashboard_superadmin_factura_manual_view, name='emitir_factura_manual'),
    path('superadmin/ordenes/', views.dashboard_superadmin_ordenes_view, name='dashboard_superadmin_ordenes'),
    path('superadmin/ordenes/<int:orden_id>/aprobar/', views.superadmin_aprobar_orden_view, name='superadmin_aprobar_orden'),
    path('superadmin/ordenes/<int:orden_id>/descargar/', views.superadmin_descargar_orden_pdf_view, name='superadmin_descargar_orden_pdf'),
    path('superadmin/recordatorio/<int:orden_id>/', views.superadmin_enviar_recordatorio_view, name='superadmin_enviar_recordatorio'),
    path('superadmin/modulos-erp/', views.dashboard_superadmin_modulos_erp_view, name='dashboard_superadmin_modulos_erp'),
    path('superadmin/configuracion/', views.dashboard_superadmin_configuracion_view, name='dashboard_superadmin_configuracion'),
    path('superadmin/estadisticas/', views.dashboard_superadmin_estadisticas_view, name='dashboard_superadmin_estadisticas'),
    # Control de Accesos
    path('superadmin/roles/', views.dashboard_superadmin_roles_view, name='dashboard_superadmin_roles'),
    path('superadmin/roles/<int:rol_id>/eliminar/', views.superadmin_eliminar_rol_view, name='superadmin_eliminar_rol'),
    path('superadmin/usuarios/', views.dashboard_superadmin_usuarios_view, name='dashboard_superadmin_usuarios'),
    path('superadmin/solicitudes-global/', views.dashboard_superadmin_solicitudes_view, name='dashboard_superadmin_solicitudes'),
    path('superadmin/solicitudes/<int:solicitud_id>/aprobar/', views.superadmin_aprobar_solicitud, name='superadmin_aprobar_solicitud'),
    path('superadmin/solicitudes/<int:solicitud_id>/rechazar/', views.superadmin_rechazar_solicitud, name='superadmin_rechazar_solicitud'),
    # Éxito del Cliente (CSM)
    path('superadmin/onboarding/', views.dashboard_superadmin_onboarding_view, name='dashboard_superadmin_onboarding'),
    # Comunicación
    path('superadmin/comunicados/', views.dashboard_superadmin_comunicados_view, name='dashboard_superadmin_comunicados'),
    # Seguridad y Auditoría
    path('superadmin/auditoria/', views.dashboard_superadmin_auditoria_view, name='dashboard_superadmin_auditoria'),
    # Gestión Académica Global
    path('superadmin/academico/', views.dashboard_superadmin_academico_view, name='dashboard_superadmin_academico'),
    # Generador de Reportes Personalizables (openpyxl)
    path('superadmin/reportes/', views.dashboard_superadmin_reportes_view, name='dashboard_superadmin_reportes'),
    path('superadmin/reportes/descargar/', views.exportar_reporte_colegios_excel, name='descargar_excel'),
    path('superadmin/finanzas/exportar/', views.exportar_finanzas_excel, name='exportar_finanzas_excel'),
    path('solicitudes/<int:solicitud_id>/aprobar/', views.aprobar_solicitud, name='aprobar_solicitud'),
    path('solicitudes/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
]
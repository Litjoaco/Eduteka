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
    path('configuracion/paso-6/<int:colegio_id>/', views.configuracion_colegio_paso6_view, name='configuracion_colegio_paso6'),
    path('configuracion/finalizando/<int:colegio_id>/', views.configuracion_colegio_finalizando_view, name='configuracion_colegio_finalizando'),

    # Gestión de Estudiantes
    path('estudiantes/', views.listar_estudiantes_view, name='listar_estudiantes'),
    path('estudiantes/matricular/', views.matricular_estudiante_view, name='matricular_estudiante'),
    path('estudiantes/editar/<int:estudiante_id>/', views.editar_estudiante_view, name='editar_estudiante'),
    path('estudiantes/baja/<int:estudiante_id>/', views.baja_estudiante_view, name='baja_estudiante'),

    # Gestión de Asignaturas
    path('asignaturas/', views.listar_asignaturas_view, name='listar_asignaturas'),
    path('asignaturas/crear/', views.crear_asignatura_view, name='crear_asignatura'),
    path('asignaturas/editar/<int:asignatura_id>/', views.editar_asignatura_view, name='editar_asignatura'),
    path('asignaturas/eliminar/<int:asignatura_id>/', views.eliminar_asignatura_view, name='eliminar_asignatura'),
    path('asignaturas/precargar/', views.precargar_asignaturas_base_view, name='precargar_asignaturas_base'),
    path('asignaturas/asignar-docente/<int:asignatura_id>/', views.asignar_docente_asignatura_view, name='asignar_docente_asignatura'),

    # Gestión de Cursos y Secciones
    path('cursos/', views.listar_cursos_view, name='listar_cursos'),
    path('cursos/crear/', views.crear_curso_view, name='crear_curso'),
    path('cursos/editar/<int:curso_id>/', views.editar_curso_view, name='editar_curso'),
    path('cursos/baja/<int:curso_id>/', views.baja_curso_view, name='baja_curso'),
    path('secciones/crear/<int:curso_id>/', views.crear_seccion_view, name='crear_seccion'),
    path('secciones/baja/<int:seccion_id>/', views.baja_seccion_view, name='baja_seccion'),
    path('secciones/asignar-profesor-jefe/<int:seccion_id>/', views.asignar_profesor_jefe_view, name='asignar_profesor_jefe'),

    # Panel Docente: Mis Cursos y Materias
    path('mis-cursos/', views.mis_cursos_docente_view, name='mis_cursos_docente'),


    # Gestión de Personal y Roles
    path('personal/', views.listar_personal_view, name='listar_personal'),
    path('personal/crear-rol/', views.crear_rol_personalizado_view, name='crear_rol_personalizado'),
    path('personal/roles/guardar/', views.guardar_rol_permisos_view, name='guardar_rol_permisos'),
    path('personal/roles/eliminar/<int:rol_id>/', views.eliminar_rol_personalizado_view, name='eliminar_rol_personalizado'),
    path('personal/permisos-individuales/<int:miembro_id>/', views.guardar_permisos_individuales_personal_view, name='guardar_permisos_individuales_personal'),
    path('personal/editar/<int:miembro_id>/', views.editar_personal_view, name='editar_personal'),
    path('personal/asignar-materias/<int:miembro_id>/', views.asignar_asignaturas_docente_view, name='asignar_asignaturas_docente'),
    path('personal/baja/<int:miembro_id>/', views.baja_personal_view, name='baja_personal'),




    # Centro de Reportes y Estadísticas
    path('reportes/', views.centro_reportes_view, name='centro_reportes'),
    path('estadisticas/', views.estadisticas_colegio_view, name='estadisticas_colegio'),
    path('estadisticas/exportar-excel/', views.exportar_estadisticas_excel_view, name='exportar_estadisticas_excel'),

    # Módulo de Finanzas, Caja Chica y Facturas
    path('finanzas/', views.finanzas_dashboard_view, name='finanzas_dashboard'),
    path('finanzas/movimientos/crear/', views.crear_movimiento_financiero_view, name='crear_movimiento_financiero'),
    path('finanzas/movimientos/eliminar/<int:movimiento_id>/', views.eliminar_movimiento_financiero_view, name='eliminar_movimiento_financiero'),
    path('finanzas/facturas/crear/', views.crear_factura_view, name='crear_factura'),
    path('finanzas/facturas/pagar/<int:factura_id>/', views.pagar_factura_view, name='pagar_factura'),
    path('finanzas/facturas/eliminar/<int:factura_id>/', views.eliminar_factura_view, name='eliminar_factura'),
    path('finanzas/cuentas/crear/', views.crear_cuenta_financiera_view, name='crear_cuenta_financiera'),
    path('finanzas/categorias/crear/', views.crear_categoria_financiera_view, name='crear_categoria_financiera'),
    path('finanzas/exportar-excel/', views.exportar_finanzas_excel_view, name='exportar_finanzas_excel'),

    # Módulo de Inventario & Proveedores
    path('inventario/', views.inventario_dashboard_view, name='inventario_dashboard'),
    path('inventario/crear-item/', views.crear_item_inventario_view, name='crear_item_inventario'),
    path('inventario/ajustar-stock/<int:item_id>/', views.ajustar_stock_view, name='ajustar_stock'),
    path('inventario/eliminar-item/<int:item_id>/', views.eliminar_item_inventario_view, name='eliminar_item_inventario'),
    path('inventario/exportar-excel/', views.exportar_inventario_excel_view, name='exportar_inventario_excel'),

    path('proveedores/', views.proveedores_directorio_view, name='proveedores_directorio'),
    path('proveedores/crear/', views.crear_proveedor_view, name='crear_proveedor'),
    path('proveedores/editar/<int:proveedor_id>/', views.editar_proveedor_view, name='editar_proveedor'),
    path('proveedores/eliminar/<int:proveedor_id>/', views.eliminar_proveedor_view, name='eliminar_proveedor'),




    # Módulo de Talleres Extracurriculares (ACLES) & Asistencia
    path('talleres/', views.talleres_dashboard_view, name='talleres_dashboard'),
    path('talleres/crear/', views.crear_taller_view, name='crear_taller'),
    path('talleres/<int:taller_id>/', views.detalle_taller_view, name='detalle_taller'),
    path('talleres/<int:taller_id>/editar/', views.editar_taller_view, name='editar_taller'),
    path('talleres/<int:taller_id>/eliminar/', views.eliminar_taller_view, name='eliminar_taller'),
    path('talleres/<int:taller_id>/inscribir/', views.inscribir_estudiante_taller_view, name='inscribir_estudiante_taller'),
    path('talleres/<int:taller_id>/desinscribir/<int:inscripcion_id>/', views.desinscribir_estudiante_taller_view, name='desinscribir_estudiante_taller'),
    path('talleres/<int:taller_id>/asistencia/', views.tomar_asistencia_taller_view, name='tomar_asistencia_taller'),
    path('talleres/<int:taller_id>/asistencia/sesion/<int:sesion_id>/', views.detalle_sesion_taller_view, name='detalle_sesion_taller'),
    path('talleres/<int:taller_id>/asistencia/sesion/<int:sesion_id>/eliminar/', views.eliminar_sesion_taller_view, name='eliminar_sesion_taller'),

    path('configuracion/politicas/', views.configuracion_politicas_view, name='configuracion_politicas'),

    # Convivencia Escolar y Hoja de Vida
    path('convivencia/', views.convivencia_hub_view, name='convivencia_hub'),
    path('convivencia/<int:estudiante_id>/', views.hoja_vida_estudiante_view, name='hoja_vida_estudiante'),
    path('convivencia/anotacion/eliminar/<int:anotacion_id>/', views.eliminar_anotacion_view, name='eliminar_anotacion'),

    # Agenda y Calendario Escolar
    path('calendario/', views.calendario_escolar_view, name='calendario_escolar'),
    path('calendario/api/eventos/', views.api_eventos_calendario_view, name='api_eventos_calendario'),
    path('calendario/exportar-ical/', views.exportar_ical_agenda_view, name='exportar_ical_agenda'),
    path('calendario/eliminar/<int:evento_id>/', views.eliminar_evento_agenda_view, name='eliminar_evento_agenda'),

    # SIMCE y Diagnóstico Integral de Aprendizajes (DIA)
    path('simce/', views.simce_dashboard_view, name='simce_dashboard'),
    path('simce/crear/', views.crear_ensayo_simce_view, name='crear_ensayo_simce'),
    path('simce/ensayo/<int:ensayo_id>/', views.detalle_ensayo_simce_view, name='detalle_ensayo_simce'),
    path('simce/ensayo/<int:ensayo_id>/guardar/', views.guardar_resultados_ensayo_view, name='guardar_resultados_ensayo'),
    path('simce/ensayo/<int:ensayo_id>/eliminar/', views.eliminar_ensayo_simce_view, name='eliminar_ensayo_simce'),
    path('simce/historico/crear/', views.crear_historico_simce_view, name='crear_historico_simce'),
    path('simce/historico/eliminar/<int:historico_id>/', views.eliminar_historico_simce_view, name='eliminar_historico_simce'),
    path('simce/exportar-excel/', views.exportar_simce_excel_view, name='exportar_simce_excel'),
    path('simce/exportar-excel/<int:ensayo_id>/', views.exportar_simce_excel_view, name='exportar_ensayo_excel'),
]






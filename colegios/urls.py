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

    # Gestión de Cursos y Secciones
    path('cursos/', views.listar_cursos_view, name='listar_cursos'),
    path('cursos/crear/', views.crear_curso_view, name='crear_curso'),
    path('cursos/editar/<int:curso_id>/', views.editar_curso_view, name='editar_curso'),
    path('cursos/baja/<int:curso_id>/', views.baja_curso_view, name='baja_curso'),
    path('secciones/crear/<int:curso_id>/', views.crear_seccion_view, name='crear_seccion'),
    path('secciones/baja/<int:seccion_id>/', views.baja_seccion_view, name='baja_seccion'),

    # Gestión de Personal
    path('personal/', views.listar_personal_view, name='listar_personal'),
    path('personal/crear-rol/', views.crear_rol_personalizado_view, name='crear_rol_personalizado'),
    path('personal/editar/<int:miembro_id>/', views.editar_personal_view, name='editar_personal'),
    path('personal/asignar-materias/<int:miembro_id>/', views.asignar_asignaturas_docente_view, name='asignar_asignaturas_docente'),
    path('personal/baja/<int:miembro_id>/', views.baja_personal_view, name='baja_personal'),



    # Centro de Reportes
    path('reportes/', views.centro_reportes_view, name='centro_reportes'),

    # Configuración de Políticas Académicas
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

    # Configuración de Módulos
    path('actualizar-modulo/', views.actualizar_modulo_colegio, name='actualizar_modulo_colegio'),

    # Detalles y Edición de Colegio (Superadmin)
    path('colegios/detalle/<int:pk>/', views.ver_detalle_colegio, name='ver_detalle_colegio'),
    path('colegios/editar/<int:pk>/', views.editar_colegio, name='editar_colegio'),
    path('colegios/<int:colegio_id>/suscripcion/editar/', views.editar_suscripcion_colegio, name='editar_suscripcion_colegio'),
]








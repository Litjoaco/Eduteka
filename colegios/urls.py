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
    path('personal/editar/<int:miembro_id>/', views.editar_personal_view, name='editar_personal'),
    path('personal/baja/<int:miembro_id>/', views.baja_personal_view, name='baja_personal'),
]
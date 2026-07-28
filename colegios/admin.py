from django.contrib import admin
from .models import (
    Colegio, Suscripcion, ColegioModulo, 
    ConfiguracionAcademica, CursoColegio, SeccionCurso,
    RolColegio, Permiso, RolPermiso
)

@admin.register(Colegio)
class ColegioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'administrador', 'estado', 'configuracion_completa', 'fecha_creacion')
    list_filter = ('estado', 'tipo_institucion', 'configuracion_completa')
    search_fields = ('nombre', 'correo_institucional')

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('colegio', 'plan', 'tipo_facturacion', 'estado', 'fecha_fin')
    list_filter = ('estado', 'tipo_facturacion', 'plan')

@admin.register(ColegioModulo)
class ColegioModuloAdmin(admin.ModelAdmin):
    list_display = ('colegio', 'modulo', 'activo', 'fecha_activacion')
    list_filter = ('activo', 'modulo')

@admin.register(ConfiguracionAcademica)
class ConfiguracionAcademicaAdmin(admin.ModelAdmin):
    list_display = ('colegio', 'anio_academico', 'periodo_academico', 'fecha_inicio', 'fecha_termino')

class SeccionCursoInline(admin.TabularInline):
    model = SeccionCurso
    extra = 1

@admin.register(CursoColegio)
class CursoColegioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'colegio', 'nivel', 'desde_letra', 'hasta_letra', 'activo')
    list_filter = ('nivel', 'activo')
    inlines = [SeccionCursoInline]

@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre', 'codigo')

class RolPermisoInline(admin.TabularInline):
    model = RolPermiso
    extra = 1

@admin.register(RolColegio)
class RolColegioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'colegio', 'es_base', 'activo')
    list_filter = ('es_base', 'activo')
    inlines = [RolPermisoInline]

from django.contrib import admin
from .models import SolicitudAcceso, MiembroColegio

@admin.register(SolicitudAcceso)
class SolicitudAccesoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'colegio', 'rol_solicitado', 'estado', 'fecha_solicitud')
    list_filter = ('estado', 'rol_solicitado')
    search_fields = ('usuario__username', 'colegio__nombre')

@admin.register(MiembroColegio)
class MiembroColegioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'colegio', 'rol', 'activo', 'fecha_ingreso')
    list_filter = ('activo', 'rol')
    search_fields = ('usuario__username', 'colegio__nombre')

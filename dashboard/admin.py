from django.contrib import admin
from .models import ComunicadoGlobal, ConfiguracionGlobal, SolicitudNuevoColegio


@admin.register(ComunicadoGlobal)
class ComunicadoGlobalAdmin(admin.ModelAdmin):
    list_display  = ('asunto', 'tipo_alerta', 'publico_objetivo', 'estado', 'fecha_creacion')
    list_filter   = ('tipo_alerta', 'estado', 'publico_objetivo')
    search_fields = ('asunto', 'mensaje')
    ordering      = ('-fecha_creacion',)


@admin.register(ConfiguracionGlobal)
class ConfiguracionGlobalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'sii_rut', 'sii_ambiente', 'mp_modo', 'updated_at')

    def has_add_permission(self, request):
        """Solo permite un registro (Singleton)."""
        return not ConfiguracionGlobal.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SolicitudNuevoColegio)
class SolicitudNuevoColegioAdmin(admin.ModelAdmin):
    list_display   = (
        'nombre_colegio', 'rut_sostenedor', 'email_contacto',
        'plan_solicitado', 'estado', 'created_at'
    )
    list_filter    = ('estado', 'plan_solicitado')
    search_fields  = ('nombre_colegio', 'rut_sostenedor', 'email_contacto', 'ciudad_comuna')
    ordering       = ('created_at',)
    readonly_fields = ('colegio_creado', 'updated_at', 'created_at')
    fieldsets = (
        ('Datos de la Institución', {
            'fields': ('nombre_colegio', 'rut_sostenedor', 'email_contacto',
                       'telefono', 'ciudad_comuna', 'nombre_administrador')
        }),
        ('Plan y Estado', {
            'fields': ('plan_solicitado', 'estado', 'notas_admin')
        }),
        ('Resultado (Solo Lectura)', {
            'fields': ('colegio_creado', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

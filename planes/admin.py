from django.contrib import admin
from .models import Modulo, Plan

@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'icono', 'activo', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('nombre',)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_mensual', 'precio_anual', 'recomendado', 'activo')
    list_filter = ('activo', 'recomendado')
    filter_horizontal = ('modulos',)

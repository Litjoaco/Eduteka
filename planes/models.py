from django.db import models
from django.utils import timezone

class Modulo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    icono = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"

    def __str__(self):
        return self.nombre


class Plan(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio_mensual = models.PositiveIntegerField(default=0)
    precio_anual = models.PositiveIntegerField(default=0)
    recomendado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    modulos = models.ManyToManyField(Modulo, blank=True, related_name='planes_asociados')
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Planes"

    def __str__(self):
        return self.nombre

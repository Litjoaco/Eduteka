from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from colegios.models import SeccionCurso, Estudiante

class RegistroAsistencia(models.Model):
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.CASCADE, related_name='registros_asistencia')
    fecha = models.DateField(default=timezone.now)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de Asistencia"
        verbose_name_plural = "Registros de Asistencia"
        unique_together = ('seccion', 'fecha')

    def __str__(self):
        return f"Asistencia {self.seccion.nombre} - {self.fecha}"

class DetalleAsistencia(models.Model):
    ESTADOS = [
        ('presente', 'Presente'),
        ('ausente', 'Ausente'),
        ('tarde', 'Atrasado'),
        ('justificado', 'Justificado'),
    ]

    registro = models.ForeignKey(RegistroAsistencia, on_delete=models.CASCADE, related_name='detalles')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='detalles_asistencia')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='presente')
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Detalle de Asistencia"
        verbose_name_plural = "Detalles de Asistencia"
        unique_together = ('registro', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.nombre_completo}: {self.get_estado_display()}"

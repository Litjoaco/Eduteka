from django.db import models

class ComunicadoGlobal(models.Model):
    PUBLICO_CHOICES = [
        ('todos', 'Todos los Colegios'),
        ('directores', 'Solo Directores y Admin'),
        ('premium', 'Colegios Plan Premium'),
        ('onboarding', 'Colegios en Onboarding'),
        ('morosos', 'Colegios con Pagos Pendientes'),
        ('profesores', 'Profesores y Docentes'),
    ]

    TIPO_CHOICES = [
        ('informativa', 'Informativa (Azul)'),
        ('mantenimiento', 'Mantenimiento (Naranja)'),
        ('urgente', 'Urgente / Sistema (Rojo)'),
    ]

    ESTADO_CHOICES = [
        ('enviado', 'Enviado'),
        ('programado', 'Programado'),
        ('borrador', 'Borrador'),
    ]

    asunto = models.CharField(max_length=255)
    publico_objetivo = models.CharField(max_length=50, choices=PUBLICO_CHOICES, default='todos')
    tipo_alerta = models.CharField(max_length=30, choices=TIPO_CHOICES, default='informativa')
    mensaje = models.TextField()
    banner_flotante = models.BooleanField(default=True)
    notificar_email = models.BooleanField(default=True)
    bloquear_popup = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado')
    tasa_lectura = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comunicado Global"
        verbose_name_plural = "Comunicados Globales"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.asunto} ({self.get_tipo_alerta_display()})"

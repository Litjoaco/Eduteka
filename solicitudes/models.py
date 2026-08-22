from django.db import models
from django.contrib.auth.models import User
from colegios.models import Colegio, RolColegio

class SolicitudAcceso(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_acceso')
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='solicitudes_acceso')
    rol_solicitado = models.CharField(max_length=50) # Ej: "profesor", "apoderado"
    mensaje = models.TextField(blank=True)
    motivo_rechazo = models.TextField(blank=True, null=True, help_text="Motivo del rechazo indicado por la dirección")
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Solicitud de Acceso"
        verbose_name_plural = "Solicitudes de Acceso"

    def __str__(self):
        return f"{self.usuario.username} - {self.colegio.nombre} ({self.get_estado_display()})"

class MiembroColegio(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='membresias_colegio')
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='miembros')
    rol = models.ForeignKey(RolColegio, on_delete=models.SET_NULL, null=True, related_name='miembros')
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Miembro de Colegio"
        verbose_name_plural = "Miembros de Colegio"
        unique_together = ('usuario', 'colegio')

    def __str__(self):
        rol_nombre = self.rol.nombre if self.rol else "Sin Rol"
        return f"{self.usuario.username} - {self.colegio.nombre} ({rol_nombre})"

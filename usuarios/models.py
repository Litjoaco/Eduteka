from django.db import models
from django.contrib.auth.models import User

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nombre_completo = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, blank=True, null=True, help_text="RUT del usuario")
    telefono = models.CharField(max_length=30, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

    def __str__(self):
        return self.nombre_completo or self.usuario.username

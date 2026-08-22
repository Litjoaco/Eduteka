from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nombre_completo = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, blank=True, null=True, help_text="RUT del usuario")
    telefono = models.CharField(max_length=30, blank=True)
    
    # Sistema de Firma Electrónica / PIN de 4 Dígitos
    pin_hash = models.CharField(max_length=128, blank=True, null=True, help_text="Hash seguro del PIN de 4 dígitos")
    pin_fecha_actualizacion = models.DateTimeField(null=True, blank=True, help_text="Fecha en que se configuró o renovó el PIN")
    pin_intentos_fallidos = models.PositiveIntegerField(default=0, help_text="Contador de intentos fallidos consecutivos")
    pin_bloqueado_hasta = models.DateTimeField(null=True, blank=True, help_text="Bloqueo temporal por intentos fallidos")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

    def __str__(self):
        return self.nombre_completo or self.usuario.username

    def tiene_pin(self):
        """Retorna True si el usuario tiene un PIN configurado."""
        return bool(self.pin_hash)

    def pin_expirado(self):
        """El PIN expira cada 90 días (3 meses)."""
        if not self.pin_hash or not self.pin_fecha_actualizacion:
            return True
        return (timezone.now() - self.pin_fecha_actualizacion) > timedelta(days=90)

    def dias_restantes_pin(self):
        """Retorna los días restantes de vigencia del PIN (0 si expiró)."""
        if not self.pin_hash or not self.pin_fecha_actualizacion:
            return 0
        dias_pasados = (timezone.now() - self.pin_fecha_actualizacion).days
        dias_restantes = 90 - dias_pasados
        return max(0, dias_restantes)

    def esta_bloqueado_pin(self):
        """Verifica si el PIN está temporalmente bloqueado."""
        if self.pin_bloqueado_hasta and self.pin_bloqueado_hasta > timezone.now():
            return True
        return False

    def establecer_pin(self, pin_str):
        """Establece un nuevo PIN de 4 dígitos con hash seguro."""
        if not pin_str or len(str(pin_str)) != 4 or not str(pin_str).isdigit():
            raise ValueError("El PIN debe tener exactamente 4 dígitos numéricos.")
        self.pin_hash = make_password(str(pin_str))
        self.pin_fecha_actualizacion = timezone.now()
        self.pin_intentos_fallidos = 0
        self.pin_bloqueado_hasta = None
        self.save(update_fields=['pin_hash', 'pin_fecha_actualizacion', 'pin_intentos_fallidos', 'pin_bloqueado_hasta'])

    def verificar_pin(self, pin_str):
        """
        Verifica si el PIN de 4 dígitos es válido.
        Retorna una tupla: (valido: bool, mensaje: str)
        """
        if not self.tiene_pin():
            return False, "No tienes un PIN configurado."
        
        if self.esta_bloqueado_pin():
            minutos = int((self.pin_bloqueado_hasta - timezone.now()).total_seconds() / 60) + 1
            return False, f"PIN bloqueado por seguridad. Intenta nuevamente en {minutos} minutos."

        if self.pin_expirado():
            return False, "Tu PIN de 4 dígitos ha expirado (política de 90 días). Debes renovarlo."

        if check_password(str(pin_str), self.pin_hash):
            if self.pin_intentos_fallidos > 0:
                self.pin_intentos_fallidos = 0
                self.save(update_fields=['pin_intentos_fallidos'])
            return True, "PIN correcto."
        else:
            self.pin_intentos_fallidos += 1
            if self.pin_intentos_fallidos >= 3:
                self.pin_bloqueado_hasta = timezone.now() + timedelta(minutes=15)
                self.save(update_fields=['pin_intentos_fallidos', 'pin_bloqueado_hasta'])
                return False, "Has superado 3 intentos fallidos. PIN bloqueado por 15 minutos."
            else:
                intentos_restantes = 3 - self.pin_intentos_fallidos
                self.save(update_fields=['pin_intentos_fallidos'])
                return False, f"PIN incorrecto. Te quedan {intentos_restantes} intento(s)."


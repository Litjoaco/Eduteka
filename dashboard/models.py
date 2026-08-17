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


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL DEL SISTEMA (Singleton)
# Solo existirá UN registro en esta tabla. Acceder siempre con .objects.first()
# ══════════════════════════════════════════════════════════════════════════════

class ConfiguracionGlobal(models.Model):
    """
    Parámetros globales de la plataforma Eduteka SaaS.
    Funciona como un Singleton: máximo un registro en la tabla.
    """

    SII_AMBIENTE_CHOICES = [
        ('produccion', 'Producción (Oficial)'),
        ('certificacion', 'Certificación / Staging (Testing)'),
    ]

    MP_MODO_CHOICES = [
        ('live', 'Live / Producción'),
        ('sandbox', 'Sandbox / Pruebas'),
    ]

    # ── Integración SII ───────────────────────────────────────────────────────
    sii_rut = models.CharField(
        max_length=20, blank=True, default='',
        verbose_name='RUT Emisor SII'
    )
    sii_razon_social = models.CharField(
        max_length=150, blank=True, default='',
        verbose_name='Razón Social SII'
    )
    sii_ambiente = models.CharField(
        max_length=20, choices=SII_AMBIENTE_CHOICES,
        default='certificacion', verbose_name='Ambiente SII'
    )
    sii_token = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name='Token API Facturación Electrónica'
    )

    # ── Pasarela de Pagos (MercadoPago / Webpay) ──────────────────────────────
    mp_public_key = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name='Public Key (MP / Webpay)'
    )
    mp_access_token = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name='Access Token (Secret Key)'
    )
    mp_modo = models.CharField(
        max_length=20, choices=MP_MODO_CHOICES,
        default='sandbox', verbose_name='Modo de Procesamiento'
    )

    # ── Auditoría ─────────────────────────────────────────────────────────────
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')

    class Meta:
        verbose_name = "Configuración Global"
        verbose_name_plural = "Configuración Global"

    def __str__(self):
        return f"Configuración Global (actualizada: {self.updated_at.strftime('%d/%m/%Y %H:%M')})"


# ══════════════════════════════════════════════════════════════════════════════
# SOLICITUD DE REGISTRO DE NUEVO COLEGIO (Cola de Onboarding SaaS)
# Usada por el Super Admin para aprobar/rechazar establecimientos nuevos.
# ══════════════════════════════════════════════════════════════════════════════

class SolicitudNuevoColegio(models.Model):
    """
    Solicitud de incorporación a la plataforma enviada por un sostenedor.
    Al ser aprobada, se crea automáticamente un registro en el modelo Colegio.
    """

    ESTADO_CHOICES = [
        ('pendiente',  'Pendiente'),
        ('aprobada',   'Aprobada'),
        ('rechazada',  'Rechazada'),
    ]

    # ── Datos de la institución solicitante ───────────────────────────────────
    nombre_colegio    = models.CharField(max_length=150, verbose_name='Nombre del Colegio')
    rut_sostenedor    = models.CharField(max_length=20,  verbose_name='RUT del Sostenedor')
    email_contacto    = models.EmailField(verbose_name='Email de Contacto')
    telefono          = models.CharField(max_length=30, blank=True, default='',
                                         verbose_name='Teléfono de Contacto')
    ciudad_comuna     = models.CharField(max_length=100, blank=True, default='',
                                         verbose_name='Ciudad / Comuna')
    nombre_administrador = models.CharField(max_length=150, blank=True, default='',
                                            verbose_name='Nombre del Director / Administrador')

    # ── Plan solicitado ───────────────────────────────────────────────────────
    plan_solicitado   = models.ForeignKey(
        'planes.Plan',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='solicitudes_colegio',
        verbose_name='Plan Solicitado'
    )

    # ── Estado del proceso ────────────────────────────────────────────────────
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='pendiente', verbose_name='Estado'
    )

    # ── Referencia al Colegio creado (se llena al aprobar) ───────────────────
    colegio_creado = models.OneToOneField(
        'colegios.Colegio',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='solicitud_origen',
        verbose_name='Colegio Generado'
    )

    # ── Auditoría ─────────────────────────────────────────────────────────────
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Solicitud')
    updated_at  = models.DateTimeField(auto_now=True,     verbose_name='Última Actualización')
    notas_admin = models.TextField(blank=True, default='', verbose_name='Notas del Revisor')

    class Meta:
        verbose_name = "Solicitud de Nuevo Colegio"
        verbose_name_plural = "Solicitudes de Nuevos Colegios"
        ordering = ['created_at']   # Los más antiguos primero (FIFO)

    def __str__(self):
        return f"{self.nombre_colegio} ({self.get_estado_display()})"

    def aprobar_y_crear_colegio(self):
        """
        Cambia el estado a 'aprobada' y crea el registro de Colegio
        con los datos de la solicitud. Devuelve el Colegio creado.
        """
        from colegios.models import Colegio

        colegio = Colegio.objects.create(
            nombre               = self.nombre_colegio,
            nombre_administrador = self.nombre_administrador or self.nombre_colegio,
            correo_institucional = self.email_contacto,
            telefono             = self.telefono or '—',
            ciudad_comuna        = self.ciudad_comuna or '—',
            tipo_institucion     = 'otro',        # Valor por defecto; el admin lo ajusta
            cantidad_alumnos     = 'menos_100',   # Valor por defecto
            estado               = 'pendiente_configuracion',
            configuracion_completa = False,
        )

        self.estado          = 'aprobada'
        self.colegio_creado  = colegio
        self.save()
        return colegio


class EstadoOnboarding(models.Model):
    colegio = models.ForeignKey('colegios.Colegio', on_delete=models.CASCADE, related_name='estado_onboarding')
    configuracion_inicial = models.BooleanField(default=False)
    carga_alumnos = models.BooleanField(default=False)
    capacitacion_docentes = models.BooleanField(default=False)
    lanzamiento_oficial = models.BooleanField(default=False)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def porcentaje_completado(self):
        total = 0
        if self.configuracion_inicial: total += 25
        if self.carga_alumnos: total += 25
        if self.capacitacion_docentes: total += 25
        if self.lanzamiento_oficial: total += 25
        return total

    def __str__(self):
        return f"Onboarding de {self.colegio.nombre} ({self.porcentaje_completado()}%)"

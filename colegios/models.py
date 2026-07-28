from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from planes.models import Plan, Modulo


class Colegio(models.Model):
    TIPO_INSTITUCION = [
        ('municipal', 'Municipal'),
        ('subvencionado', 'Subvencionado'),
        ('particular', 'Particular'),
        ('instituto', 'Instituto'),
        ('otro', 'Otro'),
    ]

    CANTIDAD_ALUMNOS = [
        ('menos_100', 'Menos de 100'),
        ('100_300', '100 a 300'),
        ('301_600', '301 a 600'),
        ('mas_600', 'Más de 600'),
    ]

    ESTADOS = [
        ('pendiente_configuracion', 'Pendiente de Configuración'),
        ('pendiente_pago', 'Pendiente de Pago'),
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]

    # Datos base (Paso 1 del Registro)
    nombre = models.CharField(max_length=150)
    nombre_administrador = models.CharField(max_length=150)
    correo_institucional = models.EmailField()
    telefono = models.CharField(max_length=30)
    ciudad_comuna = models.CharField(max_length=100)
    tipo_institucion = models.CharField(max_length=30, choices=TIPO_INSTITUCION)
    cantidad_alumnos = models.CharField(max_length=30, choices=CANTIDAD_ALUMNOS)

    # Identidad (Configuración Paso 1)
    nombre_corto = models.CharField(max_length=50, blank=True, null=True)
    eslogan = models.CharField(max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='colegios/logos/', blank=True, null=True)
    imagen_portada = models.ImageField(upload_to='colegios/portadas/', blank=True, null=True)
    
    # Colores institucional
    color_principal = models.CharField(max_length=20, default='#7b52d9')
    color_secundario = models.CharField(max_length=20, default='#6a44c2')
    color_acento = models.CharField(max_length=20, default='#ff6b6b')
    color_neutro = models.CharField(max_length=20, default='#f8fafc')

    # Información Institucional (Configuración Paso 2)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono_alternativo = models.CharField(max_length=30, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True)
    pais = models.CharField(max_length=100, default='Chile')
    referencia_direccion = models.CharField(max_length=255, blank=True, null=True)

    # Control de Estado
    administrador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='colegios_administrados',
        null=True,
        blank=True
    )
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente_configuracion')
    configuracion_completa = models.BooleanField(default=False)
    paso_configuracion_actual = models.IntegerField(default=1)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Colegio"
        verbose_name_plural = "Colegios"

    def __str__(self):
        return self.nombre


class Suscripcion(models.Model):
    FACTURACION_CHOICES = [
        ('mensual', 'Mensual'),
        ('anual', 'Anual'),
    ]
    ESTADOS = [
        ('pendiente_pago', 'Pendiente de pago'),
        ('activa', 'Activa'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]

    colegio = models.OneToOneField(Colegio, on_delete=models.CASCADE, related_name='suscripcion')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    tipo_facturacion = models.CharField(max_length=20, choices=FACTURACION_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente_pago')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"

    def __str__(self):
        return f"{self.colegio.nombre} - {self.plan.nombre}"


class ColegioModulo(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='modulos_activos')
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)
    fecha_activacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Módulo de Colegio"
        verbose_name_plural = "Módulos de Colegio"
        unique_together = ('colegio', 'modulo')

    def __str__(self):
        return f"{self.colegio.nombre} - {self.modulo.nombre}"


# --- CONFIGURACIÓN ACADÉMICA ---

class ConfiguracionAcademica(models.Model):
    PERIODOS = [
        ('semestres', 'Semestres'),
        ('trimestres', 'Trimestres'),
        ('anual', 'Anual'),
    ]

    colegio = models.OneToOneField(Colegio, on_delete=models.CASCADE, related_name='configuracion_academica')
    anio_academico = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    periodo_academico = models.CharField(max_length=20, choices=PERIODOS, default='semestres')
    horario_referencial = models.CharField(max_length=100, blank=True)

    # Niveles educativos activos
    nivel_parvularia = models.BooleanField(default=False)
    nivel_basica = models.BooleanField(default=False)
    nivel_media = models.BooleanField(default=False)
    nivel_tecnico_profesional = models.BooleanField(default=False)
    nivel_especial = models.BooleanField(default=False)
    nivel_otro = models.BooleanField(default=False)

    # Jornadas
    jornada_manana = models.BooleanField(default=False)
    jornada_tarde = models.BooleanField(default=False)
    jornada_completa = models.BooleanField(default=True)
    jornada_vespertina = models.BooleanField(default=False)
    jornada_flexible = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración Académica"
        verbose_name_plural = "Configuraciones Académicas"


class CursoColegio(models.Model):
    NIVELES = [
        ('parvularia', 'Educación Parvularia'),
        ('basica', 'Educación Básica'),
        ('media', 'Educación Media'),
        ('tecnico_profesional', 'Técnico Profesional'),
        ('especial', 'Educación Especial'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='cursos')
    nombre = models.CharField(max_length=100) # Ej: 1° Básico
    nivel = models.CharField(max_length=30, choices=NIVELES)
    jornada = models.CharField(max_length=50, default='Mañana')
    orden = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    desde_letra = models.CharField(max_length=1, default='A')
    hasta_letra = models.CharField(max_length=1, default='A')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Curso de Colegio"
        verbose_name_plural = "Cursos de Colegio"
        unique_together = ('colegio', 'nombre', 'jornada')

    def __str__(self):
        return f"{self.nombre} - {self.jornada} ({self.colegio.nombre})"


class SeccionCurso(models.Model):
    curso = models.ForeignKey(CursoColegio, on_delete=models.CASCADE, related_name='secciones')
    letra = models.CharField(max_length=1)
    nombre = models.CharField(max_length=20) # Ej: 1° Básico A
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sección de Curso"
        verbose_name_plural = "Secciones de Cursos"
        unique_together = ('curso', 'letra')

    def __str__(self):
        return self.nombre


# --- ROLES Y PERMISOS RELACIONALES ---

class Permiso(models.Model):
    codigo = models.CharField(max_length=50, unique=True) # Ej: ver, crear, editar, eliminar
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"

    def __str__(self):
        return self.nombre


class RolColegio(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='roles', null=True, blank=True)
    nombre = models.CharField(max_length=50) # Ej: Profesor, Director
    descripcion = models.TextField(blank=True)
    es_base = models.BooleanField(default=False) # Si es un rol predefinido por el sistema
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rol de Colegio"
        verbose_name_plural = "Roles de Colegio"
        unique_together = ('colegio', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.colegio.nombre})"


class RolPermiso(models.Model):
    rol = models.ForeignKey(RolColegio, on_delete=models.CASCADE, related_name='permisos')
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    
    # Flags de permisos explícitos como solicitó el usuario para facilidad de consulta
    puede_ver = models.BooleanField(default=False)
    puede_crear = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)
    puede_exportar = models.BooleanField(default=False)
    puede_aprobar = models.BooleanField(default=False)
    puede_enviar_mensajes = models.BooleanField(default=False)
    puede_administrar = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Permiso de Rol"
        verbose_name_plural = "Permisos de Roles"
        unique_together = ('rol', 'modulo')

    def __str__(self):
        return f"{self.rol.nombre} - {self.modulo.nombre}"

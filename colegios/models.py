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


class ConfiguracionModulos(models.Model):
    colegio = models.OneToOneField(Colegio, on_delete=models.CASCADE, related_name='configuracion_modulos')
    libro_clases = models.BooleanField(default=False)
    contabilidad = models.BooleanField(default=False)
    proveedores = models.BooleanField(default=False)
    simce = models.BooleanField(default=False)
    mercado_publico = models.BooleanField(default=False)
    comunidad = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuración de Módulos"
        verbose_name_plural = "Configuraciones de Módulos"

    def __str__(self):
        return f"Módulos de {self.colegio.nombre}"



# --- CONFIGURACIÓN ACADÉMICA ---

class ConfiguracionAcademica(models.Model):
    PERIODOS = [
        ('semestres', 'Semestres'),
        ('trimestres', 'Trimestres'),
        ('anual', 'Anual'),
    ]

    MODALIDADES_ASISTENCIA = [
        ('diaria', 'Asistencia Diaria General'),
        ('asignatura', 'Asistencia por Asignatura / Bloque'),
    ]

    TIPO_CALIFICACION_CHOICES = [
        ('numerica', 'Notas Numéricas (1.0 a 7.0)'),
        ('conceptual', 'Evaluación Conceptual (L, PL, NL)'),
    ]

    REGLA_REDONDEO_CHOICES = [
        ('un_decimal', 'Redondear a 1 decimal (ej: 5.65 -> 5.7)'),
        ('dos_decimales', 'Redondear a 2 decimales (ej: 5.65)'),
        ('truncado', 'Truncar sin redondear (ej: 5.69 -> 5.6)'),
    ]

    TIPO_CALCULO_PROMEDIO_CHOICES = [
        ('ponderado', 'Promedio Ponderado por Coeficientes'),
        ('simple', 'Promedio Aritmético Simple'),
    ]

    VISIBILIDAD_NOTAS_CHOICES = [
        ('inmediata', 'Publicación Inmediata al Guardar Nota'),
        ('cierre_periodo', 'Solo al Cierre del Período Académico'),
    ]

    colegio = models.OneToOneField(Colegio, on_delete=models.CASCADE, related_name='configuracion_academica')
    anio_academico = models.IntegerField()
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    periodo_academico = models.CharField(max_length=20, choices=PERIODOS, default='semestres')
    modalidad_asistencia = models.CharField(max_length=20, choices=MODALIDADES_ASISTENCIA, default='asignatura')
    horario_referencial = models.CharField(max_length=100, blank=True)

    # Políticas Académicas y de Evaluación
    tipo_calificacion = models.CharField(max_length=20, choices=TIPO_CALIFICACION_CHOICES, default='numerica')
    nota_minima_aprobacion = models.DecimalField(max_digits=3, decimal_places=1, default=4.0)
    porcentaje_exigencia = models.IntegerField(default=60)
    regla_redondeo = models.CharField(max_length=20, choices=REGLA_REDONDEO_CHOICES, default='un_decimal')
    tipo_calculo_promedio = models.CharField(max_length=20, choices=TIPO_CALCULO_PROMEDIO_CHOICES, default='ponderado')
    porcentaje_asistencia_minima = models.IntegerField(default=85)
    visibilidad_notas_apoderados = models.CharField(max_length=20, choices=VISIBILIDAD_NOTAS_CHOICES, default='inmediata')
    notificar_ausencias = models.BooleanField(default=True)
    notificar_notas_rojas = models.BooleanField(default=True)



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
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sección de Curso"
        verbose_name_plural = "Secciones de Cursos"
        unique_together = ('curso', 'letra')

    def __str__(self):
        return self.nombre


class Estudiante(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='estudiantes')
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.SET_NULL, null=True, blank=True, related_name='estudiantes')
    nombre_completo = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"

    def __str__(self):
        return f"{self.nombre_completo} - {self.seccion.nombre if self.seccion else 'Sin Sección'}"


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


class Asignatura(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='asignaturas')
    curso = models.ForeignKey(CursoColegio, on_delete=models.CASCADE, related_name='asignaturas')
    nombre = models.CharField(max_length=100)
    docente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='asignaturas_dictadas')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        unique_together = ('curso', 'nombre')

    def __str__(self):
        return f"{self.nombre} - {self.curso.nombre}"


class AnotacionEstudiante(models.Model):
    TIPO_CHOICES = [
        ('positiva', 'Anotación Positiva / Mérito'),
        ('negativa', 'Anotación Negativa / Falta'),
        ('neutra', 'Observación Neutra'),
        ('citacion', 'Citación a Apoderado'),
    ]

    GRAVEDAD_CHOICES = [
        ('leve', 'Leve'),
        ('grave', 'Grave'),
        ('gravisima', 'Gravísima'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='anotaciones')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='anotaciones')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.SET_NULL, null=True, blank=True, related_name='anotaciones')
    docente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='neutra')
    gravedad = models.CharField(max_length=20, choices=GRAVEDAD_CHOICES, default='leve')
    fecha = models.DateField(default=timezone.now)
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anotación de Estudiante"
        verbose_name_plural = "Anotaciones de Estudiantes"
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estudiante.nombre_completo} ({self.fecha})"


class EventoAgenda(models.Model):
    TIPO_CHOICES = [
        ('clase', 'Clase / Cátedra'),
        ('evaluacion', 'Prueba / Evaluación'),
        ('reunion', 'Reunión Directiva / Apoderados'),
        ('actividad', 'Actividad Institucional'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='eventos_agenda')
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='eventos_asignados')
    es_para_todos = models.BooleanField(default=False)
    es_recurrente = models.BooleanField(default=False)
    dia_semana = models.IntegerField(blank=True, null=True)
    titulo = models.CharField(max_length=200)


    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='actividad')
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    lugar = models.CharField(max_length=150, blank=True, null=True)
    curso = models.ForeignKey(CursoColegio, on_delete=models.SET_NULL, null=True, blank=True)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = "Evento de Agenda"
        verbose_name_plural = "Eventos de Agenda"
        ordering = ['fecha_inicio', 'id']

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio.strftime('%d/%m/%Y %H:%M')})"



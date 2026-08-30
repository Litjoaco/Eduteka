from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from planes.models import Plan, Modulo
from decimal import Decimal


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
    profesor_jefe = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='secciones_jefatura')
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sección de Curso"
        verbose_name_plural = "Secciones de Cursos"
        unique_together = ('curso', 'letra')

    def __str__(self):
        return self.nombre



class Estudiante(models.Model):
    GENEROS = [
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('otro', 'Otro / No Binarie'),
        ('no_informa', 'Prefiero no decir'),
    ]

    PREVISIONES = [
        ('fonasa', 'Fonasa'),
        ('isapre', 'Isapre'),
        ('particular', 'Particular / Seguro'),
        ('ninguna', 'Sin Previsión'),
    ]

    TIPOS_PIE = [
        ('neep', 'NEEP (Permanente)'),
        ('neet', 'NEET (Transitorio)'),
        ('sin_clasificar', 'En Proceso / Sin Clasificar'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='estudiantes')
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.SET_NULL, null=True, blank=True, related_name='estudiantes')
    nombre_completo = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, blank=True, null=True)

    # Datos Personales Extendidos
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=20, choices=GENEROS, default='no_informa')
    nacionalidad = models.CharField(max_length=50, default='Chilena')
    direccion = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.CharField(max_length=100, blank=True, null=True)

    # Salud y Emergencia
    prevision_salud = models.CharField(max_length=50, choices=PREVISIONES, default='fonasa')
    grupo_sanguineo = models.CharField(max_length=10, blank=True, null=True)
    alergias_enfermedades = models.TextField(blank=True, null=True, help_text="Alergias, condiciones médicas o medicamentos")
    contacto_emergencia_nombre = models.CharField(max_length=150, blank=True, null=True)
    contacto_emergencia_parentesco = models.CharField(max_length=50, blank=True, null=True)
    contacto_emergencia_telefono = models.CharField(max_length=30, blank=True, null=True)

    # Apoderado Titular
    nombre_apoderado = models.CharField(max_length=150, blank=True, null=True)
    rut_apoderado = models.CharField(max_length=12, blank=True, null=True)
    telefono_apoderado = models.CharField(max_length=30, blank=True, null=True)
    email_apoderado = models.EmailField(blank=True, null=True)
    parentesco_apoderado = models.CharField(max_length=50, blank=True, null=True)

    # Programa de Integración Escolar (PIE) y Necesidades Especiales
    es_pie = models.BooleanField(default=False)
    tipo_pie = models.CharField(max_length=50, choices=TIPOS_PIE, blank=True, null=True)
    diagnostico_pie = models.CharField(max_length=255, blank=True, null=True, help_text="Ej: TEA, TDAH, TEL, etc.")
    observaciones_pie = models.TextField(blank=True, null=True, help_text="Adecuaciones pedagógicas y recomendaciones para docentes")

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
    
    # Flags de permisos por módulo
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
    horas_semanales = models.PositiveIntegerField(default=4, help_text="Horas pedagógicas semanales")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        unique_together = ('curso', 'nombre')

    def __str__(self):
        return f"{self.nombre} - {self.curso.nombre}"


class BloqueHorario(models.Model):
    TIPO_CHOICES = [
        ('clase', 'Clase Pedagógica'),
        ('recreo', 'Recreo / Pausa'),
        ('almuerzo', 'Almuerzo'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='bloques_horario')
    numero_bloque = models.PositiveIntegerField(default=1)
    nombre = models.CharField(max_length=50, help_text="Ej: 1° Bloque, Recreo Mañana")
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='clase')
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Bloque Horario"
        verbose_name_plural = "Bloques Horarios"
        ordering = ['orden', 'hora_inicio']

    def __str__(self):
        return f"{self.nombre} ({self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')})"


class HorarioClase(models.Model):
    DIAS_SEMANA = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
        (6, 'Sábado'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='horarios_clases')
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.CASCADE, related_name='horarios_seccion')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='horarios_asignatura')
    docente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clases_horario')
    bloque = models.ForeignKey(BloqueHorario, on_delete=models.CASCADE, related_name='clases_bloque')
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS_SEMANA, default=1)
    sala = models.CharField(max_length=50, blank=True, null=True, help_text="Ej: Sala 102, Lab Ciencias, Cancha")
    color = models.CharField(max_length=20, default='#7C5CFC', help_text="Color hexadecimal para grilla")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Horario de Clase"
        verbose_name_plural = "Horarios de Clases"
        unique_together = ('colegio', 'seccion', 'bloque', 'dia_semana')
        ordering = ['dia_semana', 'bloque__orden', 'bloque__hora_inicio']

    def __str__(self):
        docente_str = self.docente.get_full_name() or self.docente.username if self.docente else "Sin Docente"
        return f"{self.get_dia_semana_display()} {self.bloque.nombre}: {self.asignatura.nombre} - {self.seccion.nombre} ({docente_str})"



class MiembroPermiso(models.Model):
    """
    Permisos individuales específicos concedidos por el Director a un miembro particular,
    permitiendo sobreescribir o extender los permisos base de su rol.
    """
    miembro = models.ForeignKey('solicitudes.MiembroColegio', on_delete=models.CASCADE, related_name='permisos_individuales')
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    
    puede_ver = models.BooleanField(default=False)
    puede_crear = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)
    puede_exportar = models.BooleanField(default=False)
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = "Permiso Individual de Funcionario"
        verbose_name_plural = "Permisos Individuales de Funcionarios"
        unique_together = ('miembro', 'modulo')

    def __str__(self):
        return f"{self.miembro.usuario.username} - {self.modulo.nombre}"



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
        ('clase', 'Clase / Horario Semanal'),
        ('reunion_apoderados', 'Reunión de Apoderados'),
        ('consejo_profesores', 'Consejo de Profesores / UTP'),
        ('entrevista', 'Entrevista Individual (Apoderado / PIE)'),
        ('evaluacion', 'Prueba / Evaluación'),
        ('actividad', 'Actividad Institucional / Acto'),
        ('feriado', 'Feriado Escolar / Suspensión'),
        ('reunion', 'Reunión General'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='eventos_agenda')
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='eventos_asignados')
    es_para_todos = models.BooleanField(default=False)
    es_recurrente = models.BooleanField(default=False)
    dia_semana = models.IntegerField(blank=True, null=True, help_text="0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes")
    titulo = models.CharField(max_length=200)

    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, default='actividad')
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(blank=True, null=True)
    lugar = models.CharField(max_length=150, blank=True, null=True)
    curso = models.ForeignKey(CursoColegio, on_delete=models.SET_NULL, null=True, blank=True)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def es_clase(self):
        return self.tipo == 'clase'

    @property
    def nombre_dia_semana(self):
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        if self.dia_semana is not None and 0 <= self.dia_semana < len(dias):
            return dias[self.dia_semana]
        return ''

    @property
    def rango_horario_str(self):
        h_ini = self.fecha_inicio.strftime('%H:%M') if self.fecha_inicio else ''
        h_fin = self.fecha_fin.strftime('%H:%M') if self.fecha_fin else ''
        if h_ini and h_fin:
            return f"{h_ini} - {h_fin}"
        return h_ini


    class Meta:
        verbose_name = "Evento de Agenda"
        verbose_name_plural = "Eventos de Agenda"
        ordering = ['fecha_inicio', 'id']

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio.strftime('%d/%m/%Y %H:%M')})"


# ==============================================================================
# MÓDULO DE FINANZAS, TESORERÍA, PROYECTOS, SUBVENCIONES Y CAJA CHICA
# ==============================================================================

class ProyectoEscolar(models.Model):
    TIPO_FONDO = [
        ('sep', 'Subvención Escolar Preferencial (SEP)'),
        ('pie', 'Programa de Integración Escolar (PIE)'),
        ('subvencion_general', 'Subvención General / Regular'),
        ('mantenimiento', 'Fondo de Mantenimiento e Infraestructura'),
        ('fondos_propios', 'Fondos Propios / Centro de Padres / Donaciones'),
        ('otro', 'Otro Fondo / Convenio'),
    ]

    CATEGORIA_SUPEREDUC = [
        ('pedagogico', 'Insumos & Recursos Pedagógicos / Aula'),
        ('utiles_escolares', 'Útiles Escolares & Materiales para Estudiantes'),
        ('equipamiento', 'Equipamiento Tecnológico y Mobiliario'),
        ('infraestructura', 'Mantenimiento, Obras Menores y Reparaciones'),
        ('psicosocial', 'Acompañamiento Psicosocial & Convivencia'),
        ('remuneraciones', 'Honorarios & Talleres Especializados'),
        ('operacional', 'Gastos Operacionales & Servicios'),
        ('otro', 'Otro Gasto Educativo Autorizado'),
    ]

    ESTADOS = [
        ('planificacion', 'En Planificación'),
        ('en_ejecucion', 'En Ejecución'),
        ('rendido', 'Rendido / En Verificación'),
        ('cerrado', 'Cerrado / Completado'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='proyectos_escolares')
    codigo = models.CharField(max_length=50) # Ej: PRY-SEP-01, UTILES-2026, PME-2.1
    nombre = models.CharField(max_length=200) # Ej: Campaña Útiles Escolares Prioritarios 2026
    descripcion = models.TextField(blank=True, null=True)
    tipo_fondo = models.CharField(max_length=30, choices=TIPO_FONDO, default='sep')
    categoria_supereduc = models.CharField(max_length=30, choices=CATEGORIA_SUPEREDUC, default='pedagogico')
    presupuesto_asignado = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_termino = models.DateField(blank=True, null=True)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='proyectos_a_cargo')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='en_ejecucion')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proyecto Escolar / Centro de Costo"
        verbose_name_plural = "Proyectos Escolares y Centros de Costo"
        ordering = ['-fecha_inicio', '-id']

    def __str__(self):
        return f"[{self.codigo}] {self.nombre} ({self.get_tipo_fondo_display()})"

    @property
    def total_gastado(self):
        from django.db.models import Sum
        egresos = self.movimientos.filter(tipo='egreso').aggregate(t=Sum('monto'))['t'] or Decimal('0.0')
        return egresos

    @property
    def total_ingresos_extra(self):
        from django.db.models import Sum
        ingresos = self.movimientos.filter(tipo='ingreso').aggregate(t=Sum('monto'))['t'] or Decimal('0.0')
        return ingresos

    @property
    def saldo_disponible(self):
        return (self.presupuesto_asignado + self.total_ingresos_extra) - self.total_gastado

    @property
    def porcentaje_ejecucion(self):
        if self.presupuesto_asignado > 0:
            pct = (float(self.total_gastado) / float(self.presupuesto_asignado)) * 100
            return min(round(pct, 1), 100.0)
        return 0.0


class CuentaFinanciera(models.Model):
    TIPO_CUENTA = [
        ('caja_chica_utiles', 'Caja Chica Útiles Escolares & Fungibles'),
        ('caja_chica_convivencia', 'Caja Chica Convivencia & Inspectoría'),
        ('caja_chica_ciencias', 'Caja Chica Ciencias / Laboratorios'),
        ('caja_chica_rectoria', 'Caja Chica Dirección / Rectoría'),
        ('caja_chica', 'Caja Chica General / Departamentos'),
        ('subvencion_sep', 'Bolsa Subvención Escolar Preferencial (SEP)'),
        ('subvencion_pie', 'Bolsa Programa de Integración Escolar (PIE)'),
        ('subvencion_general', 'Bolsa Subvención General / Regular'),
        ('fondo_mantenimiento', 'Fondo Mantenimiento e Infraestructura'),
        ('cuenta_bancaria', 'Cuenta Bancaria / Corriente'),
        ('caja_general', 'Caja General'),
        ('otro', 'Otro'),
    ]

    TIPO_FONDO = [
        ('sep', 'Fondos SEP'),
        ('pie', 'Fondos PIE'),
        ('subvencion_general', 'Subvención General'),
        ('mantenimiento', 'Fondo Mantenimiento'),
        ('fondos_propios', 'Fondos Propios / Centro de Padres'),
        ('otro', 'Otro'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='cuentas_financieras')
    nombre = models.CharField(max_length=150) # Ej: Caja Chica Útiles Alumnos, Cuenta Corriente Banco Estado
    tipo = models.CharField(max_length=35, choices=TIPO_CUENTA, default='caja_chica')
    fondo_asociado = models.CharField(max_length=30, choices=TIPO_FONDO, default='fondos_propios')
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    banco = models.CharField(max_length=100, blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    saldo_actual = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cuentas_a_cargo')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cuenta Financiera / Caja"
        verbose_name_plural = "Cuentas Financieras y Cajas"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()}) - ${self.saldo_actual:,.0f}"


class CategoriaFinanciera(models.Model):
    TIPO_MOVIMIENTO = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso / Gasto'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='categorias_financieras')
    nombre = models.CharField(max_length=100) # Ej: Subvención Mineduc, Material Didáctico, Luz y Agua
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO, default='egreso')
    icono = models.CharField(max_length=50, default='bi-tag')
    color = models.CharField(max_length=20, default='#7C5CFC')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría Financiera"
        verbose_name_plural = "Categorías Financieras"
        unique_together = ('colegio', 'nombre', 'tipo')

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class MovimientoFinanciero(models.Model):
    TIPO_MOVIMIENTO = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso / Gasto'),
    ]

    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('cheque', 'Cheque'),
        ('otro', 'Otro'),
    ]

    ESTADOS = [
        ('completado', 'Completado'),
        ('pendiente', 'Pendiente'),
        ('anulado', 'Anulado'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='movimientos_financieros')
    cuenta = models.ForeignKey(CuentaFinanciera, on_delete=models.CASCADE, related_name='movimientos')
    proyecto = models.ForeignKey(ProyectoEscolar, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    categoria = models.ForeignKey(CategoriaFinanciera, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    tipo_fondo = models.CharField(max_length=30, choices=ProyectoEscolar.TIPO_FONDO, default='subvencion_general')
    clasificacion_supereduc = models.CharField(max_length=30, choices=ProyectoEscolar.CATEGORIA_SUPEREDUC, default='pedagogico')
    
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    concepto = models.CharField(max_length=200) # Ej: Compra de plumones y resmas de papel
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField(default=timezone.now)
    metodo_pago = models.CharField(max_length=30, choices=METODOS_PAGO, default='efectivo')
    numero_comprobante = models.CharField(max_length=100, blank=True, null=True) # Boleta / Voucher
    comprobante_adjunto = models.FileField(upload_to='finanzas/comprobantes/', blank=True, null=True)
    
    rendido_supereduc = models.BooleanField(default=False)
    numero_rendicion_folio = models.CharField(max_length=50, blank=True, null=True)
    
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='completado')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento Financiero"
        verbose_name_plural = "Movimientos Financieros"
        ordering = ['-fecha', '-id']

    def __str__(self):
        signo = '+' if self.tipo == 'ingreso' else '-'
        return f"{signo}${self.monto:,.0f} - {self.concepto} ({self.fecha})"


class FacturaGasto(models.Model):
    TIPO_DOC = [
        ('factura_afecta', 'Factura Electrónica (Afecta)'),
        ('factura_exenta', 'Factura Exenta de IVA'),
        ('boleta_honorarios', 'Boleta de Honorarios'),
        ('boleta_compra', 'Boleta de Compra / Insumos'),
        ('nota_credito', 'Nota de Crédito'),
    ]

    ESTADO_PAGO = [
        ('pendiente', 'Pendiente de Pago'),
        ('pagado', 'Pagado'),
        ('vencido', 'Vencido'),
        ('anulado', 'Anulado'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='facturas_gastos')
    proyecto = models.ForeignKey(ProyectoEscolar, on_delete=models.SET_NULL, null=True, blank=True, related_name='facturas')
    tipo_documento = models.CharField(max_length=30, choices=TIPO_DOC, default='factura_afecta')
    tipo_fondo = models.CharField(max_length=30, choices=ProyectoEscolar.TIPO_FONDO, default='subvencion_general')
    clasificacion_supereduc = models.CharField(max_length=30, choices=ProyectoEscolar.CATEGORIA_SUPEREDUC, default='pedagogico')
    folio = models.CharField(max_length=50) # Número de Factura
    proveedor_nombre = models.CharField(max_length=150) # Ej: Librería y Papelería Central SpA
    proveedor_rut = models.CharField(max_length=20, blank=True, null=True)
    fecha_emision = models.DateField(default=timezone.now)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    
    monto_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    monto_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    monto_total = models.DecimalField(max_digits=14, decimal_places=2)
    
    estado_pago = models.CharField(max_length=20, choices=ESTADO_PAGO, default='pendiente')
    rendido_supereduc = models.BooleanField(default=False)
    movimiento_asociado = models.ForeignKey(MovimientoFinanciero, on_delete=models.SET_NULL, null=True, blank=True, related_name='factura_vinculada')
    archivo_factura = models.FileField(upload_to='finanzas/facturas/', blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Factura / Documento Tributario"
        verbose_name_plural = "Facturas y Documentos Tributarios"
        ordering = ['-fecha_emision', '-id']

    def __str__(self):
        return f"{self.get_tipo_documento_display()} #{self.folio} - {self.proveedor_nombre} (${self.monto_total:,.0f})"


# ==============================================================================
# MÓDULO DE PROVEEDORES & INVENTARIO GENERAL DEL COLEGIO
# ==============================================================================

class ProveedorColegio(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='proveedores')
    nombre = models.CharField(max_length=150) # Ej: Librería & Papelería Central
    rut = models.CharField(max_length=20, blank=True, null=True)
    categoria_insumos = models.CharField(max_length=120, default='Papelería y Útiles') # Ej: Tecnología, Aseo, Insumos de Oficina
    contacto_nombre = models.CharField(max_length=100, blank=True, null=True) # Ejecutivo / Contacto comercial
    telefono = models.CharField(max_length=30, blank=True, null=True) # WhatsApp / Teléfono
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.categoria_insumos})"


class CategoriaInventario(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='categorias_inventario')
    nombre = models.CharField(max_length=100) # Ej: Útiles & Papelería, Equipos Tecnológicos, Aseo y Limpieza
    icono = models.CharField(max_length=50, default='bi-box-seam')
    color = models.CharField(max_length=20, default='#7C5CFC')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de Inventario"
        verbose_name_plural = "Categorías de Inventario"
        unique_together = ('colegio', 'nombre')

    def __str__(self):
        return self.nombre


class ItemInventario(models.Model):
    TIPO_ITEM = [
        ('consumible', 'Insumo Consumible / Fungible'),
        ('activo', 'Activo Fijo / Equipamiento / Mobiliario'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='items_inventario')
    nombre = models.CharField(max_length=150) # Ej: Resmas de Papel Carta 75g, Plumones de Pizarra Recargables
    sku = models.CharField(max_length=50, blank=True, null=True)
    categoria = models.ForeignKey(CategoriaInventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    proveedor_principal = models.ForeignKey(ProveedorColegio, on_delete=models.SET_NULL, null=True, blank=True, related_name='articulos_suministrados')
    tipo = models.CharField(max_length=30, choices=TIPO_ITEM, default='consumible')
    
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5) # Umbral de alerta
    unidad_medida = models.CharField(max_length=30, default='unidades') # resmas, cajas, unidades, litros, paquetes
    ubicacion = models.CharField(max_length=100, default='Bodega Principal') # Sala Profesores, Bodega Central, Laboratorio
    
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Artículo de Inventario"
        verbose_name_plural = "Artículos de Inventario"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_actual} {self.unidad_medida})"

    @property
    def en_alerta(self):
        return self.stock_actual <= self.stock_minimo

    @property
    def estado_stock(self):
        if self.stock_actual <= 0:
            return 'agotado'
        elif self.stock_actual <= self.stock_minimo:
            return 'critico'
        return 'optimo'


class MovimientoStock(models.Model):
    TIPO_MOVIMIENTO = [
        ('entrada', 'Entrada / Compra (+)'),
        ('salida', 'Salida / Consumo / Entrega (-)'),
        ('ajuste', 'Ajuste de Inventario'),
    ]

    item = models.ForeignKey(ItemInventario, on_delete=models.CASCADE, related_name='movimientos_stock')
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    cantidad = models.IntegerField()
    stock_resultante = models.IntegerField()
    motivo = models.CharField(max_length=200) # Ej: Entrega para 1° Básico A, Reposición de compra mensual
    entregado_a = models.CharField(max_length=150, blank=True, null=True) # Docente / Funcionario
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad} {self.item.unidad_medida} - {self.item.nombre}"


# ==============================================================================
# TALLERES EXTRACURRICULARES (ACLES) & ASISTENCIA MULTICURSO
# ==============================================================================

class TallerExtracurricular(models.Model):
    CATEGORIA_CHOICES = [
        ('deportivo', 'Deportivo & Recreativo'),
        ('artistico', 'Artístico & Expresión'),
        ('cientifico', 'Científico & Tecnológico'),
        ('academico', 'Refuerzo Académico & Idiomas'),
        ('musica', 'Música & Danza'),
        ('social', 'Liderazgo & Medioambiente'),
        ('otro', 'Otro'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='talleres_extracurriculares')
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, default='deportivo')
    docente_encargado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='talleres_a_cargo')
    monitor_externo = models.CharField(max_length=150, blank=True, null=True)
    dias_horario = models.CharField(max_length=150, help_text="Ej: Martes y Jueves 16:00 - 17:30")
    lugar = models.CharField(max_length=150, default="Gimnasio Principal / Sala Multiuso")
    cupo_maximo = models.IntegerField(default=30, null=True, blank=True)
    descripcion = models.TextField(blank=True, null=True)
    icono = models.CharField(max_length=50, default="bi-star-fill")
    color = models.CharField(max_length=20, default="#7C5CFC")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Taller Extracurricular"
        verbose_name_plural = "Talleres Extracurriculares"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_categoria_display()})"

    @property
    def total_inscritos(self):
        return self.inscripciones.filter(activo=True).count()

    @property
    def monitor_nombre(self):
        if self.docente_encargado:
            nombre = f"{self.docente_encargado.first_name} {self.docente_encargado.last_name}".strip()
            return nombre if nombre else self.docente_encargado.username
        elif self.monitor_externo:
            return self.monitor_externo
        return "Sin monitor asignado"


class InscripcionTaller(models.Model):
    taller = models.ForeignKey(TallerExtracurricular, on_delete=models.CASCADE, related_name='inscripciones')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='talleres_inscritos')
    fecha_inscripcion = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    observaciones = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Inscripción a Taller"
        verbose_name_plural = "Inscripciones a Talleres"
        unique_together = ('taller', 'estudiante')
        ordering = ['estudiante__nombre_completo']

    def __str__(self):
        return f"{self.estudiante.nombre_completo} en {self.taller.nombre}"


class SesionAsistenciaTaller(models.Model):
    taller = models.ForeignKey(TallerExtracurricular, on_delete=models.CASCADE, related_name='sesiones_asistencia')
    fecha = models.DateField()
    contenido_actividad = models.CharField(max_length=255, blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sesión de Asistencia de Taller"
        verbose_name_plural = "Sesiones de Asistencia de Talleres"
        unique_together = ('taller', 'fecha')
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"Sesión {self.taller.nombre} - {self.fecha.strftime('%d/%m/%Y')}"

    @property
    def porcentaje_asistencia(self):
        total = self.detalles.count()
        if total == 0:
            return 0
        presentes = self.detalles.filter(estado__in=['presente', 'tarde', 'justificado']).count()
        return round((presentes / total) * 100, 1)


class DetalleAsistenciaTaller(models.Model):
    ESTADO_ASISTENCIA = [
        ('presente', 'Presente'),
        ('ausente', 'Ausente'),
        ('tarde', 'Atrasado'),
        ('justificado', 'Justificado'),
    ]

    sesion = models.ForeignKey(SesionAsistenciaTaller, on_delete=models.CASCADE, related_name='detalles')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='asistencias_taller')
    estado = models.CharField(max_length=20, choices=ESTADO_ASISTENCIA, default='presente')
    observacion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Detalle de Asistencia de Taller"
        verbose_name_plural = "Detalles de Asistencia de Talleres"
        unique_together = ('sesion', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.nombre_completo} - {self.get_estado_display()} ({self.sesion.fecha})"


# ==============================================================================
# MODELOS DE GESTIÓN Y EVALUACIÓN SIMCE / DIA
# ==============================================================================

class EnsayoSIMCE(models.Model):
    ASIGNATURAS_SIMCE = [
        ('lectura', 'Lectura / Lenguaje'),
        ('matematica', 'Matemática'),
        ('ciencias', 'Ciencias Naturales'),
        ('historia', 'Historia, Geografía y Cs. Sociales'),
        ('otro', 'Otro Instrumento / DIA'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='ensayos_simce')
    titulo = models.CharField(max_length=150)
    asignatura = models.CharField(max_length=30, choices=ASIGNATURAS_SIMCE, default='matematica')
    curso = models.ForeignKey(CursoColegio, on_delete=models.CASCADE, related_name='ensayos_simce')
    fecha = models.DateField(default=timezone.now)
    total_preguntas = models.PositiveIntegerField(default=35)
    puntaje_base = models.PositiveIntegerField(default=150)
    puntaje_max = models.PositiveIntegerField(default=350)
    descripcion = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ensayo SIMCE"
        verbose_name_plural = "Ensayos SIMCE"
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"{self.titulo} - {self.curso.nombre} ({self.fecha})"

    @property
    def total_rendidos(self):
        return self.resultados.count()

    @property
    def promedio_puntaje(self):
        res = self.resultados.all()
        if not res.exists():
            return 0
        total = sum(r.puntaje_simce for r in res)
        return round(total / res.count())

    @property
    def promedio_logro(self):
        res = self.resultados.all()
        if not res.exists():
            return 0.0
        total = sum(r.porcentaje_logro for r in res)
        return round(total / res.count(), 1)

    @property
    def desglose_niveles(self):
        res = self.resultados.all()
        total = res.count()
        if total == 0:
            return {'insuficiente': 0, 'elemental': 0, 'adecuado': 0, 'pct_insuficiente': 0, 'pct_elemental': 0, 'pct_adecuado': 0}
        
        insuf = res.filter(nivel_aprendizaje='insuficiente').count()
        elem = res.filter(nivel_aprendizaje='elemental').count()
        adec = res.filter(nivel_aprendizaje='adecuado').count()
        
        return {
            'insuficiente': insuf,
            'elemental': elem,
            'adecuado': adec,
            'pct_insuficiente': round((insuf / total) * 100, 1),
            'pct_elemental': round((elem / total) * 100, 1),
            'pct_adecuado': round((adec / total) * 100, 1),
        }


class ResultadoEnsayoSIMCE(models.Model):
    NIVELES_APRENDIZAJE = [
        ('insuficiente', 'Insuficiente'),
        ('elemental', 'Elemental'),
        ('adecuado', 'Adecuado'),
    ]

    ensayo = models.ForeignKey(EnsayoSIMCE, on_delete=models.CASCADE, related_name='resultados')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='resultados_simce')
    respuestas_correctas = models.PositiveIntegerField(default=0)
    porcentaje_logro = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    puntaje_simce = models.PositiveIntegerField(default=200)
    nivel_aprendizaje = models.CharField(max_length=20, choices=NIVELES_APRENDIZAJE, default='elemental')
    observaciones = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        verbose_name = "Resultado Ensayo SIMCE"
        verbose_name_plural = "Resultados Ensayos SIMCE"
        unique_together = ('ensayo', 'estudiante')
        ordering = ['estudiante__nombre_completo']

    def __str__(self):
        return f"{self.estudiante.nombre_completo} - {self.ensayo.titulo}: {self.puntaje_simce} pts"

    def calcular_puntaje_y_nivel(self):
        """Calcula el puntaje SIMCE escala 150-350 y asigna el nivel oficial de la Agencia de Calidad."""
        tot = self.ensayo.total_preguntas
        if tot > 0:
            logro = (self.respuestas_correctas / tot) * 100.0
            self.porcentaje_logro = round(logro, 1)
            # Escala lineal 150 a 350
            rango = self.ensayo.puntaje_max - self.ensayo.puntaje_base
            self.puntaje_simce = round(self.ensayo.puntaje_base + (logro / 100.0) * rango)
        else:
            self.porcentaje_logro = 0.0
            self.puntaje_simce = self.ensayo.puntaje_base

        # Criterio estándar MINEDUC/Agencia
        if self.puntaje_simce < 235:
            self.nivel_aprendizaje = 'insuficiente'
        elif self.puntaje_simce < 285:
            self.nivel_aprendizaje = 'elemental'
        else:
            self.nivel_aprendizaje = 'adecuado'


class PuntajeHistoricoSIMCE(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='historicos_simce')
    anio = models.PositiveIntegerField()
    nivel_escolar = models.CharField(max_length=60)  # ej: 4° Básico, 8° Básico, II° Medio
    asignatura = models.CharField(max_length=60)     # ej: Lectura, Matemática, Ciencias Naturales
    puntaje_colegio = models.PositiveIntegerField()
    puntaje_gse = models.PositiveIntegerField(default=255)       # Promedio Grupo Socioeconómico
    puntaje_nacional = models.PositiveIntegerField(default=250)  # Promedio Nacional
    nivel_insuficiente_pct = models.DecimalField(max_digits=5, decimal_places=1, default=20.0)
    nivel_elemental_pct = models.DecimalField(max_digits=5, decimal_places=1, default=45.0)
    nivel_adecuado_pct = models.DecimalField(max_digits=5, decimal_places=1, default=35.0)

    class Meta:
        verbose_name = "Puntaje Histórico SIMCE"
        verbose_name_plural = "Puntajes Históricos SIMCE"
        ordering = ['-anio', 'nivel_escolar', 'asignatura']

    def __str__(self):
        return f"{self.anio} - {self.nivel_escolar} ({self.asignatura}): {self.puntaje_colegio} pts"


# ════════════════════════════════════════════════════════════════════════════════
# 📦 MÓDULO DE ADQUISICIONES & CUMPLIMIENTO DE 3 COTIZACIONES (SUPEREDUC)
# ════════════════════════════════════════════════════════════════════════════════

class ProcesoCompra(models.Model):
    TIPO_FONDO = [
        ('subvencion_general', 'Subvención General MINEDUC'),
        ('sep', 'Subvención Escolar Preferencial (SEP)'),
        ('pie', 'Programa de Integración Escolar (PIE)'),
        ('mantenimiento', 'Fondo de Mantenimiento'),
        ('pro_retencion', 'Fondo Pro-Retención'),
        ('fondos_propios', 'Fondos Propios / Financiamiento Compartido'),
    ]

    ESTADOS = [
        ('borrador', 'Borrador'),
        ('en_cotizacion', 'En Cotización (Solicitando Ofertas)'),
        ('evaluacion', 'En Evaluación (Cotizaciones Recibidas)'),
        ('adjudicado', 'Adjudicado (Proveedor Seleccionado)'),
        ('orden_compra_emitida', 'Orden de Compra Emitida'),
        ('recepcionado', 'Recepcionado Conforme (Ingresado a Stock)'),
        ('anulado', 'Anulado / Cancelado'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='procesos_compra')
    codigo = models.CharField(max_length=40)  # ej: REQ-2026-001
    titulo = models.CharField(max_length=200) # ej: Adquisición de Insumos de Oficina y Papelería I Semestre
    descripcion = models.TextField(blank=True, null=True)
    tipo_fondo = models.CharField(max_length=30, choices=TIPO_FONDO, default='subvencion_general')
    centro_costo = models.CharField(max_length=100, blank=True, null=True) # ej: Coordinación Básica / UTP / Rectoría
    estado = models.CharField(max_length=30, choices=ESTADOS, default='en_cotizacion')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_limite_cotizacion = models.DateField(blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='procesos_compra_creados')
    
    # Adjudicación
    cotizacion_ganadora = models.ForeignKey('CotizacionProveedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='procesos_adjudicados')
    justificacion_adjudicacion = models.TextField(blank=True, null=True) # Exigencia Supereduc
    fecha_adjudicacion = models.DateTimeField(blank=True, null=True)
    adjudicado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='procesos_adjudicados_por')
    
    # Orden de Compra Oficial
    numero_orden_compra = models.CharField(max_length=50, blank=True, null=True) # ej: OC-2026-001
    fecha_emision_oc = models.DateTimeField(blank=True, null=True)
    
    # Recepción de Bodega / Stock
    fecha_recepcion = models.DateTimeField(blank=True, null=True)
    recepcionado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='procesos_recepcionados')
    observaciones_recepcion = models.TextField(blank=True, null=True)
    numero_guia_factura = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Proceso de Compra & Cotización"
        verbose_name_plural = "Procesos de Compra & Cotizaciones"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.codigo} - {self.titulo} ({self.get_estado_display()})"

    @property
    def total_cotizaciones(self):
        return self.cotizaciones.count()

    @property
    def cumple_normativa_3_cotizaciones(self):
        """Retorna True si tiene al menos 3 cotizaciones válidas registradas (exigencia Supereduc)."""
        return self.cotizaciones.count() >= 3

    @property
    def semaforo_cotizaciones(self):
        cnt = self.cotizaciones.count()
        if cnt == 0:
            return {'color': 'secondary', 'texto': '0/3 Cotizaciones', 'pct': 0, 'estado': 'vacio'}
        elif cnt == 1:
            return {'color': 'danger', 'texto': '1/3 Cotización (Insuficiente)', 'pct': 33, 'estado': 'insuficiente'}
        elif cnt == 2:
            return {'color': 'warning', 'texto': '2/3 Cotizaciones (Incompleto)', 'pct': 66, 'estado': 'incompleto'}
        else:
            return {'color': 'success', 'texto': f'{cnt}/3 Cotizaciones (Cumple Normativa)', 'pct': 100, 'estado': 'optimo'}

    @property
    def monto_estimado_o_ganador(self):
        if self.cotizacion_ganadora:
            return self.cotizacion_ganadora.monto_total
        menor = self.cotizaciones.order_by('monto_total').first()
        return menor.monto_total if menor else 0


class ItemProcesoCompra(models.Model):
    proceso = models.ForeignKey(ProcesoCompra, on_delete=models.CASCADE, related_name='items')
    item_inventario = models.ForeignKey(ItemInventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='requerimientos_compra')
    descripcion = models.CharField(max_length=200) # ej: Resmas de Papel Carta 75gr
    cantidad = models.PositiveIntegerField(default=1)
    unidad_medida = models.CharField(max_length=40, default='unidades')
    especificaciones_tecnicas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Ítem de Proceso de Compra"
        verbose_name_plural = "Ítems de Proceso de Compra"

    def __str__(self):
        return f"{self.cantidad} {self.unidad_medida} x {self.descripcion}"


class CotizacionProveedor(models.Model):
    proceso = models.ForeignKey(ProcesoCompra, on_delete=models.CASCADE, related_name='cotizaciones')
    proveedor = models.ForeignKey(ProveedorColegio, on_delete=models.CASCADE, related_name='cotizaciones_emitidas')
    numero_cotizacion_proveedor = models.CharField(max_length=80, blank=True, null=True) # ej: COT-9812
    fecha_cotizacion = models.DateField(default=timezone.now)
    validez_dias = models.PositiveIntegerField(default=30)
    
    # Valores
    monto_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    monto_total = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    
    # Condiciones
    plazo_entrega_dias = models.PositiveIntegerField(default=5)
    condiciones_pago = models.CharField(max_length=120, default='Transferencia 30 días') # ej: Contado, 30 días, etc.
    incluye_despacho = models.BooleanField(default=True)
    costo_despacho = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    # Documento PDF Oficial
    archivo_adjunto = models.FileField(upload_to='compras/cotizaciones/', blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    
    es_ganadora = models.BooleanField(default=False)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cotización de Proveedor"
        verbose_name_plural = "Cotizaciones de Proveedores"
        ordering = ['monto_total', 'plazo_entrega_dias']

    def __str__(self):
        return f"{self.proveedor.nombre} - ${self.monto_total:,.0f} ({self.proceso.codigo})"

    def save(self, *args, **kwargs):
        # Auto calcular IVA si monto_total o monto_neto fueron provistos
        if self.monto_neto > 0 and self.monto_total == 0:
            self.iva = round(self.monto_neto * Decimal('0.19'), 2)
            self.monto_total = self.monto_neto + self.iva
        elif self.monto_total > 0 and self.monto_neto == 0:
            self.monto_neto = round(self.monto_total / Decimal('1.19'), 2)
            self.iva = self.monto_total - self.monto_neto
        super().save(*args, **kwargs)


# ==============================================================================
# MODELOS: LECCIONARIO DIGITAL & PLANIFICACIÓN CURRICULAR (MINEDUC COMPLIANT)
# ==============================================================================

class RegistroLeccionario(models.Model):
    ACTIVIDADES_CHOICES = [
        ('catedra', 'Clase Expositiva / Cátedra'),
        ('grupal', 'Trabajo Colaborativo / Grupal'),
        ('laboratorio', 'Laboratorio / Práctico'),
        ('evaluacion', 'Evaluación / Prueba / Control'),
        ('taller', 'Taller de Ejercitación'),
        ('salida', 'Salida a Terreno / Actividad Externa'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='leccionarios')
    horario_clase = models.ForeignKey(HorarioClase, on_delete=models.SET_NULL, null=True, blank=True, related_name='leccionarios')
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.CASCADE, related_name='leccionarios')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='leccionarios')
    docente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leccionarios_firmados')
    bloque = models.ForeignKey(BloqueHorario, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha = models.DateField(default=timezone.now)
    oa_codigo = models.CharField(max_length=80, blank=True, null=True, help_text="Ej: OA 04, OA 07")
    contenido_tratado = models.TextField(help_text="Descripción pedagógica del contenido impartido en la clase")
    actividad_tipo = models.CharField(max_length=30, choices=ACTIVIDADES_CHOICES, default='catedra')
    observaciones = models.TextField(blank=True, null=True, help_text="Incidentes, retrasos o notas pedagógicas")
    
    # Firma Electrónica Simple con PIN
    firmado = models.BooleanField(default=False)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    hash_firma = models.CharField(max_length=64, blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de Leccionario"
        verbose_name_plural = "Registros de Leccionario"
        ordering = ['-fecha', '-bloque__orden', '-fecha_creacion']

    def __str__(self):
        return f"{self.fecha} - {self.asignatura.nombre} ({self.seccion.nombre}) - {self.docente.get_full_name() or self.docente.username}"


class PlanificacionCurricular(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada a UTP'),
        ('aprobada', 'Aprobada por UTP'),
        ('observada', 'Con Observaciones'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='planificaciones')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='planificaciones')
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.CASCADE, related_name='planificaciones')
    docente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='planificaciones_docente')
    
    titulo_unidad = models.CharField(max_length=200, help_text="Ej: Unidad 1: Álgebra y Ecuaciones Lineales")
    semestre = models.PositiveSmallIntegerField(default=1, choices=[(1, '1° Semestre'), (2, '2° Semestre')])
    anio_lectivo = models.PositiveIntegerField(default=2026)
    
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    
    oas_curriculares = models.TextField(help_text="Objetivos de Aprendizaje MINEDUC abordados")
    estrategias_metodologicas = models.TextField(blank=True, null=True)
    evaluacion_descripcion = models.TextField(blank=True, null=True, help_text="Instrumentos y formas de evaluación")
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    feedback_utp = models.TextField(blank=True, null=True, help_text="Retroalimentación o correcciones solicitadas por UTP")
    revisado_por_utp = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='planificaciones_auditadas')
    fecha_revision_utp = models.DateTimeField(null=True, blank=True)
    
    archivo_adjunto = models.FileField(upload_to='planificaciones/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Planificación Curricular"
        verbose_name_plural = "Planificaciones Curriculares"
        ordering = ['-anio_lectivo', 'semestre', 'fecha_inicio']

    def __str__(self):
        return f"{self.titulo_unidad} - {self.asignatura.nombre} ({self.seccion.nombre})"


# ==============================================================================
# MODELOS: PROGRAMA DE INTEGRACIÓN ESCOLAR (PIE / NEE - DECRETO 170 & 83)
# ==============================================================================

class FichaEstudiantePIE(models.Model):
    TIPO_NEE_CHOICES = [
        ('transitoria', 'NEE Transitoria (NEET)'),
        ('permanente', 'NEE Permanente (NEEP)'),
    ]

    DIAGNOSTICOS_CHOICES = [
        # Transitorias
        ('DEA', 'Dificultad Específica del Aprendizaje (DEA)'),
        ('TEL_EXPRESIVO', 'Trastorno Específico del Lenguaje (TEL Expresivo)'),
        ('TEL_MIXTO', 'Trastorno Específico del Lenguaje (TEL Mixto)'),
        ('TDAH', 'Trastorno por Déficit Atencional con/sin Hiperactividad (TDA/TDAH)'),
        ('FIL', 'Funcionamiento Intelectual Limítrofe (FIL)'),
        # Permanentes
        ('TEA', 'Trastorno del Espectro Autista (TEA)'),
        ('DI_LEVE', 'Discapacidad Intelectual Leve'),
        ('DI_MODERADA', 'Discapacidad Intelectual Moderada'),
        ('DISCAPACIDAD_VISUAL', 'Discapacidad Visual / Baja Visión / Ceguera'),
        ('DISCAPACIDAD_AUDITIVA', 'Discapacidad Auditiva / Hipoacusia / Sordera'),
        ('DISCAPACIDAD_MOTORA', 'Discapacidad Motora / Física'),
        ('MULTIDEFICIT', 'Multidéficit'),
        ('OTRO', 'Otro Diagnóstico Clínico'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='estudiantes_pie')
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE, related_name='ficha_pie')
    
    tipo_nee = models.CharField(max_length=20, choices=TIPO_NEE_CHOICES, default='transitoria')
    diagnostico = models.CharField(max_length=30, choices=DIAGNOSTICOS_CHOICES)
    diagnostico_personalizado = models.CharField(max_length=200, blank=True, null=True, help_text="Especificación médica o neurólogo si aplica")
    
    fecha_ingreso = models.DateField(default=timezone.now)
    fecha_revaluacion = models.DateField(null=True, blank=True, help_text="Fecha máxima para informe de reevaluación integral")
    
    profesional_a_cargo = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='casos_pie_asignados', help_text="Educadora Diferencial o Psicopedagoga a cargo")
    
    requiere_paci = models.BooleanField(default=True, help_text="Indica si cuenta con Plan de Adecuación Curricular Individual")
    activo = models.BooleanField(default=True)
    
    informe_medico_pdf = models.FileField(upload_to='pie/informes/', blank=True, null=True)
    observaciones_ingreso = models.TextField(blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ficha de Estudiante PIE"
        verbose_name_plural = "Fichas de Estudiantes PIE"
        ordering = ['estudiante__nombre_completo']

    def __str__(self):
        return f"PIE: {self.estudiante.nombre_completo} ({self.get_diagnostico_display()})"


class AtencionEspecialistaPIE(models.Model):
    ROLES_ESPECIALISTA = [
        ('educadora_diferencial', 'Educadora Diferencial'),
        ('psicologo', 'Psicólogo / Psicóloga'),
        ('fonoaudiologo', 'Fonoaudiólogo / Fonoaudióloga'),
        ('terapeuta_ocupacional', 'Terapeuta Ocupacional'),
        ('psicopedagogo', 'Psicopedagogo / Psicopedagoga'),
        ('otro', 'Otro Profesional de Apoyo'),
    ]

    TIPO_SESION = [
        ('aula_recursos', 'Aula de Recursos (Apoyo Específico)'),
        ('aula_regular', 'Aula Regular (Co-Docencia / Acompañamiento)'),
        ('individual', 'Sesión Individual / Taller Especialista'),
        ('apoderado', 'Entrevista con Apoderado / Familia'),
        ('equipo_aula', 'Reunión de Trabajo Colaborativo'),
    ]

    ficha_pie = models.ForeignKey(FichaEstudiantePIE, on_delete=models.CASCADE, related_name='atenciones')
    especialista = models.ForeignKey(User, on_delete=models.CASCADE, related_name='atenciones_pie_realizadas')
    rol_especialista = models.CharField(max_length=30, choices=ROLES_ESPECIALISTA, default='educadora_diferencial')
    
    fecha = models.DateField(default=timezone.now)
    tipo_sesion = models.CharField(max_length=25, choices=TIPO_SESION, default='aula_recursos')
    
    objetivo_trabajado = models.CharField(max_length=250, help_text="Habilidad o contenido trabajado en la sesión")
    resumen_intervencion = models.TextField(help_text="Detalle de actividades realizadas y desempeño del estudiante")
    acuerdos_pedagogicos = models.TextField(blank=True, null=True, help_text="Estrategias o acuerdos para el docente de aula o la familia")
    
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Atención de Especialista PIE"
        verbose_name_plural = "Atenciones de Especialistas PIE"
        ordering = ['-fecha', '-fecha_registro']

    def __str__(self):
        return f"{self.fecha} - {self.ficha_pie.estudiante.nombre_completo} ({self.get_rol_especialista_display()})"


class PlanAdecuacionCurricular(models.Model):
    ficha_pie = models.ForeignKey(FichaEstudiantePIE, on_delete=models.CASCADE, related_name='pacis')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.SET_NULL, null=True, blank=True, help_text="Asignatura específica o General")
    anio_lectivo = models.PositiveIntegerField(default=2026)
    
    # 1. Adecuaciones de Acceso (Decreto 83)
    tiempo_adicional = models.BooleanField(default=True, help_text="Tiempo adicional en evaluaciones")
    adaptacion_materiales = models.TextField(blank=True, null=True, help_text="Uso de material concreto, letra aumentada, apoyos visuales")
    espacio_evaluacion = models.TextField(blank=True, null=True, help_text="Ubicación preferencial en sala o aula de recursos")
    
    # 2. Adecuaciones en los Objetivos de Aprendizaje (OAs)
    graduacion_complejidad = models.TextField(blank=True, null=True, help_text="Graduación o simplificación de exigencia en OAs")
    priorizacion_objetivos = models.TextField(blank=True, null=True, help_text="OAs prioritarios focalizados")
    
    # 3. Evaluación Diferenciada
    estrategias_evaluacion = models.TextField(help_text="Rúbricas adaptadas, pruebas orales, ponderación flexible")
    
    aprobado_utp = models.BooleanField(default=False)
    fecha_aprobacion = models.DateField(null=True, blank=True)
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pacis_aprobados')
    
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plan de Adecuación Curricular (PACI)"
        verbose_name_plural = "Planes de Adecuación Curricular (PACI)"
        ordering = ['-anio_lectivo', '-fecha_creacion']

    def __str__(self):
        return f"PACI {self.anio_lectivo} - {self.ficha_pie.estudiante.nombre_completo}"


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: MENSAJES DE CHAT DE SOPORTE (Super Admin ↔ Colegio)
# ══════════════════════════════════════════════════════════════════════════════

class MensajeChat(models.Model):
    REMITENTE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('colegio', 'Colegio'),
    ]

    colegio = models.ForeignKey(
        Colegio,
        on_delete=models.CASCADE,
        related_name='mensajes_chat',
        verbose_name="Colegio"
    )
    remitente = models.CharField(
        max_length=20,
        choices=REMITENTE_CHOICES,
        default='superadmin',
        verbose_name="Remitente"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensajes_chat_enviados',
        verbose_name="Usuario Remitente"
    )
    contenido = models.TextField(verbose_name="Contenido del Mensaje")
    leido = models.BooleanField(default=False, verbose_name="¿Leído?")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Envío")

    class Meta:
        verbose_name = "Mensaje de Chat"
        verbose_name_plural = "Mensajes de Chat"
        ordering = ['fecha_creacion']

    def __str__(self):
        return f"[{self.get_remitente_display()}] {self.colegio.nombre} ({self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}): {self.contenido[:40]}"










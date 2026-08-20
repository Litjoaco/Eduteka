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
    horas_semanales = models.PositiveIntegerField(default=4, help_text="Horas pedagógicas semanales")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        unique_together = ('curso', 'nombre')

    def __str__(self):
        return f"{self.nombre} - {self.curso.nombre}"


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


# ==============================================================================
# MÓDULO DE FINANZAS, TESORERÍA, CAJA CHICA Y FACTURAS
# ==============================================================================

class CuentaFinanciera(models.Model):
    TIPO_CUENTA = [
        ('caja_chica', 'Caja Chica'),
        ('cuenta_bancaria', 'Cuenta Bancaria / Corriente'),
        ('caja_general', 'Caja General'),
        ('otro', 'Otro'),
    ]

    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='cuentas_financieras')
    nombre = models.CharField(max_length=150) # Ej: Caja Chica Dirección, Banco Santander Cta Cte
    tipo = models.CharField(max_length=30, choices=TIPO_CUENTA, default='caja_chica')
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
    categoria = models.ForeignKey(CategoriaFinanciera, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    concepto = models.CharField(max_length=200) # Ej: Compra de plumones y resmas de papel
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField(default=timezone.now)
    metodo_pago = models.CharField(max_length=30, choices=METODOS_PAGO, default='efectivo')
    numero_comprobante = models.CharField(max_length=100, blank=True, null=True) # Boleta / Voucher
    comprobante_adjunto = models.FileField(upload_to='finanzas/comprobantes/', blank=True, null=True)
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
    tipo_documento = models.CharField(max_length=30, choices=TIPO_DOC, default='factura_afecta')
    folio = models.CharField(max_length=50) # Número de Factura
    proveedor_nombre = models.CharField(max_length=150) # Ej: Librería y Papelería Central SpA
    proveedor_rut = models.CharField(max_length=20, blank=True, null=True)
    fecha_emision = models.DateField(default=timezone.now)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    
    monto_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    monto_iva = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    monto_total = models.DecimalField(max_digits=14, decimal_places=2)
    
    estado_pago = models.CharField(max_length=20, choices=ESTADO_PAGO, default='pendiente')
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








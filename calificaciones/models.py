from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from colegios.models import Colegio, SeccionCurso, Asignatura, Estudiante

class Evaluacion(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='evaluaciones')
    seccion = models.ForeignKey(SeccionCurso, on_delete=models.CASCADE, related_name='evaluaciones')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='evaluaciones')
    
    nombre = models.CharField(max_length=100)
    periodo_nombre = models.CharField(max_length=50, default="1° Semestre")
    fecha = models.DateField()
    ponderacion = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, help_text="Coeficiente o Porcentaje de la nota")

    
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        ordering = ['fecha', 'id']

    def __str__(self):
        return f"{self.nombre} - {self.asignatura.nombre} ({self.seccion.nombre})"


class Nota(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='notas')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='notas')
    
    # En Chile las notas van de 1.0 a 7.0 (con un decimal)
    valor = models.DecimalField(
        max_digits=3, 
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(7.0)]
    )
    observacion = models.CharField(max_length=200, blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        unique_together = ('evaluacion', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.nombre_completo}: {self.valor} en {self.evaluacion.nombre}"


class ObservacionBoletin(models.Model):
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name='observaciones_boletin')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='observaciones_boletin')
    periodo_nombre = models.CharField(max_length=50, default="1° Semestre")
    texto = models.TextField()

    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Observación de Boletín"
        verbose_name_plural = "Observaciones de Boletín"
        unique_together = ('estudiante', 'periodo_nombre')

    def __str__(self):
        return f"Observación {self.estudiante.nombre_completo} ({self.periodo_nombre})"


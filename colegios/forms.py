from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from .models import Colegio
from planes.models import Plan, Modulo

def validar_rut(rut):
    rut = rut.upper().replace("-", "").replace(".", "")
    if len(rut) < 2:
        return False
    rut_aux = rut[:-1]
    dv = rut[-1:]
    if not rut_aux.isdigit():
        return False
    revertido = map(int, reversed(str(rut_aux)))
    factors = [2, 3, 4, 5, 6, 7]
    s = sum(d * factors[i % 6] for i, d in enumerate(revertido))
    res = 11 - (s % 11)
    if res == 11:
        dv_esperado = "0"
    elif res == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(res)
    return dv == dv_esperado

class RegistroColegioPaso1Form(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True)
    telefono = forms.CharField(
        validators=[RegexValidator(r'^\+?1?\d{8,15}$', message="Ingrese un teléfono válido (entre 8 y 15 dígitos).")],
        required=True
    )
    rut_administrador = forms.CharField(max_length=12, required=True)
    telefono_administrador = forms.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{8,15}$', message="Ingrese un teléfono válido (entre 8 y 15 dígitos).")],
        required=True
    )

    class Meta:
        model = Colegio
        fields = [
            'nombre', 'nombre_administrador', 'correo_institucional',
            'telefono', 'region', 'ciudad_comuna', 'tipo_institucion', 'cantidad_alumnos'
        ]

    def clean_correo_institucional(self):
        correo = self.cleaned_data.get('correo_institucional')
        if correo:
            correo = correo.strip().lower()
        if User.objects.filter(username=correo).exists():
            raise forms.ValidationError("Este correo ya está registrado. Por favor, inicie sesión o utilice otro.")
        return correo

    def clean_rut_administrador(self):
        rut = self.cleaned_data.get('rut_administrador', '')
        if not validar_rut(rut):
            raise forms.ValidationError("El RUT del administrador no es válido.")
        return rut.upper()

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres para ser segura.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', "Las contraseñas no coinciden.")
        return cleaned_data

class RegistroColegioPaso2Form(forms.Form):
    PLAN_MAPPING = {
        'basico': 'Básico',
        'profesional': 'Profesional',
        'institucional': 'Institucional',
        'personalizado': 'Personalizado',
    }

    MODULO_MAPPING = {
        'libro_clases': 'Libro de clases',
        'asistencia': 'Asistencia',
        'perfil_alumno': 'Perfil del estudiante',
        'calendario': 'Calendario',
        'reportes': 'Reportes y analíticas',
        'contabilidad': 'Finanzas',
        'proveedores': 'Proveedores',
        'simce': 'SIMCE',
    }

    plan = forms.CharField(required=True)
    tipo_facturacion = forms.ChoiceField(choices=[('mensual', 'Mensual'), ('anual', 'Anual')], required=True)
    modulos = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            self.fields['modulos'].choices = [(m, m) for m in self.data.getlist('modulos')]

    def clean_plan(self):
        plan_val = self.cleaned_data.get('plan')
        if not plan_val:
            raise forms.ValidationError("Debe seleccionar un plan.")
        
        # 1. Si viene como ID numérico
        if str(plan_val).isdigit():
            plan_obj = Plan.objects.filter(id=int(plan_val)).first()
            if plan_obj:
                return plan_obj

        # 2. Si viene como string / nombre
        nombre_real = self.PLAN_MAPPING.get(plan_val, plan_val)
        plan_obj = Plan.objects.filter(nombre__iexact=nombre_real).first()
        if not plan_obj:
            plan_obj = Plan.objects.filter(nombre__icontains=nombre_real).first()
        
        if plan_obj:
            return plan_obj

        raise forms.ValidationError(f"El plan seleccionado '{plan_val}' no existe en el sistema.")

    def clean_modulos(self):
        modulos_keys = self.cleaned_data.get('modulos', [])
        modulos = []
        for key in modulos_keys:
            if str(key).isdigit():
                mod = Modulo.objects.filter(id=int(key)).first()
                if mod:
                    modulos.append(mod)
                    continue

            nombre_real = self.MODULO_MAPPING.get(key, key.replace('_', ' ').strip())
            mod = Modulo.objects.filter(nombre__iexact=nombre_real).first()
            if not mod:
                mod = Modulo.objects.filter(nombre__icontains=nombre_real).first()
            if mod:
                modulos.append(mod)
        return modulos

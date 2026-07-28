from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from .models import PerfilUsuario

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

class RegistroUsuarioForm(forms.ModelForm):
    nombre_completo = forms.CharField(max_length=150, required=True)
    rut = forms.CharField(max_length=12, required=True, label="RUT")
    telefono = forms.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{8,15}$', message="Ingrese un teléfono válido (entre 8 y 15 dígitos).")],
        required=True, label="Teléfono"
    )
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '')
        if not validar_rut(rut):
            raise forms.ValidationError("El RUT ingresado no es válido.")
        return rut.upper()

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Usamos el email como username en Django
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            PerfilUsuario.objects.create(
                usuario=user,
                nombre_completo=self.cleaned_data['nombre_completo'],
                rut=self.cleaned_data.get('rut', ''),
                telefono=self.cleaned_data.get('telefono', '')
            )
        return user
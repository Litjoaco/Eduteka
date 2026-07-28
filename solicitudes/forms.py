from django import forms
from .models import SolicitudAcceso

class SolicitudAccesoForm(forms.ModelForm):
    class Meta:
        model = SolicitudAcceso
        fields = ['colegio', 'rol_solicitado', 'mensaje']
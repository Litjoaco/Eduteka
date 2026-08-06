from django import forms
from .models import Plan

class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['nombre', 'descripcion', 'precio_mensual', 'precio_anual', 'recomendado', 'activo', 'modulos']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Plan Estándar'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del plan'}),
            'precio_mensual': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_anual': forms.NumberInput(attrs={'class': 'form-control'}),
            'recomendado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'modulos': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }


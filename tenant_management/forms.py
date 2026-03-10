from django import forms
from .models import Client
from django.utils import timezone

from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    paid_until = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),  # Usa um seletor de data moderno
        required=True
    )

    class Meta:
        model = Client
        fields = ['name', 'schema_name', 'paid_until', 'on_trial', 'cnpj', 'endereco', 'telefone']
        labels = {
            'name': 'Nome do Cliente',
            'schema_name': 'Nome do Esquema',
            'paid_until': 'Data de Expiração do Pagamento',
            'on_trial': 'Em Período de Teste',
            'cnpj': 'CNPJ',
            'endereco': 'Endereço',
            'telefone': 'Telefone',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nome do cliente'}),
            'schema_name': forms.TextInput(attrs={'placeholder': 'nome_esquema'}),
            'cnpj': forms.TextInput(attrs={'placeholder': '00.000.000/0000-00'}),
            'endereco': forms.TextInput(attrs={'placeholder': 'Rua, Número, Bairro, Cidade'}),
            'telefone': forms.TextInput(attrs={'placeholder': '(00) 00000-0000'}),
        }

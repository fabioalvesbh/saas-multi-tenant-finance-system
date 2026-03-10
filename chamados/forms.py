from django import forms
from django.contrib.auth import get_user_model

from .models import Chamado

User = get_user_model()


class ChamadoForm(forms.ModelForm):
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Direcionar a (usuário)",
        help_text="O chamado só será visível para você e para o usuário selecionado.",
    )

    class Meta:
        model = Chamado
        fields = [
            "titulo",
            "descricao",
            "tipo",
            "prioridade",
            "responsavel",
            "departamento_destino",
            "anexo",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        if self.request_user:
            self.fields["responsavel"].queryset = (
                User.objects.filter(is_active=True)
                .exclude(pk=self.request_user.pk)
                .exclude(is_superuser=True)
                .exclude(username__iexact="administrator")
                .order_by("username")
            )


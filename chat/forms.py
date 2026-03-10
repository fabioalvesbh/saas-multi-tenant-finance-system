from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


class ScheduleMeetingForm(forms.Form):
    titulo = forms.CharField(label="Título da reunião", max_length=140)
    quando = forms.DateTimeField(
        label="Data e hora",
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
            }
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    participantes = forms.ModelMultipleChoiceField(
        label="Participantes",
        queryset=User.objects.none(),
        required=False,
        help_text="Selecione quem deve receber o convite com o link da reunião.",
    )
    convidados_externos = forms.CharField(
        label="Convidados externos (e-mails)",
        required=False,
        help_text="Opcional: informe e-mails externos separados por vírgula ou ponto e vírgula.",
    )

    def __init__(self, *args, **kwargs) -> None:
        request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        if request_user is not None:
            qs = (
                User.objects.filter(is_active=True)
                .exclude(pk=request_user.pk)
                .exclude(is_superuser=True)
                .exclude(username__iexact="administrator")
                .order_by("username")
            )
            self.fields["participantes"].queryset = qs


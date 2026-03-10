from django.conf import settings
from django.db import models


class Chamado(models.Model):
    class Tipo(models.TextChoices):
        TI = "TI", "TI / Informática"
        INFRA = "INFRA", "Infraestrutura"
        SEGURANCA = "SEGURANCA", "Segurança"
        VISITANTE = "VISITANTE", "Visitantes / Portaria"
        MANUTENCAO = "MANUTENCAO", "Manutenção"

    class Prioridade(models.TextChoices):
        BAIXA = "BAIXA", "Baixa"
        MEDIA = "MEDIA", "Média"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em atendimento"
        AGUARDANDO = "AGUARDANDO", "Aguardando"
        RESOLVIDO = "RESOLVIDO", "Resolvido"
        CANCELADO = "CANCELADO", "Cancelado"

    titulo = models.CharField(max_length=140)
    descricao = models.TextField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    prioridade = models.CharField(
        max_length=20, choices=Prioridade.choices, default=Prioridade.MEDIA
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ABERTO
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chamados_abertos",
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="chamados_atendidos",
        null=True,
        blank=True,
    )
    departamento_destino = models.CharField(
        max_length=100,
        blank=True,
        help_text="Departamento/setor que deve atender o chamado.",
    )
    anexo = models.FileField(
        upload_to="chamados/anexos/",
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-criado_em",)

    def __str__(self) -> str:
        return f"#{self.id} - {self.titulo}"


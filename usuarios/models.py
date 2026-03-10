from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    class Role(models.TextChoices):
        PORTARIA = "PORTARIA", "Portaria"
        GERENTE_ADMIN = "GERENTE_ADMIN", "Gerente administrativo"
        TI = "TI", "TI / Informática"
        COMPRAS = "COMPRAS", "Compras"
        INFRA = "INFRA", "Infraestrutura"
        SEGURANCA = "SEGURANCA", "Segurança"
        OUTRO = "OUTRO", "Outro"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    company = models.CharField(
        max_length=100,
        blank=True,
        help_text="Empresa (ex.: Kuttner do Brasil, Kuttner Automation).",
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Departamento/setor do colaborador (ex.: Portaria, TI, Compras).",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.OUTRO,
    )
    display_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nome exibido na lista de conversas (opcional).",
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text="Foto do perfil exibida no chat.",
    )

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()

    @property
    def status(self) -> str:
        """
        Retorna 'online', 'away' ou 'offline' com base no último acesso.
        """
        if not self.last_seen:
            return "offline"
        now = timezone.now()
        delta = now - self.last_seen
        seconds = delta.total_seconds()
        if seconds <= 120:
            return "online"
        if seconds <= 600:
            return "away"
        return "offline"


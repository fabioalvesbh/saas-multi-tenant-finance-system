from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """
    Representa um canal de conversa entre usuários.
    Para começar vamos usar conversas privadas (até 2 participantes),
    mas o modelo já permite mais participantes no futuro.
    """

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        users = ", ".join(self.participants.values_list("username", flat=True))
        return f"Conversa ({users})"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    text = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="chat/attachments/", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.sender}: {self.text[:40]}"


class Meeting(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativa"
        CANCELLED = "CANCELLED", "Cancelada"

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_meetings",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="meetings",
        blank=True,
    )
    title = models.CharField(max_length=140)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    room_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


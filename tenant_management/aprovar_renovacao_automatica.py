from django.utils import timezone
from tenant_management.models import Client, SubscriptionRequest, WebhookLog
import random
import string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.management import call_command
from django.db import connection
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django_tenants.utils import schema_context, get_tenant_model
from login.views import group_required
from .forms import ClientForm
from .models import Client, TenantDeleteRequest, Informativo, SubscriptionRequest

def aprovar_renovacao_automatica(email_cliente, plano, payload=None, evento="renovacao_auto"):
    dias_dict = {'mensal': 30, 'semestral': 180, 'anual': 365}
    dias = dias_dict.get(plano)

    if not dias:
        WebhookLog.objects.create(
            evento=f"erro_{evento}_plano",
            email_cliente=email_cliente,
            dados_recebidos=payload or {},
            resposta_enviada=f"Plano inválido: {plano}"
        )
        return False, "Plano inválido"

    sub = SubscriptionRequest.objects.filter(email=email_cliente, tipo='renovacao', status='pendente').first()
    if not sub:
        WebhookLog.objects.create(
            evento=f"erro_{evento}_assinatura",
            email_cliente=email_cliente,
            dados_recebidos=payload or {},
            resposta_enviada="Assinatura original não encontrada para renovação"
        )
        return False, "Assinatura não encontrada"

    try:
        client = Client.objects.get(email=email_cliente)
    except Client.DoesNotExist:
        WebhookLog.objects.create(
            evento=f"erro_{evento}_cliente",
            email_cliente=email_cliente,
            dados_recebidos=payload or {},
            resposta_enviada="Tenant não encontrado"
        )
        return False, "Tenant não encontrado"

    nova_data = max(client.paid_until, timezone.now().date()) + timezone.timedelta(days=dias)
    client.paid_until = nova_data
    client.plano = plano
    client.save()

    sub.status = 'aprovado'
    sub.save()

    WebhookLog.objects.create(
        evento=evento,
        email_cliente=email_cliente,
        dados_recebidos=payload or {},
        resposta_enviada=f"Renovação aprovada até {nova_data}",
        schema_criado=client.schema_name
    )

    return True, "Renovação processada"
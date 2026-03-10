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

@login_required
@group_required('Desenvolvedores')
def lista_renovacoes_pendentes(request):
    solicitacoes = SubscriptionRequest.objects.filter(tipo='renovacao').order_by('-criado_em')
    return render(request, 'tenant_management/renovacoes_pendentes.html', {
        'solicitacoes': solicitacoes
    })

from django.views.decorators.http import require_POST

@login_required
@require_POST
@group_required('Desenvolvedores')
def rejeitar_renovacao(request, id):
    sub = get_object_or_404(SubscriptionRequest, id=id, tipo='renovacao', status='pendente')
    sub.status = 'rejeitado'
    sub.save()
    messages.info(request, f"Renovação de {sub.email} foi rejeitada.")
    return redirect('tenant_management:lista_renovacoes')



from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from tenant_management.models import SubscriptionRequest, Client

@login_required
@group_required('Desenvolvedores')
def aprovar_renovacao(request, id):
    sub = get_object_or_404(SubscriptionRequest, id=id, tipo='renovacao', status='pendente')

    dias_dict = {'mensal': 30, 'semestral': 180, 'anual': 365}
    dias = dias_dict.get(sub.plano)
    if not dias:
        messages.error(request, f"Plano inválido: {sub.plano}")
        return redirect('tenant_management:lista_renovacoes')

    client = Client.objects.filter(email=sub.email).first()
    if not client:
        messages.error(request, f"Cliente com e-mail {sub.email} não encontrado.")
        return redirect('tenant_management:lista_renovacoes')

    nova_data = max(client.paid_until, timezone.now().date()) + timezone.timedelta(days=dias)
    client.paid_until = nova_data
    client.plano = sub.plano
    client.save()

    sub.status = 'aprovado'
    sub.save()

    send_mail(
        subject="Renovação aprovada – SaaS Demo",
        message=(
            f"Olá {sub.nome},\n\n"
            f"Seu plano foi renovado com sucesso!\n"
            f"Nova vigência: até {nova_data:%d/%m/%Y}.\n\n"
            f"Equipe SaaS Demo"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[client.email],
        fail_silently=False
    )

    messages.success(request, f"Plano de {client.schema_name} renovado até {nova_data:%d/%m/%Y}.")
    return redirect('tenant_management:lista_renovacoes')
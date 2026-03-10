from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

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
def register_tenant(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tenant registrado com sucesso!')
            return redirect('tenant_management:tenant_list')
        else:
            messages.error(request, 'Erro ao registrar o tenant.')
    else:
        form = ClientForm()

    return render(request, 'tenant_management/register_tenant.html', {'form': form})



@require_http_methods(["POST", "GET"])
@login_required
@group_required('Desenvolvedores')
def solicitar_exclusao_tenant(request, tenant_id):
    tenant = get_object_or_404(Client, id=tenant_id)

    if request.method == 'POST':
        # 👇 garante que a verificação/criação rode dentro do schema do tenant
        with schema_context(tenant.schema_name):
            if TenantDeleteRequest.objects.filter(tenant=tenant, approved=False).exists():
                msg = "Já existe uma solicitação pendente para este tenant."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'message': msg}, status=409)
                messages.warning(request, msg)
                return redirect('tenant_management:tenant_list')

            TenantDeleteRequest.objects.create(
                tenant=tenant,
                requested_by=request.user,
                status='pendente',
                approved=False
            )

        msg = "Solicitação enviada para aprovação do administrador."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': msg})
        messages.success(request, msg)
        return redirect('tenant_management:tenant_list')

    # --- GET: cair aqui só se o usuário navegou direto ----------------
    return render(
        request,
        'tenant_management/confirm_delete_tenant.html',
        {'tenant': tenant}
    )


@login_required
@user_passes_test(lambda u: u.groups.filter(name='Administrador').exists())
def aprovar_exclusao(request, req_id):
    req = get_object_or_404(TenantDeleteRequest, id=req_id, status='pendente')
    tenant = req.tenant

    if request.method == 'POST':
        User = get_user_model()

        # 👇 executa a deleção dentro do schema do tenant
        with schema_context(tenant.schema_name):
            # Apaga usuários vinculados (cascade nos relacionamentos)
            users = User.objects.filter(tenant=tenant)
            emails = list(users.values_list('email', flat=True))
            users.delete()

            # Apaga pedidos de assinatura relacionados
            SubscriptionRequest.objects.filter(email__in=emails).delete()

        # Atualiza a solicitação
        req.status = 'aprovado'
        req.approved = True
        req.approved_by = request.user
        req.approved_at = timezone.now()
        req.save()

        # Deleta o schema no banco (já sem dados ativos)
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS \"{tenant.schema_name}\" CASCADE')

        # Deleta o tenant (cascade em Domain, DeleteRequests, etc.)
        tenant.delete()

        messages.success(request, "Tenant, usuários e e-mails foram excluídos com sucesso.")
        return redirect('tenant_management:painel_aprovacoes')

    return render(request, 'tenant_management/confirm_approve.html', {'req': req})


# Rejeitar solicitação de exclusão
@login_required
@user_passes_test(lambda u: u.groups.filter(name='Administrador').exists())
def rejeitar_exclusao_tenant(request, solicitacao_id):
    solicitacao = get_object_or_404(TenantDeleteRequest, id=solicitacao_id)
    solicitacao.delete()
    messages.info(request, "Solicitação de exclusão rejeitada e removida.")
    return redirect('tenant_management:painel_aprovacoes')

# Painel de aprovações (Admin)
@login_required
@user_passes_test(lambda u: u.groups.filter(name='Administrador').exists())
def painel_aprovacoes(request):
    pendentes = TenantDeleteRequest.objects.filter(approved=False)
    return render(request, 'tenant_management/lista_aprovacoes.html', {'pendentes': pendentes})
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
def tenant_list(request):
    tenants = Client.objects.all()
    return render(request, 'tenant_management/tenant_list.html', {'tenants': tenants})


# Editar Tenant
@login_required
@group_required('Desenvolvedores')
def edit_tenant(request, tenant_id):
    tenant = get_object_or_404(Client, id=tenant_id)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tenant atualizado com sucesso!')
            return redirect('tenant_management:tenant_list')
        else:
            messages.error(request, 'Erro ao atualizar o tenant.')
    else:
        form = ClientForm(instance=tenant)

    return render(request, 'tenant_management/edit_tenant.html', {
        'form': form,
        'tenant': tenant
    })

# Listar usuários de um tenant
@login_required
@group_required('Desenvolvedores')
def tenant_users(request, tenant_id):
    tenant = get_object_or_404(Client, id=tenant_id)
    User = get_user_model()
    users = User.objects.filter(tenant=tenant)
    return render(request, 'tenant_management/tenant_users.html', {
        'tenant': tenant,
        'users': users
    })


# Deletar usuário e todos os dados relacionados
@login_required
@group_required('Desenvolvedores')
def delete_user(request, tenant_id, user_id):
    tenant = get_object_or_404(Client, id=tenant_id)
    User = get_user_model()
    user = get_object_or_404(User, id=user_id, tenant=tenant)

    if request.method == 'POST':
        email = user.email
        user.delete()
        SubscriptionRequest.objects.filter(email=email).delete()
        messages.success(request, f"Usuário {email} e todos os dados relacionados foram removidos.")
        return redirect('tenant_management:tenant_users', tenant_id=tenant_id)

    return render(request, 'tenant_management/confirm_delete_user.html', {
        'tenant': tenant,
        'user': user
    })
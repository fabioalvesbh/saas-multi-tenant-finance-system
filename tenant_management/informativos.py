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
@user_passes_test(lambda u: u.groups.filter(name='Desenvolvedores').exists())
def gerenciar_informativos(request):
    with schema_context('public'):
        if request.method == 'POST':
            Informativo.objects.create(
                titulo=request.POST.get('titulo'),
                mensagem=request.POST.get('mensagem'),
                data_programada=request.POST.get('data_programada')
            )
            messages.success(request, "Informativo salvo.")
            return redirect('tenant_management:gerenciar_informativos')

        # ⬅️ Esta linha PRECISA estar dentro do schema_context
        informativos = Informativo.objects.order_by('-data_programada')

        return render(request, 'tenant_management/gerenciar_informativos.html', {
            'informativos': informativos
        })
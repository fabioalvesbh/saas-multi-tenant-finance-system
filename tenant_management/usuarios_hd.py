from django.contrib.auth import get_user_model
from tenant_management.models import Client
from django_tenants.utils import schema_context
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
def usuarios_hd(request):
    User = get_user_model()
    registros = []

    for client in Client.objects.all():
        with schema_context(client.schema_name):
            for user in User.objects.all():
                registros.append({
                    "nome": user.get_full_name() or user.username,
                    "email": user.email,
                    "tenant_nome": client.name,
                    "schema": client.schema_name,
                    "espaco_extra_mb": client.espaco_extra_mb,
                    "espaco_total_mb": 1024 + client.espaco_extra_mb
                })

    return render(request, "tenant_management/usuarios_hd.html", {"registros": registros})
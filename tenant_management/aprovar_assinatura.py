import random
import string
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django_tenants.utils import schema_context
from tenant_management.models import SubscriptionRequest, Client, WebhookLog
from django.conf import settings
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


def gerar_senha_segura(tamanho=14):
    if tamanho < 8:
        raise ValueError("Tamanho mínimo da senha deve ser 8 caracteres.")

    categorias = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice("!@#$%&*-_=+.,:;?")
    ]

    todos = string.ascii_letters + string.digits + "!@#$%&*-_=+.,:;?"
    restantes = random.choices(todos, k=tamanho - len(categorias))
    senha_lista = categorias + restantes
    random.shuffle(senha_lista)
    return ''.join(senha_lista)


@login_required
@group_required('Desenvolvedores')
def aprovar_assinatura(request, id):
    if request.method != 'POST':
        messages.error(request, "Requisição inválida.")
        return redirect('tenant_management:lista_assinaturas')

    sub = get_object_or_404(SubscriptionRequest, id=id)  # <- aceita qualquer status
    schema_name = sub.email.split('@')[0].replace('.', '_').replace('-', '_')
    senha = gerar_senha_segura()
    User = get_user_model()

    if Client.objects.filter(schema_name=schema_name).exists():
        messages.error(request, f"Schema '{schema_name}' já existe.")
        return redirect('tenant_management:lista_assinaturas')

    dias = {'trial': 5, 'mensal': 30, 'semestral': 180, 'anual': 365}.get(sub.plano, 5)

    tenant = Client.objects.create(
        name=sub.nome,
        schema_name=schema_name,
        paid_until=timezone.now() + timezone.timedelta(days=dias),
        on_trial=(sub.plano == 'trial'),
        cnpj=sub.documento,
        endereco=sub.endereco,
        telefone=sub.telefone,
        plano=sub.plano,
        email=sub.email
    )

    call_command('migrate_schemas', schema_name=schema_name, interactive=False, verbosity=0)

    with schema_context(schema_name):
        user = User.objects.create_user(username=sub.email, email=sub.email, password=senha)
        user.tenant = tenant
        grupo_owner, _ = Group.objects.get_or_create(name='owner')
        user.groups.add(grupo_owner)

        user.save()

    send_mail(
        subject="Acesso ao sistema SaaS Demo",
        message=(f"Olá {sub.nome},\n\nSeu acesso foi aprovado!\n\n"
                 f"🔑 Usuário: {sub.email}\n"
                 f"🔒 Senha: {senha}\n"
                 f"🌐 Acesse: {getattr(settings, 'SITE_URL', 'https://app.example-saas.com')}\n"),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[sub.email],
        fail_silently=False
    )

    sub.status = 'aprovado'
    sub.save()

    messages.success(request, f"Tenant '{schema_name}' criado e acesso enviado para {sub.email}.")
    return redirect('tenant_management:lista_assinaturas')

# Lista de assinaturas pendentes
@login_required
@group_required('Desenvolvedores')
def lista_assinaturas_pendentes(request):
    todas = SubscriptionRequest.objects.all().order_by('-criado_em')
    return render(request, 'tenant_management/assinaturas_pendentes.html', {
        'solicitacoes': todas
    })

def gerar_senha_segura(tamanho=14):
    if tamanho < 8:
        raise ValueError("Tamanho mínimo da senha deve ser 8 caracteres.")

    categorias = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice("!@#$%&*-_=+.,:;?")
    ]

    todos = string.ascii_letters + string.digits + "!@#$%&*-_=+.,:;?"
    restantes = random.choices(todos, k=tamanho - len(categorias))
    senha_lista = categorias + restantes
    random.shuffle(senha_lista)
    return ''.join(senha_lista)

# Rejeitar assinatura e apagar pedido
@login_required
@group_required('Desenvolvedores')
def rejeitar_assinatura(request, id):
    sub = get_object_or_404(SubscriptionRequest, id=id)
    sub.delete()
    messages.info(request, f"❌ Solicitação de {sub.nome} foi rejeitada e removida.")
    return redirect('tenant_management:lista_assinaturas')

@login_required
@group_required('Desenvolvedores')
def cancelar_assinatura(request, id):
    sub = get_object_or_404(SubscriptionRequest, id=id)

    # Somente se ainda estiver como 'aprovado' ou outro estado válido
    if sub.status == 'aprovado':
        sub.delete()
        messages.info(request, f"A assinatura de {sub.nome} foi cancelada e removida.")
    else:
        messages.warning(request, f"Assinatura de {sub.nome} não pode ser cancelada porque está em status: {sub.status}.")

    return redirect('tenant_management:lista_assinaturas')

from tenant_management.models import WebhookLog  # já deve estar importado
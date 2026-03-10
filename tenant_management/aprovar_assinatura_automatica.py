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


def aprovar_assinatura_automatica(email_cliente, payload=None, evento="webhook_auto"):
    sub = SubscriptionRequest.objects.filter(email=email_cliente, status='pendente').first()

    if not sub:
        WebhookLog.objects.create(
            evento=f"erro_{evento}",
            email_cliente=email_cliente,
            dados_recebidos=payload or {},
            resposta_enviada="Assinatura pendente não encontrada"
        )
        return False, "Assinatura não encontrada"

    schema_name = sub.email.split('@')[0].replace('.', '_').replace('-', '_')
    senha = gerar_senha_segura()
    User = get_user_model()

    if Client.objects.filter(schema_name=schema_name).exists():
        WebhookLog.objects.create(
            evento=f"erro_{evento}",
            email_cliente=email_cliente,
            dados_recebidos=payload or {},
            resposta_enviada=f"Schema '{schema_name}' já existe"
        )
        return False, "Schema já existe"

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


    # 🌐 Envia e-mail HTML com acesso
    context = {
        'nome': sub.nome,
        'email': sub.email,
        'senha': senha,
        'url': getattr(settings, "SITE_URL", None) or "https://app.example-saas.com",
        'now': timezone.now(),
    }

    assunto = "Seus dados de acesso ao sistema SaaS Demo"
    mensagem_html = render_to_string("emails/acesso_automatico.html", context)
    mensagem_texto = (
        f"Olá {sub.nome},\n\nSeu acesso ao sistema SaaS Demo foi liberado com sucesso.\n\n"
        f"🔑 Usuário: {sub.email}\n"
        f"🔒 Senha: {senha}\n"
        f"🌐 Acesse: {context['url']}\n"
    )

    email = EmailMultiAlternatives(
        subject=assunto,
        body=mensagem_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[sub.email],
    )
    email.attach_alternative(mensagem_html, "text/html")
    email.send(fail_silently=False)

    # Atualiza status da assinatura
    sub.status = 'aprovado'
    sub.save()

    WebhookLog.objects.create(
        evento=evento,
        email_cliente=sub.email,
        dados_recebidos=payload or {},
        resposta_enviada="Tenant criado automaticamente",
        usuario_criado=sub.email,
        schema_criado=schema_name
    )

    return True, "Tenant criado com sucesso"
# Python stdlib
import random
import string
import json
from datetime import timedelta

# Django core
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.management import call_command
from django.db import connection
from django.db.models import Count, F
from django.db.models.functions import TruncDay, TruncMonth, TruncYear, TruncMinute
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django_tenants.utils import schema_context, get_tenant_model

# App local
from login.views import group_required
from .forms import ClientForm
from .models import (
    Client,
    TenantDeleteRequest,
    SubscriptionRequest,
    Informativo,
    LeituraInformativo,
    WebhookLog,
    EspacoExtraRequest,
    ChatThread,
    ChatMessage,
    PaginaVisitaLog,
)

# Funções auxiliares organizadas em arquivos separados
from .estatisticas_visitas import estatisticas_visitas
from .aprovar_assinatura import (
    aprovar_assinatura,
    lista_assinaturas_pendentes,
    rejeitar_assinatura,
    cancelar_assinatura,
)
from .aprovar_assinatura_automatica import aprovar_assinatura_automatica
from .registrar_excluir_tenant import (
    register_tenant,
    solicitar_exclusao_tenant,
    aprovar_exclusao,
    rejeitar_exclusao_tenant,
    painel_aprovacoes,
)
from .aprovar_espaco_extra_hd_automaticamente import aprovar_espaco_extra_automaticamente
from .tenant_list_edit import tenant_list, edit_tenant, tenant_users, delete_user
from .informativos import gerenciar_informativos
from .aprovar_espaco_extra_hd import (
    lista_espaco_pendentes,
    aprovar_espaco_extra,
    rejeitar_espaco_extra,
)
from .aprovar_renovacao import (
    lista_renovacoes_pendentes,
    rejeitar_renovacao,
    aprovar_renovacao,
)
from .aprovar_renovacao_automatica import aprovar_renovacao_automatica
from .usuarios_hd import usuarios_hd
from .chat_admin_client import (
    chat_admin_painel,
    chat_admin_detalhe,
    enviar_mensagem_chat,
    marcar_lidas_chat,
)

from .mapa_ips import mapa_acessos_ips

# Painel de administração CAG
@login_required
@group_required('Desenvolvedores')
def painel_cag_adm(request):
    tenants = Client.objects.all()
    delete_requests = TenantDeleteRequest.objects.filter(approved=False)
    return render(request, 'tenant_management/painel_cag_adm.html', {
        'tenants': tenants,
        'delete_requests': delete_requests
    })


# Relatório de usuários e planos (Staff)
@login_required
@user_passes_test(lambda u: u.is_staff)
def usuarios_e_planos(request):
    ClientModel = get_tenant_model()
    clientes = ClientModel.objects.all()

    for cliente in clientes:
        cliente.usuario = cliente.users.first() if hasattr(cliente, 'users') else None
        if cliente.created_at and cliente.paid_until:
            cliente.vigencia_dias = (cliente.paid_until - cliente.created_at.date()).days
        else:
            cliente.vigencia_dias = '—'

    return render(request, 'tenant_management/usuarios_e_planos.html', {
        'clientes': clientes
    })




@login_required
@group_required('Desenvolvedores')
def historico_webhooks(request):
    logs = WebhookLog.objects.all().order_by('-recebido_em')
    return render(request, 'tenant_management/historico_webhooks.html', {
        'logs': logs
    })


@login_required
@group_required('Desenvolvedores')
def historico_webhooks_hd(request):
    logs = WebhookLog.objects.filter(evento__icontains='espaco').order_by('-recebido_em')[:100]
    return render(request, 'tenant_management/historico_webhooks_hd.html', {'logs': logs})



from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from login.decorators import group_required

@login_required
@group_required('Desenvolvedores')
def modelo_email_acesso(request):
    contexto = {
        "nome": "Fulano de Tal",
        "email": "fulano@email.com",
        "senha": "abc12",
        "url": request.build_absolute_uri("/"),  # <-- pega o domínio da própria requisição
        "now": timezone.now(),
    }
    return render(request, "tenant_management/email_preview.html", contexto)




@login_required
@group_required('Desenvolvedores')
def lista_trials(request):
    trials = Client.objects.filter(on_trial=True).order_by('-created_at')
    return render(request, 'tenant_management/lista_trials.html', {'trials': trials})


##################################################################################
##################################################################################
############################# Promoção Trials ####################################


import logging

logger = logging.getLogger(__name__)


@login_required
@group_required('Desenvolvedores')
def preview_email_depoimento(request):
    """Preview do email de oferta de depoimento (40% OFF)"""
    contexto = {
        'nome': 'João Silva',
        'email': 'joao@exemplo.com',
        'nome_empresa': 'Empresa Exemplo Ltda',
        'url': getattr(settings, "SITE_URL", None) or "https://app.example-saas.com",
        'now': now()
    }
    return render(request, 'emails/email_depoimento_desconto.html', contexto)

##################################################################################
##################################################################################
############################# Promoção Trials ####################################

import logging

logger = logging.getLogger(__name__)


@login_required
@group_required('Desenvolvedores')
def enviar_email_depoimento_trial(request):
    """
    Tela para selecionar usuários trial e enviar email oferecendo 40% de desconto
    em troca de depoimento sobre o uso da plataforma.
    """
    trials = Client.objects.filter(on_trial=True).order_by('-created_at')
    
    if request.method == 'POST':
        # Pegar IDs selecionados
        trial_ids = request.POST.getlist('trial_ids')
        
        if not trial_ids:
            messages.warning(request, 'Selecione pelo menos um usuário trial.')
            return redirect('tenant_management:enviar_email_depoimento_trial')
        
        enviados = 0
        erros = 0
        erros_detalhe = []
        
        for trial_id in trial_ids:
            try:
                client = Client.objects.get(id=trial_id, on_trial=True)
                
                # Pegar primeiro usuário do tenant
                usuario = client.users.first() if hasattr(client, 'users') else None
                
                if not usuario or not usuario.email:
                    erros += 1
                    erros_detalhe.append(f"{client.name}: sem usuário ou email")
                    logger.warning(f"Trial {client.schema_name} sem usuário ou email válido")
                    continue
                
                # Determinar o nome para usar no email (prioridade: nome completo > username > nome da empresa)
                nome_usuario = None
                if usuario.first_name and usuario.last_name:
                    nome_usuario = f"{usuario.first_name} {usuario.last_name}".strip()
                elif usuario.first_name:
                    nome_usuario = usuario.first_name.strip()
                elif usuario.get_full_name():
                    nome_usuario = usuario.get_full_name().strip()
                
                # Se ainda não tem nome, usa o nome da empresa (Client.name)
                if not nome_usuario or nome_usuario == '':
                    nome_usuario = client.name
                
                # Contexto para o template de email
                contexto = {
                    'nome': nome_usuario,
                    'email': usuario.email,
                    'nome_empresa': client.name,
                    'url': getattr(settings, "SITE_URL", None) or "https://app.example-saas.com",
                    'now': now()
                }
                
                # Assunto e remetente
                subject = '🎉 Oferta Exclusiva: 40% de desconto + ajude outros usuários!'
                from_email = settings.DEFAULT_FROM_EMAIL
                to_email = usuario.email
                
                # Corpo em texto simples (fallback)
        corpo_texto = f"""
Olá {contexto['nome']},

Seu email foi enviado porque você se inscreveu no período trial da nossa plataforma SaaS. 
Estamos extremamente felizes em tê-lo(a) conosco! 🚀

🎉 OFERTA EXCLUSIVA: 40% DE DESCONTO!

Dentro dos 127 usuários trial ativos hoje, estamos enviando este email para todos vocês para participarem 
de uma oferta exclusiva e limitada. Porém, apenas os 10 primeiros que confirmarem receberão o desconto!

📝 COMO FUNCIONA?

1. Acesse sua conta na plataforma
2. Entre no Chat de Suporte
3. Envie as seguintes informações:
   - Seu nome completo
   - CPF ou CNPJ
   - Plano escolhido (Mensal, Semestral ou Anual)
   - Método de pagamento (PIX, Cartão ou Boleto)
   - Seu depoimento sobre a experiência de uso da plataforma
   - Autorização para utilizarmos seu depoimento no site

💰 PLANOS DISPONÍVEIS COM 40% OFF:

Mensal (1 mês): R$ 189,99 → R$ 113,99
Semestral (6 meses): R$ 1.082,94 → R$ 649,76 (R$ 108,29/mês)
Anual (12 meses): R$ 2.051,89 → R$ 1.231,13 (R$ 102,59/mês) - MAIS VANTAJOSO

* Desconto único aplicado na primeira assinatura

Esta é uma oportunidade ÚNICA para você fazer parte da história da nossa plataforma e ainda economizar!

Acesse: https://app.example-saas.com/login/

Qualquer dúvida, estamos à disposição através do chat de suporte!

Equipe SaaS Demo
                """
                
                # Renderizar HTML (caminho correto do template)
                html_content = render_to_string(
                    'emails/email_depoimento_desconto.html',
                    contexto
                )
                
                # Criar e enviar email
                email_obj = EmailMultiAlternatives(
                    subject=subject,
                    body=corpo_texto,
                    from_email=from_email,
                    to=[to_email]
                )
                email_obj.attach_alternative(html_content, "text/html")
                email_obj.send()
                
                enviados += 1
                logger.info(f"Email de depoimento enviado para {to_email} ({client.schema_name}) - Nome: {nome_usuario}")
                
            except Client.DoesNotExist:
                erros += 1
                erros_detalhe.append(f"ID {trial_id}: não encontrado")
                logger.error(f"Client ID {trial_id} não encontrado")
                
            except Exception as e:
                erros += 1
                erros_detalhe.append(f"ID {trial_id}: {str(e)[:50]}")
                logger.exception(f"Erro ao enviar email para trial {trial_id}")
        
        # Mensagens de feedback
        if enviados > 0:
            messages.success(
                request, 
                f'✅ {enviados} email(s) enviado(s) com sucesso!'
            )
        
        if erros > 0:
            detalhes = ", ".join(erros_detalhe[:3])
            if len(erros_detalhe) > 3:
                detalhes += f" (e mais {len(erros_detalhe) - 3}...)"
            messages.warning(
                request,
                f'⚠️ {erros} email(s) não puderam ser enviados. Detalhes: {detalhes}'
            )
        
        return redirect('tenant_management:enviar_email_depoimento_trial')
    
    # GET - exibir formulário
    return render(request, 'tenant_management/enviar_email_depoimento.html', {
        'trials': trials
    })
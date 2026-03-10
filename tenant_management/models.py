from django.conf import settings
from django.db import models
from django.utils import timezone
from django_tenants.models import TenantMixin, DomainMixin
import os

class Client(TenantMixin):
    """
    Modelo que representa um tenant (cliente).
    O schema será criado automaticamente no PostgreSQL.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nome do cliente/empresa"
    )
    schema_name = models.CharField(
        max_length=63,
        unique=True,
        help_text="Nome do schema no PostgreSQL"
    )
    paid_until = models.DateField(
        default=timezone.now,
        help_text="Data até a qual o plano está ativo"
    )
    on_trial = models.BooleanField(
        default=True,
        help_text="Está em período de teste?"
    )

    # Campos de contato/informações adicionais
    cnpj = models.CharField(
        max_length=18,
        blank=True,
        null=True,
        help_text="CNPJ (somente números)"
    )
    endereco = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    telefone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        help_text="E-mail de contato do tenant (deixe em branco ao criar, preencha depois)"
    )

    # Controle de espaço em disco
    espaco_extra_mb = models.PositiveIntegerField(
        default=0,
        help_text="MB adicionais ao limite padrão"
    )

    # Tipo de plano
    PLANO_CHOICES = [
        ('trial', 'Trial (5 dias)'),
        ('mensal', 'Mensal'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]
    plano = models.CharField(
        max_length=20,
        choices=PLANO_CHOICES,
        default='trial',
        help_text="Plano contratado"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Data de criação do tenant"
    )

    auto_create_schema = True  # Cria automaticamente o schema

    class Meta:
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ['name']

    def __str__(self):
        return self.name

    def limite_total_hd(self):
        """
        Retorna o limite total de HD (limite padrão + espaço extra).
        """
        limite_padrao = getattr(settings, "HD_LIMIT_MB", 1024)
        return limite_padrao + self.espaco_extra_mb


class Domain(DomainMixin):
    """
    Domínios associados a um tenant.
    """
    tenant = models.ForeignKey(
        settings.TENANT_MODEL,
        related_name="domains",
        on_delete=models.CASCADE
    )
    domain = models.CharField(
        max_length=255,
        unique=True,
        help_text="Domínio (ex: cliente.minhaobra.com)"
    )
    is_primary = models.BooleanField(
        default=True,
        help_text="É o domínio principal deste tenant?"
    )

    class Meta:
        verbose_name = "Domínio"
        verbose_name_plural = "Domínios"

    def __str__(self):
        return self.domain


class TenantDeleteRequest(models.Model):
    """
    Solicitações de exclusão de tenant.
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='delete_requests'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delete_requests'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_deletions'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente'
    )

    class Meta:
        verbose_name = "Solicitação de Exclusão"
        verbose_name_plural = "Solicitações de Exclusão"
        ordering = ['-requested_at']

    def __str__(self):
        return f"DeleteRequest: {self.tenant.name} by {self.requested_by}"





from django.db import models

class SubscriptionRequest(models.Model):
    """
    Pedidos de assinatura via formulário público (antes de aprovar e criar tenant).
    Pode ser uma assinatura nova ou uma renovação de plano.
    """
    PLANO_CHOICES = [
        ('trial', 'Teste gratuito (5 dias)'),
        ('mensal', 'Mensal – R$ 55,99'),
        ('semestral', 'Semestral – R$ 209,99'),
        ('anual', 'Anual – R$ 388,99'),
    ]

    TIPO_CHOICES = [
        ('assinatura', 'Assinatura'),
        ('renovacao', 'Renovação'),
    ]

    tipo = models.CharField(
        max_length=12,
        choices=TIPO_CHOICES,
        default='assinatura',
        help_text="Tipo de solicitação: assinatura nova ou renovação."
    )

    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=False)
    documento = models.CharField(max_length=25, help_text="CPF ou CNPJ")
    endereco = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20)
    plano = models.CharField(max_length=20, choices=PLANO_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pendente', 'Pendente'), ('aprovado', 'Aprovado'), ('rejeitado', 'Rejeitado')],
        default='pendente'
    )

    class Meta:
        verbose_name = "Pedido de Assinatura"
        verbose_name_plural = "Pedidos de Assinatura"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome} ({self.plano}) - {self.get_tipo_display().capitalize()}"



# tenant_management/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class Informativo(models.Model):
    """
    Mensagens informativas agendadas para todos os tenants.
    """
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    data_programada = models.DateField()
    criado_em = models.DateTimeField(default=timezone.now)  # corrigido para evitar erro em migração

    class Meta:
        verbose_name = "Informativo"
        verbose_name_plural = "Informativos"
        ordering = ['-data_programada']

    def __str__(self):
        return f"{self.titulo} ({self.data_programada})"


class LeituraInformativo(models.Model):
    informativo = models.ForeignKey(Informativo, on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data_leitura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('informativo', 'usuario')





from django.db import models
from django.utils.timezone import now

class WebhookLog(models.Model):
    evento = models.CharField(max_length=100)
    email_cliente = models.EmailField(null=True, blank=True)
    usuario_criado = models.EmailField(null=True, blank=True)
    schema_criado = models.CharField(max_length=100, null=True, blank=True)
    dados_recebidos = models.JSONField()
    resposta_enviada = models.TextField(null=True, blank=True)  # <- CORRIGIDO AQUI
    recebido_em = models.DateTimeField(default=now)

    class Meta:
        verbose_name = "Log de Webhook"
        verbose_name_plural = "Logs de Webhooks"
        ordering = ['-recebido_em']

    def __str__(self):
        return f"{self.evento} – {self.email_cliente or 'sem email'}"


from django.db import models
from .models import Client

class EspacoExtraRequest(models.Model):
    """
    Registra solicitações de compra de espaço adicional por tenants existentes.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="espacos", null=True, blank=True)
    email = models.EmailField(help_text="E-mail do cliente que fez a solicitação")
    schema = models.CharField(max_length=100, help_text="Schema do tenant que solicitou")
    quantidade_gb = models.PositiveIntegerField(help_text="Quantidade de GB solicitados")

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Solicitação de Espaço Extra"
        verbose_name_plural = "Solicitações de Espaço Extra"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.schema} – {self.quantidade_gb} GB – {self.status}"



########################## CHAT ############################

from django.db import models
from django.conf import settings
from tenant_management.models import Client
from hdvirtual.uploads import caminho_hd_virtual


def caminho_screenshot_chat(instance, filename):
    """
    Gera caminho de upload no HD virtual do tenant:
    HDvirtual/<schema>/<obra_id>-<slug>/chat/<filename>
    """
    thread = instance.thread
    usuario = thread.user
    obra_id = None
    obra_nome = None

    try:
        # tentativa segura (não depende de FK direta)
        if hasattr(thread, 'obra_id') and hasattr(thread, 'obra'):
            obra_id = thread.obra_id
            obra_nome = thread.obra.nome
    except Exception:
        pass

    return caminho_hd_virtual(
        usuario,
        filename,
        categoria="chat",
        obra_id=obra_id,
        obra_nome=obra_nome
    )


class ChatThread(models.Model):
    """
    Uma thread de conversa entre o usuário e a equipe de suporte.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    obra_id = models.IntegerField(null=True, blank=True)  # ✅ mais estável para multitenant
    obra_nome = models.CharField(max_length=200, blank=True)  # opcional para exibição
    criado_em = models.DateTimeField(auto_now_add=True)

    def mensagens_nao_lidas(self):
        return self.mensagens.filter(from_support=False, lida=False).count()

    class Meta:
        verbose_name = "Conversa de Suporte"
        verbose_name_plural = "Conversas de Suporte"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.user.email} – {self.tenant.schema_name}"


class ChatMessage(models.Model):
    """
    Mensagem dentro de uma thread de suporte.
    """
    thread = models.ForeignKey(ChatThread, related_name='mensagens', on_delete=models.CASCADE)
    from_support = models.BooleanField(default=False, help_text="Mensagem enviada pela equipe?")
    texto = models.TextField(blank=True)
    screenshot = models.ImageField(upload_to=caminho_screenshot_chat, blank=True, null=True)
    enviada_em = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Mensagem de Suporte"
        verbose_name_plural = "Mensagens de Suporte"
        ordering = ['enviada_em']

    def __str__(self):
        lado = "Equipe" if self.from_support else "Usuário"
        return f"[{lado}] {self.texto[:30]}..."


########################## Visitas ############################

from django.db import models
from django.utils.timezone import now


class PaginaVisitaLog(models.Model):
    pagina = models.CharField(max_length=50, choices=[
        ('assinar', 'Assinar'),
        ('renovar', 'Renovar'),
        ('trial', 'Trial'),
    ])
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    visitado_em = models.DateTimeField(default=now)

    # Novos campos para rastrear campanhas
    utm_source = models.CharField("UTM Source", max_length=100, null=True, blank=True)
    utm_medium = models.CharField("UTM Medium", max_length=100, null=True, blank=True)
    utm_campaign = models.CharField("UTM Campaign", max_length=100, null=True, blank=True)
    loja_id = models.PositiveIntegerField("ID da Loja (utm)", null=True, blank=True)

    class Meta:
        verbose_name = "Log de Visita"
        verbose_name_plural = "Logs de Visitas"
        ordering = ['-visitado_em']

    def __str__(self):
        return f"{self.pagina} em {self.visitado_em.strftime('%Y-%m-%d %H:%M')}"


# Adicione este modelo no arquivo models.py

from django.db import models
from django.conf import settings
from django.utils.timezone import now

class EmailDepoimentoEnviado(models.Model):
    """
    Registra os emails de oferta de depoimento enviados para evitar duplicidade
    """
    client = models.ForeignKey(
        'Client',
        on_delete=models.CASCADE,
        related_name='emails_depoimento'
    )
    email_destinatario = models.EmailField()
    nome_destinatario = models.CharField(max_length=200)
    enviado_em = models.DateTimeField(default=now)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Email de Depoimento Enviado"
        verbose_name_plural = "Emails de Depoimento Enviados"
        ordering = ['-enviado_em']
        unique_together = ('client', 'email_destinatario')

    def __str__(self):
        return f"{self.email_destinatario} - {self.enviado_em.strftime('%d/%m/%Y %H:%M')}"




from django.db import models


class LojaDistribuidora(models.Model):
    nome = models.CharField("Nome da loja", max_length=200)
    cidade = models.CharField("Cidade", max_length=100, blank=True)
    estado = models.CharField("Estado", max_length=2, blank=True)  # Ex: 'SP'
    responsavel = models.CharField("Responsável / contato", max_length=200, blank=True)
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    observacoes = models.TextField("Observações", blank=True)
    ativa = models.BooleanField("Loja ativa", default=True)
    data_cadastro = models.DateTimeField("Cadastrada em", auto_now_add=True)

    class Meta:
        verbose_name = "Loja distribuidora"
        verbose_name_plural = "Lojas distribuidoras"
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"{self.nome} ({self.cidade})"


class OrigemCampanha(models.Model):
    nome = models.CharField("Nome interno da campanha", max_length=200)
    plataforma = models.CharField(
        "Plataforma",
        max_length=50,
        choices=[
            ('google', 'Google Ads'),
            ('instagram', 'Instagram'),
            ('facebook', 'Facebook'),
            ('tiktok', 'TikTok'),
            ('email', 'E-mail Marketing'),
            ('loja', 'Loja física com QR Code'),
            ('outra', 'Outra'),
        ]
    )
    loja = models.ForeignKey(
        LojaDistribuidora,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Se a campanha está associada a uma loja física"
    )
    utm_source = models.CharField("utm_source", max_length=100, help_text="Ex: google, instagram, loja")
    utm_medium = models.CharField("utm_medium", max_length=100, help_text="Ex: cpc, social, qrcode, promo")
    utm_campaign = models.CharField("utm_campaign", max_length=100, help_text="Ex: blackfriday, loja1", blank=True)
    descricao = models.TextField("Descrição ou observações", blank=True)
    link_destino = models.URLField("URL base de destino", default="https://app.example-saas.com/signup/trial/")
    data_inicio = models.DateField("Início da campanha", null=True, blank=True)
    data_fim = models.DateField("Fim da campanha", null=True, blank=True)
    ativa = models.BooleanField("Campanha ativa?", default=True)
    criada_em = models.DateTimeField("Criada em", auto_now_add=True)

    class Meta:
        verbose_name = "Campanha / origem de acesso"
        verbose_name_plural = "Campanhas / origens de acesso"
        ordering = ['-criada_em']

    def __str__(self):
        return f"{self.nome} [{self.plataforma}]"

    def gerar_url_com_utm(self):
        """
        Gera a URL final de destino com os parâmetros UTM.
        """
        base = self.link_destino or "https://app.example-saas.com/signup/trial/"

        params = []
        params.append(f"utm_source={self.utm_source}")
        params.append(f"utm_medium={self.utm_medium}")

        if self.utm_campaign:
            params.append(f"utm_campaign={self.utm_campaign}")

        if self.loja:
            params.append(f"loja_id={self.loja.id}")

        return f"{base}?{'&'.join(params)}"

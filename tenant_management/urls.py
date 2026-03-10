from django.urls import path
from . import views
from .views import (
    register_tenant,
    tenant_list,
    solicitar_exclusao_tenant,  # substitui delete_tenant
    edit_tenant,
    painel_cag_adm,
    painel_aprovacoes,
    aprovar_exclusao,
    rejeitar_exclusao_tenant,
    gerenciar_informativos, usuarios_e_planos, usuarios_hd, aprovar_renovacao, rejeitar_renovacao, mapa_acessos_ips, enviar_email_depoimento_trial, preview_email_depoimento
)                    

from tenant_management.gerar_qrcode import gerar_qrcode_view
from tenant_management.views_estatisticas import acessos_por_utm_view

app_name = 'tenant_management'

urlpatterns = [
    path('register/', register_tenant, name='register_tenant'),
    path('tenants/', tenant_list, name='tenant_list'),
    path('tenants/solicitar-exclusao/<int:tenant_id>/', solicitar_exclusao_tenant, name='solicitar_exclusao_tenant'),
    path('editar/<int:tenant_id>/', edit_tenant, name='edit_tenant'),
    path('painel/', painel_cag_adm, name='painel_cag_adm'),
    path('aprovacoes/', painel_aprovacoes, name='painel_aprovacoes'),
    path('aprovacoes/aprovar/<int:req_id>/', aprovar_exclusao, name='aprovar_exclusao'),
    path('aprovacoes/rejeitar/<int:solicitacao_id>/', rejeitar_exclusao_tenant, name='rejeitar_exclusao_tenant'),
    path('informativos/', views.gerenciar_informativos, name='gerenciar_informativos'),
    path('assinaturas/pendentes/', views.lista_assinaturas_pendentes, name='lista_assinaturas'),
    path('assinaturas/aprovar/<int:id>/', views.aprovar_assinatura, name='aprovar_assinatura'),
    path('assinaturas/rejeitar/<int:id>/', views.rejeitar_assinatura, name='rejeitar_assinatura'),
    path('usuarios-planos/', usuarios_e_planos, name='usuarios_e_planos'),
    path("assinaturas/cancelar/<int:id>/", views.cancelar_assinatura, name="cancelar_assinatura"),
    path('webhooks/historico/', views.historico_webhooks, name='historico_webhooks'),
    path('webhooks/modelo-email/', views.modelo_email_acesso, name='modelo_email_acesso'),
    path('historico_webhooks_hd/', views.historico_webhooks_hd, name='historico_webhooks_hd'),
    path('espaco/pendentes/', views.lista_espaco_pendentes, name='lista_espaco_pendentes'),
    path('espaco/aprovar/<int:id>/', views.aprovar_espaco_extra, name='aprovar_espaco_extra'),
    path('espaco/rejeitar/<int:id>/', views.rejeitar_espaco_extra, name='rejeitar_espaco_extra'),
    path("usuarios_hd/", usuarios_hd, name="usuarios_hd"),
    path("renovacoes/", views.lista_renovacoes_pendentes, name="lista_renovacoes"),
    path('renovacoes/aprovar/<int:id>/', aprovar_renovacao, name='aprovar_renovacao'),
    path('renovacoes/rejeitar/<int:id>/', rejeitar_renovacao, name='rejeitar_renovacao'),
    path("trials/", views.lista_trials, name="lista_trials"),
    path('chat/painel/', views.chat_admin_painel, name='chat_admin_painel'),
    path('chat/responder/<int:pk>/', views.chat_admin_detalhe, name='chat_admin_detalhe'),
    path('chat/enviar/', views.enviar_mensagem_chat, name='enviar_mensagem_chat'),
    path('chat/marcar-lidas/', views.marcar_lidas_chat, name='marcar_lidas_chat'),
    path("estatisticas/visitas/", views.estatisticas_visitas, name="estatisticas_visitas"),
    path("estatisticas/mapa-ips/", views.mapa_acessos_ips, name="mapa_acessos_ips"),
    path("trials/enviar-email-depoimento/", views.enviar_email_depoimento_trial, name="enviar_email_depoimento_trial"),
    path("trials/preview-email-depoimento/", views.preview_email_depoimento, name="preview_email_depoimento"),
    path('gerar-qrcode/', gerar_qrcode_view, name='gerar_qrcode'),
    path('acessos-por-utm/', acessos_por_utm_view, name='acessos_por_utm'),



]





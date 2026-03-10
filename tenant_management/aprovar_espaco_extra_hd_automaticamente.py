from tenant_management.models import EspacoExtraRequest, WebhookLog, Client


def aprovar_espaco_extra_automaticamente(
    schema_name=None,
    quantidade_gb=None,
    email_cliente=None,
    payload=None,
    evento="espaco_auto"
):
    client = None

    # 1️⃣ Tenta pelo schema_name
    if schema_name:
        try:
            client = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            pass

    # 2️⃣ Se não achou, tenta pelo e-mail
    if not client and email_cliente:
        try:
            client = Client.objects.get(email=email_cliente)
            schema_name = client.schema_name  # garante que o log mostre o schema certo
        except Client.DoesNotExist:
            pass

    # 3️⃣ Se ainda não achou → erro
    if not client:
        WebhookLog.objects.create(
            evento=f"erro_{evento}",
            email_cliente=email_cliente or "desconhecido",
            dados_recebidos=payload or {},
            resposta_enviada=f"Tenant com schema '{schema_name}' não encontrado",
            schema_criado=schema_name or "",
        )
        return False, "Tenant não encontrado"

    # 4️⃣ Valida quantidade
    try:
        quantidade_gb = int(quantidade_gb)
        if quantidade_gb <= 0:
            raise ValueError("Quantidade inválida")
    except Exception as e:
        WebhookLog.objects.create(
            evento=f"erro_{evento}_quantidade",
            email_cliente=client.email,
            dados_recebidos=payload or {},
            resposta_enviada=f"Erro na conversão de quantidade_gb: {e}",
            schema_criado=schema_name,
        )
        return False, "Quantidade inválida"

    # 5️⃣ Busca a solicitação pendente
    req = EspacoExtraRequest.objects.filter(
        client=client, status__in=["pendente", "aguardando_pagamento"]
    ).order_by("-criado_em").first()

    if not req:
        WebhookLog.objects.create(
            evento=f"erro_{evento}_sem_requisicao",
            email_cliente=client.email,
            dados_recebidos=payload or {},
            resposta_enviada="Solicitação de espaço extra não encontrada",
            schema_criado=schema_name,
        )
        return False, "Solicitação não encontrada"

    # 6️⃣ Aplica o espaço adicional
    client.espaco_extra_mb += quantidade_gb * 1024
    client.save()

    req.status = "aprovado"
    req.save()

    WebhookLog.objects.create(
        evento=evento,
        email_cliente=req.email,
        dados_recebidos=payload or {},
        resposta_enviada=f"{quantidade_gb} GB adicionados automaticamente ao schema {schema_name}",
        schema_criado=schema_name,
    )

    return True, "Espaço extra aprovado"

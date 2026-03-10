############################### ESPAÇO EXTRA ################################

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from tenant_management.models import EspacoExtraRequest, Client

@login_required
@user_passes_test(lambda u: u.groups.filter(name='Desenvolvedores').exists())
def lista_espaco_pendentes(request):
    pendentes = EspacoExtraRequest.objects.all().order_by('-criado_em')
    return render(request, 'tenant_management/espacos_pendentes.html', {'solicitacoes': pendentes})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='Desenvolvedores').exists())
def aprovar_espaco_extra(request, id):
    req = get_object_or_404(EspacoExtraRequest, id=id)
    if req.status in ['pendente', 'aguardando_pagamento']:
        client = req.client
        client.espaco_extra_mb += req.quantidade_gb * 1024
        client.save()
        req.status = 'aprovado'
        req.save()
        messages.success(request, f"Espaço extra aprovado para o tenant '{client.schema_name}'.")
    else:
        messages.warning(request, "Solicitação já processada.")
    return redirect('tenant_management:lista_espaco_pendentes')


@login_required
@user_passes_test(lambda u: u.groups.filter(name='Desenvolvedores').exists())
def rejeitar_espaco_extra(request, id):
    req = get_object_or_404(EspacoExtraRequest, id=id)
    if req.status in ['pendente', 'aguardando_pagamento']:
        req.status = 'rejeitado'
        req.save()
        messages.info(request, f"Solicitação de espaço extra de {req.email} rejeitada.")
    else:
        messages.warning(request, "Solicitação já processada.")
    return redirect('tenant_management:lista_espaco_pendentes')
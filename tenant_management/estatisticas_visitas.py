from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.timezone import now
from django.db.models import Count, F
from django.db.models.functions import TruncDay, TruncMonth, TruncYear, TruncMinute
from datetime import timedelta

from tenant_management.models import PaginaVisitaLog

@login_required
@user_passes_test(lambda u: u.groups.filter(name="Desenvolvedores").exists())
def estatisticas_visitas(request):
    logs = PaginaVisitaLog.objects.exclude(pagina__isnull=True).exclude(pagina='')

    # Agrupamento por visita "real" (IP + página por janela de 10 min)
    logs_deduplicados = (
        logs
        .annotate(
            janela_10m=TruncMinute(F("visitado_em"))  # será truncado depois
        )
        .values("pagina", "ip", "janela_10m")
        .distinct()
    )

    # Agora vamos recontar agrupando por página e data (truncando datas):
    def agrupar_por_periodo(field_func):
        return (
            logs
            .annotate(data=field_func("visitado_em"))
            .values("pagina", "ip", "data")  # cada IP conta no período
            .distinct()
            .values("pagina", "data")
            .annotate(total=Count("ip"))
            .order_by("data")
        )

    por_dia = list(agrupar_por_periodo(TruncDay))
    por_mes = list(agrupar_por_periodo(TruncMonth))
    por_ano = list(agrupar_por_periodo(TruncYear))

    # Contagem final por página (visitas únicas por IP nos últimos 10 min)
    deduplicadas_10min = (
        logs
        .annotate(janela=TruncMinute(F("visitado_em")))
        .values("pagina", "ip", "janela")
        .distinct()
    )
    contagem_por_pagina = {}
    for p in ['assinar', 'renovar', 'trial']:
        contagem_por_pagina[p] = sum(1 for l in deduplicadas_10min if l['pagina'] == p)

    context = {
        "logs": logs.order_by("-visitado_em")[:300],  # tabela completa
        "por_dia": por_dia,
        "por_mes": por_mes,
        "por_ano": por_ano,
        "paginas": ["assinar", "renovar", "trial"],
        "contagem_por_pagina": contagem_por_pagina,
    }
    return render(request, "tenant_management/estatisticas_visitas.html", context)
# Em views_estatisticas.py

from django.shortcuts import render
from tenant_management.models import OrigemCampanha, PaginaVisitaLog
from django.db.models import Count

def acessos_por_utm_view(request):
    campanhas = OrigemCampanha.objects.filter(ativa=True).order_by('-criada_em')

    # Busca os logs agrupados
    visitas = (
        PaginaVisitaLog.objects
        .filter(utm_source__isnull=False)  # Apenas logs com UTM
        .values('utm_source', 'utm_medium', 'utm_campaign')
        .annotate(total=Count('id'))
    )

    # 🔥 Cria dicionário normalizando None para string vazia
    acessos = {}
    for v in visitas:
        source = v['utm_source'] or ''
        medium = v['utm_medium'] or ''
        campaign = v['utm_campaign'] or ''
        
        # Chave precisa bater exatamente com o template
        chave = f"{source}|{medium}|{campaign}"
        acessos[chave] = v['total']
    
    # ✅ Debug para verificar
    print("📊 Acessos contabilizados:")
    for chave, total in acessos.items():
        print(f"   {chave} = {total}")

    return render(request, 'tenant_management/acessos_por_utm.html', {
        'campanhas': campanhas,
        'acessos': acessos
    })
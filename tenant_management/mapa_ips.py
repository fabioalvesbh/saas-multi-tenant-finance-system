import requests
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.timezone import now, localtime
from datetime import datetime, timedelta
from tenant_management.models import PaginaVisitaLog
from django.core.cache import cache
from django.db.models import Count, Max
import json

@login_required
@user_passes_test(lambda u: u.groups.filter(name="Desenvolvedores").exists())
def mapa_acessos_ips(request):
    """
    Exibe mapa interativo de acessos por IP com geolocalização otimizada.
    Usa ip-api.com (gratuito, 45 requests/minuto)
    """
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    periodo = request.GET.get('periodo', 'todo')
    
    logs = PaginaVisitaLog.objects.exclude(ip__isnull=True)
    hoje = localtime(now()).date()
    
    # Aplicar filtros
    if periodo == 'hoje':
        logs = logs.filter(visitado_em__date=hoje)
        periodo_texto = f"Hoje ({hoje.strftime('%d/%m/%Y')})"
    elif periodo == 'semana':
        logs = logs.filter(visitado_em__date__gte=hoje - timedelta(days=7))
        periodo_texto = "Últimos 7 dias"
    elif periodo == 'mes':
        logs = logs.filter(visitado_em__date__gte=hoje - timedelta(days=30))
        periodo_texto = "Últimos 30 dias"
    elif periodo == 'ano':
        logs = logs.filter(visitado_em__date__gte=hoje - timedelta(days=365))
        periodo_texto = "Último ano"
    elif periodo == 'custom' and data_inicio and data_fim:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            if dt_inicio > dt_fim:
                dt_inicio, dt_fim = dt_fim, dt_inicio
            logs = logs.filter(visitado_em__date__gte=dt_inicio, visitado_em__date__lte=dt_fim)
            periodo_texto = f"{dt_inicio.strftime('%d/%m/%Y')} até {dt_fim.strftime('%d/%m/%Y')}"
        except ValueError:
            periodo_texto = "Todo o período"
    else:
        periodo_texto = "Todo o período"
    
    total_acessos = logs.count()
    
    # Agrupar IPs
    ips_agrupados = logs.values('ip').annotate(
        total=Count('id'),
        ultimo_acesso=Max('visitado_em')
    ).order_by('-total')[:100]  # Reduzido para 100
    
    total_ips = ips_agrupados.count()
    
    # Geolocalizar usando ip-api.com (GRATUITO)
    ip_geolocalizados = []
    contador_sucesso = 0
    contador_falha = 0
    
    import time
    
    for idx, ip_info in enumerate(ips_agrupados):
        ip = ip_info['ip']
        cache_key = f'geoip_{ip}'
        geo_data = cache.get(cache_key)
        
        if not geo_data:
            try:
                # Respeitar rate limit: 45 requests/minuto = ~1.3 segundos entre requests
                if idx > 0:
                    time.sleep(1.4)
                
                # API GRATUITA SEM LIMITE DIÁRIO
                response = requests.get(
                    f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,isp",
                    timeout=3
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('status') == 'success':
                        geo_data = {
                            'city': data.get('city', 'Desconhecida'),
                            'region': data.get('regionName', ''),
                            'country': data.get('country', ''),
                            'lat': str(data.get('lat', '')),
                            'lon': str(data.get('lon', '')),
                            'org': data.get('isp', ''),
                        }
                        cache.set(cache_key, geo_data, 86400 * 30)  # Cache por 30 dias
                        print(f"✓ IP {ip} geolocalizado: {geo_data['city']}, {geo_data['region']}")
                    else:
                        print(f"✗ IP {ip} inválido ou privado")
                        contador_falha += 1
                        continue
                else:
                    print(f"✗ Erro API para IP {ip}: Status {response.status_code}")
                    contador_falha += 1
                    continue
                    
            except Exception as e:
                print(f"✗ Exceção ao geolocalizar {ip}: {e}")
                contador_falha += 1
                continue
        else:
            print(f"✓ IP {ip} obtido do cache")
        
        if geo_data and geo_data.get('lat') and geo_data.get('lon'):
            try:
                ultimo_log = logs.filter(ip=ip).order_by('-visitado_em').first()
                
                if ultimo_log:
                    data_hora_local = localtime(ultimo_log.visitado_em)
                    
                    item = {
                        'ip': ip,
                        'city': geo_data['city'],
                        'region': geo_data['region'],
                        'country': geo_data['country'],
                        'lat': float(geo_data['lat']),
                        'lon': float(geo_data['lon']),
                        'org': geo_data.get('org', ''),
                        'pagina': ultimo_log.get_pagina_display(),
                        'data': data_hora_local.strftime('%d/%m/%Y'),
                        'hora': data_hora_local.strftime('%H:%M:%S'),
                        'acessos': ip_info['total']
                    }
                    ip_geolocalizados.append(item)
                    contador_sucesso += 1
            except Exception as e:
                print(f"✗ Erro ao processar IP {ip}: {e}")
                contador_falha += 1
                continue
    
    print(f"\n=== RESUMO ===")
    print(f"Total de IPs processados: {len(ips_agrupados)}")
    print(f"IPs geolocalizados com sucesso: {contador_sucesso}")
    print(f"IPs com falha: {contador_falha}")
    print(f"IPs no array final: {len(ip_geolocalizados)}")
    
    context = {
        'total_ips': total_ips,
        'total_acessos': total_acessos,
        'periodo_selecionado': periodo,
        'periodo_texto': periodo_texto,
        'data_inicio': data_inicio or '',
        'data_fim': data_fim or '',
        'ip_geolocalizados': ip_geolocalizados,
        'ip_geolocalizados_json': json.dumps(ip_geolocalizados),
        'limit_applied': total_acessos > 100,
    }
    
    return render(request, 'tenant_management/mapa_acessos_ips.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from .models import LojaDistribuidora, OrigemCampanha
import qrcode
import io
import base64
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from django.conf import settings


def gerar_qrcode_view(request):
    lojas = LojaDistribuidora.objects.filter(ativa=True).order_by('nome')
    campanhas = OrigemCampanha.objects.filter(ativa=True).order_by('-criada_em')
    qr_code_base64 = None
    banner_base64 = None
    utm_url = None
    selected_loja = None
    selected_campanha = None

    # 🗑️ DELETAR LOJA
    if request.method == 'POST' and 'deletar_loja' in request.POST:
        loja_id = request.POST.get('loja_id')
        try:
            loja = LojaDistribuidora.objects.get(id=loja_id)
            nome_loja = loja.nome
            loja.delete()
            messages.success(request, f'Loja "{nome_loja}" deletada com sucesso!')
        except LojaDistribuidora.DoesNotExist:
            messages.error(request, 'Loja não encontrada.')
        return redirect(request.path)  # ✅ Redireciona para o mesmo caminho

    # 🗑️ DELETAR CAMPANHA
    if request.method == 'POST' and 'deletar_campanha' in request.POST:
        campanha_id = request.POST.get('campanha_id')
        try:
            campanha = OrigemCampanha.objects.get(id=campanha_id)
            nome_campanha = campanha.nome
            campanha.delete()
            messages.success(request, f'Campanha "{nome_campanha}" deletada com sucesso!')
        except OrigemCampanha.DoesNotExist:
            messages.error(request, 'Campanha não encontrada.')
        return redirect(request.path)  # ✅ Redireciona para o mesmo caminho

    # ➕ CADASTRAR CAMPANHA
    if request.method == 'POST' and 'cadastrar_campanha' in request.POST:
        loja_id = request.POST.get('loja_vinculada')
        loja_obj = None
        if loja_id:
            try:
                loja_obj = LojaDistribuidora.objects.get(id=loja_id)
            except LojaDistribuidora.DoesNotExist:
                pass

        try:
            nova_campanha = OrigemCampanha.objects.create(
                nome=request.POST.get('nome_campanha'),
                plataforma=request.POST.get('plataforma'),
                loja=loja_obj,
                utm_source=request.POST.get('utm_source'),
                utm_medium=request.POST.get('utm_medium'),
                utm_campaign=request.POST.get('utm_campaign', ''),
                descricao=request.POST.get('descricao_campanha', ''),
                link_destino=request.POST.get('link_destino', 'https://app.example-saas.com/signup/trial/'),
                data_inicio=date.today(),
                ativa=True
            )
            messages.success(request, f'Campanha "{nova_campanha.nome}" criada com sucesso!')
            return redirect(request.path)  # ✅ Redireciona para o mesmo caminho
        except Exception as e:
            messages.error(request, f'Erro ao criar campanha: {e}')
            return redirect(request.path)  # ✅ Redireciona para o mesmo caminho

    # ➕ CADASTRO DE NOVA LOJA
    if request.method == 'POST' and 'cadastrar_loja' in request.POST:
        try:
            nova = LojaDistribuidora.objects.create(
                nome=request.POST.get('nome'),
                cidade=request.POST.get('cidade'),
                estado=request.POST.get('estado'),
                responsavel=request.POST.get('responsavel'),
                telefone=request.POST.get('telefone'),
                email=request.POST.get('email'),
                observacoes=request.POST.get('observacoes'),
                ativa=True
            )
            messages.success(request, f'Loja "{nova.nome}" cadastrada com sucesso!')
            return redirect(request.path)  # ✅ Redireciona para o mesmo caminho
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar loja: {e}')
            return redirect(request.path)  # ✅ Redireciona para o mesmo caminho

    # 📊 GERAR MATERIAL PARA CAMPANHA
    if request.method == 'GET' and request.GET.get('campanha_id'):
        campanha_id = request.GET.get('campanha_id')
        try:
            selected_campanha = OrigemCampanha.objects.get(id=campanha_id)
            selected_loja = selected_campanha.loja
            utm_url = selected_campanha.gerar_url_com_utm()

            # Gera QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,
                border=2,
            )
            qr.add_data(utm_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="#0d6efd", back_color="white")

            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

            # Gera banner apenas se tiver loja vinculada
            if selected_loja:
                banner_base64 = gerar_banner_premium(qr_img, selected_loja)
                print(f"✅ Banner gerado para campanha '{selected_campanha.nome}' com loja '{selected_loja.nome}'")
            else:
                print(f"ℹ️  Campanha '{selected_campanha.nome}' sem loja vinculada - gerando apenas QR Code")

        except OrigemCampanha.DoesNotExist:
            messages.error(request, f"Campanha com ID {campanha_id} não encontrada")
        except Exception as e:
            messages.error(request, f"Erro ao gerar materiais: {e}")
            import traceback
            traceback.print_exc()

    # 🏪 GERAR MATERIAL PARA LOJA
    if request.method == 'GET' and request.GET.get('loja_id'):
        loja_id = request.GET.get('loja_id')
        try:
            selected_loja = LojaDistribuidora.objects.get(id=loja_id)

            # Busca ou cria campanha
            campanha = OrigemCampanha.objects.filter(
                loja=selected_loja,
                plataforma='loja'
            ).first()

            if not campanha:
                campanha = OrigemCampanha.objects.create(
                    nome=f"QRCode {selected_loja.nome}",
                    plataforma='loja',
                    loja=selected_loja,
                    utm_source='loja',
                    utm_medium='qrcode',
                    utm_campaign=f"loja_{selected_loja.id}",
                    descricao=f"QR físico da loja {selected_loja.nome}",
                    data_inicio=date.today(),
                    link_destino='https://app.example-saas.com/signup/trial/',
                    ativa=True
                )

            selected_campanha = campanha
            utm_url = campanha.gerar_url_com_utm()

            # Gera QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,
                border=2,
            )
            qr.add_data(utm_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="#0d6efd", back_color="white")

            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

            # Gera banner
            banner_base64 = gerar_banner_premium(qr_img, selected_loja)

            print(f"✅ Material promocional gerado com sucesso para loja '{selected_loja.nome}'!")

        except LojaDistribuidora.DoesNotExist:
            messages.error(request, f"Loja com ID {loja_id} não encontrada")
        except Exception as e:
            messages.error(request, f"Erro ao gerar materiais: {e}")
            import traceback
            traceback.print_exc()

    return render(request, 'tenant_management/gerar_qrcode.html', {
        'lojas': lojas,
        'campanhas': campanhas,
        'qr_code_base64': qr_code_base64,
        'banner_base64': banner_base64,
        'utm_url': utm_url,
        'selected_loja': selected_loja,
        'selected_campanha': selected_campanha,
    })


# [MANTENHA TODAS AS SUAS FUNÇÕES AUXILIARES AQUI]
def criar_gradiente(largura, altura, cor_inicio, cor_fim, direcao='vertical'):
    """Cria um gradiente suave entre duas cores"""
    base = Image.new('RGB', (largura, altura), cor_inicio)
    top = Image.new('RGB', (largura, altura), cor_fim)
    mask = Image.new('L', (largura, altura))
    mask_data = []
    
    if direcao == 'vertical':
        for y in range(altura):
            valor = int(255 * (y / altura))
            mask_data.extend([valor] * largura)
    else:
        for y in range(altura):
            for x in range(largura):
                valor = int(255 * (x / largura))
                mask_data.append(valor)
    
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def desenhar_icone_check(draw, x, y, tamanho, cor):
    """Desenha um ícone de check mark estilizado"""
    draw.ellipse([x, y, x + tamanho, y + tamanho], fill=cor, outline=cor)
    
    offset = tamanho // 4
    draw.line([x + offset, y + tamanho//2, x + tamanho//2.5, y + tamanho - offset], 
              fill=(255, 255, 255), width=tamanho//10)
    draw.line([x + tamanho//2.5, y + tamanho - offset, x + tamanho - offset, y + offset], 
              fill=(255, 255, 255), width=tamanho//10)



def gerar_banner_premium(qr_img, loja):
    """
    Gera banner promocional PROFISSIONAL A4 (2480x3508 px @ 300 DPI)
    Design moderno, limpo e com hierarquia visual clara
    """
    # Dimensões A4 em 300 DPI
    largura = 2480
    altura = 3508
    
    # Paleta de cores moderna e profissional
    azul_escuro = (13, 71, 161)
    azul_primario = (13, 110, 253)
    azul_claro = (66, 165, 245)
    laranja = (255, 152, 0)
    laranja_escuro = (230, 81, 0)
    verde = (76, 175, 80)
    branco = (255, 255, 255)
    cinza_escuro = (33, 33, 33)
    cinza_medio = (117, 117, 117)
    cinza_claro = (245, 245, 245)
    
    # Cria imagem base
    banner = Image.new('RGB', (largura, altura), branco)
    draw = ImageDraw.Draw(banner, 'RGBA')
    
    # Carrega fontes
    try:
        font_titulo_hero = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 180)
        font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 100)
        font_subtitulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 65)
        font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 85)
        font_feature = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 58)
        font_feature_desc = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
        font_qr_call = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 75)
        font_rodape = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except:
        font_titulo_hero = ImageFont.load_default()
        font_titulo = font_titulo_hero
        font_subtitulo = font_titulo_hero
        font_badge = font_titulo_hero
        font_feature = font_titulo_hero
        font_feature_desc = font_titulo_hero
        font_qr_call = font_titulo_hero
        font_rodape = font_titulo_hero
    
    # =========================
    # 1. HEADER COM FUNDO BRANCO
    # =========================
    header_height = 750
    # Fundo branco para o header (melhor contraste com logo)
    draw.rectangle([(0, 0), (largura, header_height)], fill=branco)
    
    # Logo da empresa
    try:
        logo_path = os.path.join(settings.STATIC_ROOT, 'relatorio/grf_graph_logo.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(settings.BASE_DIR, 'static/relatorio/grf_graph_logo.png')
        
        logo = Image.open(logo_path).convert('RGBA')
        
        # Redimensiona logo mantendo proporção (altura máxima 300px)
        logo_height = 300
        aspect_ratio = logo.width / logo.height
        logo_width = int(logo_height * aspect_ratio)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Centraliza logo
        logo_x = (largura - logo_width) // 2
        logo_y = 80
        
        # Cola logo diretamente com transparência (sem sombra/fundo)
        banner.paste(logo, (logo_x, logo_y), logo)
        
    except Exception as e:
        # Fallback para texto se logo não existir
        print(f"⚠️  Logo não encontrado, usando texto: {e}")
        titulo = "MINHA OBRA"
        bbox = draw.textbbox((0, 0), titulo, font=font_titulo_hero)
        titulo_largura = bbox[2] - bbox[0]
        titulo_x = (largura - titulo_largura) // 2
        draw.text((titulo_x + 4, 84), titulo, fill=(200, 200, 200), font=font_titulo_hero)
        draw.text((titulo_x, 80), titulo, fill=azul_escuro, font=font_titulo_hero)
    
    # Linha decorativa
    linha_y = 420
    margem_linha = 600
    draw.rectangle([(margem_linha, linha_y), (largura - margem_linha, linha_y + 6)], fill=laranja)
    
    # Subtítulo
    subtitulo = "Sistema Completo de Gestão de Obras"
    bbox = draw.textbbox((0, 0), subtitulo, font=font_subtitulo)
    sub_largura = bbox[2] - bbox[0]
    draw.text(((largura - sub_largura) // 2, 470), subtitulo, fill=azul_escuro, font=font_subtitulo)
    
    # Badge "14 DIAS GRÁTIS"
    badge_y = 590
    badge_largura = 850
    badge_altura = 140
    badge_x = (largura - badge_largura) // 2
    
    # Sombra
    draw.rounded_rectangle(
        [(badge_x + 6, badge_y + 6), (badge_x + badge_largura + 6, badge_y + badge_altura + 6)],
        radius=70, fill=(0, 0, 0, 80)
    )
    
    # Badge gradiente laranja
    badge_grad = criar_gradiente(badge_largura, badge_altura, laranja, laranja_escuro, 'horizontal')
    badge_img = Image.new('RGBA', (badge_largura, badge_altura), (255, 255, 255, 0))
    badge_draw = ImageDraw.Draw(badge_img)
    badge_draw.rounded_rectangle([(0, 0), (badge_largura, badge_altura)], radius=70, fill=branco)
    badge_final = Image.new('RGBA', (badge_largura, badge_altura))
    badge_final.paste(badge_grad, (0, 0))
    banner.paste(badge_final, (badge_x, badge_y), badge_final)
    
    # Texto do badge
    draw = ImageDraw.Draw(banner, 'RGBA')
    badge_texto = "14 DIAS GRÁTIS"
    bbox = draw.textbbox((0, 0), badge_texto, font=font_badge)
    badge_texto_largura = bbox[2] - bbox[0]
    draw.text((badge_x + (badge_largura - badge_texto_largura) // 2, badge_y + 25), 
              badge_texto, fill=branco, font=font_badge)
    
    # =========================
    # 2. SEÇÃO FUNCIONALIDADES COM IMAGEM
    # =========================
    y_features = 870
    margem_lateral = 180
    
    # Título seção
    secao_titulo = "O Que Você Ganha:"
    bbox = draw.textbbox((0, 0), secao_titulo, font=font_titulo)
    titulo_secao_largura = bbox[2] - bbox[0]
    draw.text(((largura - titulo_secao_largura) // 2, y_features), 
              secao_titulo, fill=azul_escuro, font=font_titulo)
    
    y_features += 180
    
    # Features compactas
    features = [
        ("✓ Diário de Obras com IA", "Preenchimento por voz"),
        ("✓ Múltiplas Obras", "Equipe ilimitada"),
        ("✓ Cronograma Gantt", "Curva S automática"),
        ("✓ Gestão de Estoque", "Controle por obra"),
        ("✓ Portal do Cliente", "Acesso em tempo real"),
        ("✓ Chat Integrado", "Comunicação simplificada"),
    ]
    
    espacamento_vertical = 140
    
    # Calcula altura total da seção de features
    features_altura = len(features) * espacamento_vertical
    
    # Carrega imagem de fundo/demonstração
    try:
        img_path = os.path.join(settings.STATIC_ROOT, 'imagens/login_fundo/login_fundo.png')
        if not os.path.exists(img_path):
            img_path = os.path.join(settings.BASE_DIR, 'static/imagens/login_fundo/login_fundo.png')
        
        demo_img = Image.open(img_path).convert('RGBA')
        
        # Redimensiona imagem para ocupar a mesma altura das features
        demo_height = features_altura
        aspect_ratio = demo_img.width / demo_img.height
        demo_width = int(demo_height * aspect_ratio)
        demo_img = demo_img.resize((demo_width, demo_height), Image.Resampling.LANCZOS)
        
        # Posiciona imagem à direita
        demo_x = largura - margem_lateral - demo_width
        demo_y = y_features
        
        # Adiciona sombra suave à imagem
        shadow = Image.new('RGBA', (demo_width + 20, demo_height + 20), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle([(10, 10), (demo_width + 10, demo_height + 10)], 
                                       radius=25, fill=(0, 0, 0, 60))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
        banner.paste(shadow, (demo_x - 10, demo_y - 10), shadow)
        
        # Container com borda arredondada para a imagem
        img_container = Image.new('RGBA', (demo_width, demo_height), (255, 255, 255, 0))
        img_draw = ImageDraw.Draw(img_container)
        img_draw.rounded_rectangle([(0, 0), (demo_width, demo_height)], radius=25, fill=branco)
        
        # Cria máscara arredondada
        mask = Image.new('L', (demo_width, demo_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (demo_width, demo_height)], radius=25, fill=255)
        
        # Redimensiona a imagem demo para caber no container
        demo_img_fit = demo_img.resize((demo_width, demo_height), Image.Resampling.LANCZOS)
        
        # Cola imagem com cantos arredondados
        banner.paste(demo_img_fit, (demo_x, demo_y), mask)
        
        # Borda ao redor da imagem
        draw = ImageDraw.Draw(banner, 'RGBA')
        draw.rounded_rectangle([(demo_x, demo_y), (demo_x + demo_width, demo_y + demo_height)],
                              radius=25, outline=azul_claro, width=6)
        
        # Ajusta largura disponível para o texto (metade da largura útil)
        largura_texto = demo_x - (margem_lateral * 2)
        
    except Exception as e:
        print(f"⚠️  Imagem de demonstração não encontrada: {e}")
        # Se não encontrar a imagem, usa largura total para texto
        largura_texto = largura - (margem_lateral * 2)
    
    # Desenha features do lado esquerdo
    for idx, (titulo_feat, desc_feat) in enumerate(features):
        y_pos = y_features + (idx * espacamento_vertical)
        
        # Título feature
        draw.text((margem_lateral + 100, y_pos), titulo_feat, fill=azul_escuro, font=font_feature)
        
        # Descrição
        draw.text((margem_lateral + 100, y_pos + 75), desc_feat, fill=cinza_medio, font=font_feature_desc)
    
    # =========================
    # 3. SEÇÃO QR CODE - DESTAQUE CENTRAL
    # =========================
    qr_section_y = y_features + (len(features) * espacamento_vertical) + 80
    
    # Background suave
    qr_bg_height = 1050
    qr_bg = criar_gradiente(largura, qr_bg_height, cinza_claro, branco, 'vertical')
    banner.paste(qr_bg, (0, qr_section_y))
    draw = ImageDraw.Draw(banner, 'RGBA')
    
    # Call to action
    cta_texto = "Comece Agora!"
    bbox = draw.textbbox((0, 0), cta_texto, font=font_qr_call)
    cta_largura = bbox[2] - bbox[0]
    draw.text(((largura - cta_largura) // 2, qr_section_y + 60), 
              cta_texto, fill=laranja, font=font_qr_call)
    
    # QR Code - MAIOR E BEM POSICIONADO
    qr_size = 700
    qr_resized = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    qr_x = (largura - qr_size) // 2
    qr_y = qr_section_y + 200
    
    # Sombra do QR
    shadow_offset = 12
    draw.rounded_rectangle(
        [(qr_x - 30 + shadow_offset, qr_y - 30 + shadow_offset), 
         (qr_x + qr_size + 30 + shadow_offset, qr_y + qr_size + 30 + shadow_offset)],
        radius=35, fill=(0, 0, 0, 60)
    )
    
    # Container branco do QR
    draw.rounded_rectangle(
        [(qr_x - 30, qr_y - 30), (qr_x + qr_size + 30, qr_y + qr_size + 30)],
        radius=35, fill=branco, outline=azul_primario, width=10
    )
    
    # Cola QR Code
    banner.paste(qr_resized, (qr_x, qr_y))
    
    # Instrução abaixo do QR
    qr_instrucao = "Aponte a câmera do celular"
    bbox = draw.textbbox((0, 0), qr_instrucao, font=font_subtitulo)
    instr_largura = bbox[2] - bbox[0]
    draw.text(((largura - instr_largura) // 2, qr_y + qr_size + 80), 
              qr_instrucao, fill=azul_escuro, font=font_subtitulo)
    
    # =========================
    # 4. RODAPÉ
    # =========================
    rodape_y = altura - 300
    
    # Linha divisória elegante
    draw.rectangle([(margem_lateral, rodape_y - 60), (largura - margem_lateral, rodape_y - 54)], 
                   fill=azul_claro)
    
    # Informações da loja
    loja_texto = f"Disponível em: {loja.nome}"
    if loja.cidade and loja.estado:
        loja_texto += f" • {loja.cidade}/{loja.estado}"
    bbox = draw.textbbox((0, 0), loja_texto, font=font_rodape)
    loja_largura = bbox[2] - bbox[0]
    draw.text(((largura - loja_largura) // 2, rodape_y), loja_texto, fill=cinza_escuro, font=font_rodape)
    
    # URL (domínio ilustrativo para o banner)
    url_texto = "app.example-saas.com"
    bbox = draw.textbbox((0, 0), url_texto, font=font_rodape)
    url_largura = bbox[2] - bbox[0]
    draw.text(((largura - url_largura) // 2, rodape_y + 75), url_texto, fill=azul_primario, font=font_rodape)
    
    # Benefícios finais
    beneficios = "Sem Cartão • Sem Compromisso • Cancelamento a Qualquer Momento"
    bbox = draw.textbbox((0, 0), beneficios, font=font_rodape)
    benef_largura = bbox[2] - bbox[0]
    draw.text(((largura - benef_largura) // 2, rodape_y + 150), beneficios, fill=cinza_medio, font=font_rodape)
    
    # Converte para base64
    buffer_banner = io.BytesIO()
    banner.save(buffer_banner, format='PNG', dpi=(300, 300), optimize=True)
    buffer_banner.seek(0)
    return base64.b64encode(buffer_banner.getvalue()).decode()


def criar_gradiente(largura, altura, cor_inicio, cor_fim, direcao='vertical'):
    """Cria um gradiente suave entre duas cores"""
    base = Image.new('RGB', (largura, altura), cor_inicio)
    top = Image.new('RGB', (largura, altura), cor_fim)
    mask = Image.new('L', (largura, altura))
    mask_data = []
    
    if direcao == 'vertical':
        for y in range(altura):
            valor = int(255 * (y / altura))
            mask_data.extend([valor] * largura)
    else:
        for y in range(altura):
            for x in range(largura):
                valor = int(255 * (x / largura))
                mask_data.append(valor)
    
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base
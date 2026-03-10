############################# CHAT ##################################

from .models import ChatThread, ChatMessage
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404

# Verifica se é equipe (grupo Desenvolvedores)
def is_suporte(user):
    return user.groups.filter(name='Desenvolvedores').exists()

# Lista geral de chats com contadores
@login_required
@user_passes_test(is_suporte)
def chat_admin_painel(request):
    threads = ChatThread.objects.select_related('user', 'tenant').order_by('-criado_em')
    return render(request, 'tenant_management/chat_admin_painel.html', {
        'threads': threads
    })

# Detalhe da conversa com resposta
@login_required
@user_passes_test(is_suporte)
def chat_admin_detalhe(request, pk):
    thread = get_object_or_404(ChatThread, pk=pk)
    mensagens = thread.mensagens.all()

    # Marca como lidas
    thread.mensagens.filter(from_support=False, lida=False).update(lida=True)

    if request.method == 'POST':
        texto = request.POST.get("texto", "").strip()
        screenshot = request.FILES.get("screenshot")
        ChatMessage.objects.create(
            thread=thread,
            from_support=True,
            texto=texto,
            screenshot=screenshot
        )
        return redirect('tenant_management:chat_admin_detalhe', pk=pk)

    return render(request, 'tenant_management/chat_admin_detalhe.html', {
        'thread': thread,
        'mensagens': mensagens
    })

from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import ChatThread, ChatMessage
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def enviar_mensagem_chat(request):
    thread_id = request.POST.get("thread_id")
    texto = request.POST.get("texto", "").strip()
    screenshot = request.FILES.get("screenshot")

    thread = get_object_or_404(ChatThread, id=thread_id, user=request.user)

    ChatMessage.objects.create(
        thread=thread,
        from_support=False,
        texto=texto,
        screenshot=screenshot
    )
    
    return JsonResponse({"status": "ok"})

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

@csrf_exempt
@require_POST
@login_required
def marcar_lidas_chat(request):
    try:
        dados = json.loads(request.body)
        thread_id = int(dados.get("thread_id"))
        thread = ChatThread.objects.get(id=thread_id, user=request.user)

        # Marca como lidas todas as mensagens recebidas
        thread.mensagens.filter(from_support=True, lida=False).update(lida=True)
        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"status": "erro", "detalhe": str(e)}, status=400)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView, UpdateView

from .forms import ChamadoForm
from .models import Chamado


def chamados_queryset_for_user(user):
    """Chamados visíveis: quem criou ou para quem foi direcionado."""
    return Chamado.objects.filter(
        Q(solicitante=user) | Q(responsavel=user)
    ).select_related("solicitante", "responsavel")


class ChamadosHomeView(LoginRequiredMixin, ListView):
    model = Chamado
    template_name = "chamados/home.html"
    context_object_name = "chamados"

    def get_queryset(self):
        return chamados_queryset_for_user(self.request.user)


class ChamadoCreateView(LoginRequiredMixin, CreateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = "chamados/chamado_form.html"
    success_url = reverse_lazy("chamados:home")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        return super().form_valid(form)


class ChamadoDetailView(LoginRequiredMixin, DetailView):
    model = Chamado
    template_name = "chamados/chamado_detail.html"
    context_object_name = "chamado"

    def get_queryset(self):
        return chamados_queryset_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chamado = context["chamado"]
        other = None
        if chamado.responsavel and self.request.user == chamado.solicitante:
            other = chamado.responsavel
        elif self.request.user == chamado.responsavel:
            other = chamado.solicitante
        context["other_user_for_chat"] = other
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        acao = request.POST.get("acao")
        if acao == "concluir":
            self.object.status = Chamado.Status.RESOLVIDO
            self.object.save(update_fields=["status"])
        elif acao == "cancelar":
            self.object.status = Chamado.Status.CANCELADO
            self.object.save(update_fields=["status"])
        return redirect("chamados:home")


class ChamadoUpdateView(LoginRequiredMixin, UpdateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = "chamados/chamado_form.html"

    def get_queryset(self):
        # só quem vê o chamado pode editar
        return chamados_queryset_for_user(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("chamados:detalhe", kwargs={"pk": self.object.pk})

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "chamados/dashboard.html"


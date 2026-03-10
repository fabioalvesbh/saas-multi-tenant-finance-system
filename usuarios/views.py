from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import UserCreateForm, UserEditForm
from .models import UserProfile

User = get_user_model()


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return bool(self.request.user and self.request.user.is_superuser)


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = UserProfile
    template_name = "usuarios/user_list.html"
    context_object_name = "perfis"
    ordering = ["company", "department", "display_name", "user__username"]


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    form_class = UserCreateForm
    template_name = "usuarios/user_form.html"
    success_url = reverse_lazy("usuarios:user_list")


class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = "usuarios/user_edit.html"
    success_url = reverse_lazy("usuarios:user_list")
    context_object_name = "user_edit"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        profile = getattr(self.object, "profile", None)
        if profile:
            kwargs["profile"] = profile
        return kwargs


class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Confirma e exclui o usuário (GET = página de confirmação, POST = exclui)."""

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs["pk"])
        if user.username == "administrator" and user.is_superuser:
            return redirect("usuarios:user_list")
        from django.shortcuts import render
        return render(
            request,
            "usuarios/user_confirm_delete.html",
            {"user_edit": user},
        )

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs["pk"])
        if user.username == "administrator" and user.is_superuser:
            return redirect("usuarios:user_list")
        user.delete()
        return redirect("usuarios:user_list")


class UpdatePasswordView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        pwd1 = (request.POST.get("new_password1") or "").strip()
        pwd2 = (request.POST.get("new_password2") or "").strip()
        if pwd1 and pwd1 == pwd2:
            user = request.user
            user.set_password(pwd1)
            user.save()
            update_session_auth_hash(request, user)
        return redirect("chat:home")


class UpdateAvatarView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        from django.shortcuts import render

        return render(request, "usuarios/profile_avatar_form.html")

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        avatar = request.FILES.get("avatar")
        if avatar:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.avatar = avatar
            profile.save()
        return redirect("chat:home")


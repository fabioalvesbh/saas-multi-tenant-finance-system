from django import forms
from django.contrib.auth.models import User

from .models import UserProfile


class UserEditForm(forms.ModelForm):
    """Formulário para editar usuário e perfil (nome, departamento, função, senha opcional)."""
    full_name = forms.CharField(label="Nome completo", max_length=150, required=False)
    company = forms.CharField(
        label="Empresa",
        max_length=100,
        required=False,
        help_text="Ex.: Kuttner do Brasil, Kuttner Automation",
    )
    department = forms.CharField(label="Departamento", max_length=100, required=False)
    display_name = forms.CharField(label="Nome exibido", max_length=150, required=False)
    role = forms.ChoiceField(
        label="Função",
        choices=UserProfile.Role.choices,
        required=False,
    )
    password = forms.CharField(
        label="Nova senha (deixe em branco para não alterar)",
        widget=forms.PasswordInput,
        strip=False,
        required=False,
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "Usuário",
            "email": "E-mail",
        }

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)
        if self.profile:
            self.fields["full_name"].initial = self.instance.first_name
            self.fields["company"].initial = self.profile.company
            self.fields["department"].initial = self.profile.department
            self.fields["display_name"].initial = self.profile.display_name
            self.fields["role"].initial = self.profile.role

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        if self.cleaned_data.get("full_name") is not None:
            user.first_name = self.cleaned_data["full_name"] or ""
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            profile = self.profile or getattr(user, "profile", None)
            if not profile:
                profile = UserProfile.objects.create(
                    user=user,
                    company=self.cleaned_data.get("company") or "",
                    department=self.cleaned_data.get("department") or "",
                    display_name=self.cleaned_data.get("display_name") or "",
                    role=self.cleaned_data.get("role") or UserProfile.Role.OUTRO,
                )
            else:
                profile.company = self.cleaned_data.get("company") or ""
                profile.department = self.cleaned_data.get("department") or ""
                profile.display_name = self.cleaned_data.get("display_name") or ""
                profile.role = self.cleaned_data.get("role") or UserProfile.Role.OUTRO
                profile.save()
        return user


class UserCreateForm(forms.ModelForm):
    full_name = forms.CharField(label="Nome completo", max_length=150)
    company = forms.CharField(
        label="Empresa",
        max_length=100,
        help_text="Ex.: Kuttner do Brasil, Kuttner Automation",
    )
    department = forms.CharField(label="Departamento", max_length=100)
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        strip=False,
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "Usuário",
            "email": "E-mail",
        }

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["full_name"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                display_name=self.cleaned_data["full_name"],
                company=self.cleaned_data["company"],
                department=self.cleaned_data["department"],
            )
        return user


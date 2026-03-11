from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria (ou atualiza) um usuário de demonstração com credenciais simples."

    def handle(self, *args, **options):
        User = get_user_model()
        username = "username"
        password = "username"

        user, created = User.objects.get_or_create(username=username, defaults={"is_staff": True})
        user.set_password(password)
        user.is_active = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Usuário de demo criado: {username}/{password}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Usuário de demo atualizado: {username}/{password}"))


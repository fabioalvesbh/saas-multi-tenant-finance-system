from django.utils import timezone

from .models import UserProfile


class LastSeenMiddleware:
    """
    Atualiza o campo last_seen do usuário autenticado a cada requisição.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={"display_name": user.get_username()},
            )
            UserProfile.objects.filter(pk=profile.pk).update(last_seen=timezone.now())

        return response


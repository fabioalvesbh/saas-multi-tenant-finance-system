from django.urls import path
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="login", permanent=False), name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path(
        "manifest.webmanifest",
        TemplateView.as_view(
            template_name="core/manifest.webmanifest",
            content_type="application/manifest+json",
        ),
        name="manifest",
    ),
    path(
        "service-worker.js",
        TemplateView.as_view(
            template_name="core/service-worker.js",
            content_type="application/javascript",
        ),
        name="service_worker",
    ),
]


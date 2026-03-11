from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from tenant_management.api_views import TenantAutoCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("chat/", include("chat.urls", namespace="chat")),
    path("chamados/", include("chamados.urls", namespace="chamados")),
    path("usuarios/", include("usuarios.urls", namespace="usuarios")),

    # API pública (JWT + multi-tenant + documentação)
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/tenants/", TenantAutoCreateView.as_view(), name="tenant_auto_create"),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

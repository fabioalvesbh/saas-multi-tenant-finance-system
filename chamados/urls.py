from django.urls import path

from . import views

app_name = "chamados"

urlpatterns = [
    path("", views.ChamadosHomeView.as_view(), name="home"),
    path("novo/", views.ChamadoCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.ChamadoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ChamadoUpdateView.as_view(), name="editar"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]


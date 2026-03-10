from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.UserListView.as_view(), name="user_list"),
    path("novo/", views.UserCreateView.as_view(), name="user_create"),
    path("<int:pk>/editar/", views.UserUpdateView.as_view(), name="user_edit"),
    path("<int:pk>/excluir/", views.UserDeleteView.as_view(), name="user_delete"),
    path("atualizar-senha/", views.UpdatePasswordView.as_view(), name="update_password"),
    path("atualizar-avatar/", views.UpdateAvatarView.as_view(), name="update_avatar"),
]


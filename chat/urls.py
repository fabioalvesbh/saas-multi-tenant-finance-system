from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.ChatHomeView.as_view(), name="home"),
    path(
        "reunioes/agendar/",
        views.ScheduleMeetingView.as_view(),
        name="schedule_meeting",
    ),
    path(
        "reunioes/<int:pk>/cancelar/",
        views.CancelMeetingView.as_view(),
        name="cancel_meeting",
    ),
    path(
        "reunioes/<int:pk>/editar/",
        views.EditMeetingView.as_view(),
        name="edit_meeting",
    ),
    path("reunir-agora/", views.MeetNowView.as_view(), name="meet_now"),
    path("status/online-users/", views.OnlineUsersView.as_view(), name="online_users"),
    path(
        "conversation/<int:conversation_id>/messages/",
        views.ConversationMessagesView.as_view(),
        name="conversation_messages",
    ),
    path("notifications/", views.NotificationsView.as_view(), name="notifications"),
    path("with/<int:user_id>/", views.ChatWithUserView.as_view(), name="with_user"),
]


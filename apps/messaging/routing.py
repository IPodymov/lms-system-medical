from django.urls import path

from .consumers import CourseChatConsumer, DirectChatConsumer

websocket_urlpatterns = [
    path("ws/messages/direct/<uuid:user_id>/", DirectChatConsumer.as_asgi()),
    path("ws/messages/course/<uuid:run_id>/", CourseChatConsumer.as_asgi()),
]

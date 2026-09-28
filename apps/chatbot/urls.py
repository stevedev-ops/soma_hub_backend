from django.urls import path
from apps.chatbot.views import (
    chatbot_public_view,
    chatbot_authenticated_view,
    admin_chat_logs_view,
    admin_update_conversation_view,
    admin_chat_analytics_view,
    whatsapp_webhook_view
)

urlpatterns = [
    path('public/', chatbot_public_view, name='chatbot_public'),
    path('authenticated/', chatbot_authenticated_view, name='chatbot_authenticated'),
    path('admin/logs/', admin_chat_logs_view, name='admin_chat_logs'),
    path('admin/logs/<int:pk>/', admin_update_conversation_view, name='admin_update_conversation'),
    path('admin/analytics/', admin_chat_analytics_view, name='admin_chat_analytics'),
    path('whatsapp/webhook/', whatsapp_webhook_view, name='whatsapp_webhook'),
]

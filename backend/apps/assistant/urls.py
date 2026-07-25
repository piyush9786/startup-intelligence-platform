from django.urls import path

from .copilot_context_views import CopilotContextView
from .views import (
    ChatbotCurrentView,
    ChatbotMessageCreateView,
    ConciergeCurrentView,
    ConciergeDraftUpdateView,
    ConciergeTransitionView,
)

urlpatterns = [
    path("concierge/current/", ConciergeCurrentView.as_view(), name="assistant-concierge-current"),
    path("concierge/current/updates/", ConciergeDraftUpdateView.as_view(), name="assistant-concierge-draft-update"),
    path("concierge/current/transitions/", ConciergeTransitionView.as_view(), name="assistant-concierge-transition"),
    path("chatbot/current/", ChatbotCurrentView.as_view(), name="assistant-chatbot-current"),
    path("chatbot/current/messages/", ChatbotMessageCreateView.as_view(), name="assistant-chatbot-message-create"),
    path("chatbot/current/copilot-context/", CopilotContextView.as_view(), name="assistant-chatbot-copilot-context"),
]

from django.urls import path

from apps.comments.views import CommentDetailView, CommentReactionToggleView, CommentReplyView

app_name = "comments"

urlpatterns = [
    path("<uuid:pk>/", CommentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/reply/", CommentReplyView.as_view(), name="reply"),
    path("<uuid:pk>/reactions/", CommentReactionToggleView.as_view(), name="reactions"),
]

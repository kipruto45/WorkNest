from django.urls import path

from apps.tasks.views import (
    MyTasksView,
    OverdueTasksView,
    SavedTaskViewListCreateView,
    TaskArchiveView,
    TaskAssignView,
    TaskBoardView,
    TaskDetailView,
    TaskListCreateView,
    TaskTemplateInstantiateView,
    TaskTemplateListCreateView,
    TaskStatusView,
)

app_name = "tasks"

urlpatterns = [
    path("", TaskListCreateView.as_view(), name="list-create"),
    path("templates/", TaskTemplateListCreateView.as_view(), name="templates"),
    path("templates/<uuid:pk>/create-task/", TaskTemplateInstantiateView.as_view(), name="template-create-task"),
    path("views/saved/", SavedTaskViewListCreateView.as_view(), name="saved-views"),
    path("<uuid:pk>/", TaskDetailView.as_view(), name="detail"),
    path("<uuid:pk>/status/", TaskStatusView.as_view(), name="status"),
    path("<uuid:pk>/assign/", TaskAssignView.as_view(), name="assign"),
    path("<uuid:pk>/archive/", TaskArchiveView.as_view(), name="archive"),
    path("my-tasks/", MyTasksView.as_view(), name="my-tasks"),
    path("board/", TaskBoardView.as_view(), name="board"),
    path("overdue/", OverdueTasksView.as_view(), name="overdue"),
]

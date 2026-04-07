from django.urls import path

from apps.tasks.views import (
    FavoriteTaskListView,
    FavoriteTaskToggleView,
    MyTasksView,
    OverdueTasksView,
    RecentTaskListView,
    SavedTaskViewListCreateView,
    TaskArchiveView,
    TaskAssignView,
    TaskBoardView,
    TaskBulkActionView,
    TaskChecklistDetailView,
    TaskChecklistListCreateView,
    TaskDetailView,
    TaskLabelListCreateView,
    TaskListCreateView,
    TaskTimelineView,
    TaskTemplateInstantiateView,
    TaskTemplateListCreateView,
    TaskStatusView,
    TaskWatcherView,
)

app_name = "tasks"

urlpatterns = [
    path("", TaskListCreateView.as_view(), name="list-create"),
    path("labels/", TaskLabelListCreateView.as_view(), name="labels"),
    path("templates/", TaskTemplateListCreateView.as_view(), name="templates"),
    path("templates/<uuid:pk>/create-task/", TaskTemplateInstantiateView.as_view(), name="template-create-task"),
    path("views/saved/", SavedTaskViewListCreateView.as_view(), name="saved-views"),
    path("bulk/", TaskBulkActionView.as_view(), name="bulk-action"),
    path("favorites/", FavoriteTaskListView.as_view(), name="favorites"),
    path("recent/", RecentTaskListView.as_view(), name="recent"),
    path("checklist/<uuid:checklist_id>/", TaskChecklistDetailView.as_view(), name="checklist-detail"),
    path("<uuid:pk>/", TaskDetailView.as_view(), name="detail"),
    path("<uuid:pk>/status/", TaskStatusView.as_view(), name="status"),
    path("<uuid:pk>/assign/", TaskAssignView.as_view(), name="assign"),
    path("<uuid:pk>/archive/", TaskArchiveView.as_view(), name="archive"),
    path("<uuid:pk>/checklist/", TaskChecklistListCreateView.as_view(), name="checklist"),
    path("<uuid:pk>/watchers/", TaskWatcherView.as_view(), name="watchers"),
    path("<uuid:pk>/timeline/", TaskTimelineView.as_view(), name="timeline"),
    path("<uuid:pk>/favorite/", FavoriteTaskToggleView.as_view(), name="favorite-toggle"),
    path("my-tasks/", MyTasksView.as_view(), name="my-tasks"),
    path("board/", TaskBoardView.as_view(), name="board"),
    path("overdue/", OverdueTasksView.as_view(), name="overdue"),
]

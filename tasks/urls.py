from django.urls import path
from . import views


urlpatterns = [
    path('category/', views.CategoryAPIView.as_view(), name="category"),
    path('group/', views.GroupAPIView.as_view(), name="group"),
    path('reason-choice/', views.ReasonChoiceAPIView.as_view(), name="reason-choices"),
    path('user-task/<int:pk>/', views.TaskDetailAPIView.as_view(), name="task"),
    path('user-task/list/', views.UserTaskListAPIView.as_view(), name="user-task-list"),
    path('admin/user-task/list/', views.UserTaskAdminAPIView.as_view(), name="user-task-admin"),
    path('admin/user-task/<int:pk>/', views.UserTaskAPIView.as_view(), name="user-task"),
    path('admin/user-task/', views.UserTaskAPIView.as_view(), name="user-task"),
    path('admin/routine/list/', views.RoutinesAdminAPIView.as_view(), name="routines-admin"),
    path('admin/routine/<int:pk>/', views.RoutineAPIView.as_view(), name="routines"),
    path('admin/routine/', views.RoutineAPIView.as_view(), name="routines"),
    path('periodic-relation/<int:pk>/', views.PeriodicRelationAPIView.as_view(), name="periodic-relation"),
    path('response/<int:pk>/', views.ResponseAPIView.as_view(), name="response"),
    path('comment/<int:pk>/', views.CommentAPIView.as_view(), name="comment"),
    path('comment/seen/<int:pk>/', views.SeenCommentAPIView.as_view(), name="seen-comment"),
    path('user-ranking/', views.TaskUserRankingAPIView.as_view(), name="task-user-ranking"),
    path('pictures/', views.PicturesAPIView.as_view(), name="pictures"),
    path('pictures/category/', views.PicturesCategoriesAPIView.as_view(), name="pictures-categories"),
]

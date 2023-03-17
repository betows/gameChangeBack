from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, TaskViewSet, TaskProgressViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'taskprogress', TaskProgressViewSet, basename='taskprogress')

urlpatterns = router.urls

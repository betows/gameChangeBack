from rest_framework import viewsets
from .models import Employee, Task, TaskProgress
from .serializers import EmployeeSerializer, TaskSerializer, TaskProgressSerializer
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class TaskProgressViewSet(viewsets.ModelViewSet):
    queryset = TaskProgress.objects.all()
    serializer_class = TaskProgressSerializer

@api_view(['PUT'])
def complete_task(request, pk):
    try:
        task_progress = TaskProgress.objects.get(task_id=pk)
    except TaskProgress.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    task_progress.progress = 100
    task_progress.save()

    return JsonResponse({"message": "Task marked as complete"})

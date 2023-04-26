from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from tasks.models import Task, Employee
from tasks.serializers import TaskSerializer

class CustomLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        username = request.data.get('username')

        user = authenticate(request, email=email, password=password, username=username)
        
        if user is not None:
            refresh = RefreshToken.for_user(user)
            try:
                employee = Employee.objects.get(user=user)
                tasks = Task.objects.filter(assigned_to=employee)
                task_serializer = TaskSerializer(tasks, many=True)
                serialized_tasks = task_serializer.data
            except Employee.DoesNotExist:
                serialized_tasks = []

            # You can add other fields as needed, e.g., team, accomplishments, etc.
            return Response({
            'user': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'tasks': serialized_tasks,
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)

        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

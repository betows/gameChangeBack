from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey(Employee, on_delete=models.CASCADE)


class TaskProgress(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE)
    progress = models.PositiveIntegerField(default=0)

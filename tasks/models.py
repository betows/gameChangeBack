from django.db import models
from django.core import validators
RECURRENCE_CHOICES = [("d", "day"), ("w", "week"), ("m", "month")]
SUBMISSION_TYPES = [("f", "file"), ("t", "text"), ("s", "simple")]
SUPPORTING_TYPES = [("f", "file"), ("l", "link"), ("v", "video"), ("i", "internal")]


class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    motivation = models.CharField(max_length=500, blank=True)
    recurrence = models.CharField(choices=RECURRENCE_CHOICES, null=True, max_length=1)
    recurrence_index = models.IntegerField(null=True, blank=True)
    advance_days = models.IntegerField(null=True)
    store = models.ForeignKey("stores.Store", on_delete=models.CASCADE)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True)
    group = models.ForeignKey("Group", on_delete=models.CASCADE, null=True)
    submission = models.ForeignKey("Submission", on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True)
    is_editable = models.BooleanField(default=True)
    suggested_time = models.TimeField(blank=True, null=True)


class Group(models.Model):
    title = models.CharField(max_length=100)
    order = models.IntegerField()
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE)


class Category(models.Model):
    title = models.CharField(max_length=100)
    brand = models.ForeignKey("brands.Brand", on_delete=models.CASCADE)


class Submission(models.Model):
    type = models.CharField(choices=SUBMISSION_TYPES, max_length=1)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    min_objects = models.IntegerField(null=True, blank=True)
    max_objects = models.IntegerField(null=True, blank=True)


class UserTask(models.Model):
    task = models.ForeignKey("Task", on_delete=models.CASCADE)
    user = models.ForeignKey("authentication.User", on_delete=models.CASCADE)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_concluded = models.BooleanField(null=True)
    concluded_at = models.DateTimeField(null=True)
    obs = models.TextField(blank=True)
    title_extension = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    concluded_by_user = models.BooleanField(default=True)
    concluded_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, related_name="user_task_concluded_by")
    ifood_relation = models.ForeignKey('ifood.Reviews', null=True, on_delete=models.SET_NULL)
    reason = models.ForeignKey('Reason', null=True, on_delete=models.CASCADE)


def get_upload(instance, filename):
    return "images/tasks/response/" + str(instance.user_task.id) + '/' + filename


class Response(models.Model):
    user_task = models.ForeignKey("UserTask", on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_upload, null=True)
    text = models.CharField(max_length=500, null=True)
    is_image = models.BooleanField(null=True)


class PeriodicRelation(models.Model):
    task = models.ForeignKey("Task", on_delete=models.CASCADE)
    user = models.ForeignKey("authentication.User", on_delete=models.CASCADE)
    obs = models.CharField(max_length=500, blank=True)
    priority = models.IntegerField(default=1, validators=[validators.MinValueValidator(1), validators.MaxValueValidator(5)])


class Comment(models.Model):
    user_task = models.ForeignKey("UserTask", on_delete=models.CASCADE)
    user = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True)
    content = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)


class SeenComment(models.Model):
    comment = models.ForeignKey("Comment", on_delete=models.CASCADE)
    user = models.ForeignKey("authentication.User", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Reason(models.Model):
    reason_choice = models.ForeignKey("ReasonChoice", on_delete=models.CASCADE)
    description = models.CharField(max_length=500, null=True)


class ReasonChoice(models.Model):
    type = models.CharField(max_length=1)
    description = models.CharField(max_length=80, null=True)


def get_upload_supporting(instance, filename):
    return "images/tasks/supporting/" + str(instance.task.id) + '/' + filename


class Supporting(models.Model):
    task = models.ForeignKey("Task", on_delete=models.CASCADE)
    type = models.CharField(choices=SUPPORTING_TYPES, max_length=1)
    data = models.FileField(upload_to=get_upload_supporting, null=True)
    link = models.URLField(max_length=200, null=True)

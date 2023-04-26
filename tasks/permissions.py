from arccanet import permissions
from django.core.exceptions import PermissionDenied
from arccanetBackend.validators import validate_store
from stores.models import Store
from .models import PeriodicRelation
from authentication.permissions import PermitAdmin, PermitSeeOrEditData


class PermitDetail(permissions.BasePermission):
    @staticmethod
    def validate(request, ut):
        validate_store(request.user, ut.task.store_id)
        if not ut.is_active or \
                (not PermitSeeOrEditData().has_object_permission(request, None, ut.user) and not PermitRoutineHandle.routine_permission(ut.task, request.user)):
            raise PermissionDenied


class PermitRoutine(permissions.BasePermission):
    @staticmethod
    def validate(r, user):
        if not PermitAdmin.user_permission(user) or r.recurrence is None or not user.store.filter(id=r.store.id).exists():
            raise PermissionDenied


class PermitTask(permissions.BasePermission):
    @staticmethod
    def validate(t, user):
        if not PermitAdmin.user_permission(user) or t.recurrence is not None or not user.store.filter(id=t.store.id).exists():
            raise PermissionDenied


class PermitUserTask(permissions.BasePermission):
    @staticmethod
    def validate(ut, user):
        if ut.user_id != user.id and not \
                (PermitAdmin.user_permission(user) and Store.objects.filter(user=user.id, is_active=True).filter(user=ut.user_id).exists()) and not \
                PermitRoutineHandle.routine_permission(ut.task, user):
            raise PermissionDenied


class PermitTaskEdition(permissions.BasePermission):
    @staticmethod
    def validate(t):
        if t.is_editable is False:
            raise PermissionDenied


class PermitCommentHandle(permissions.BasePermission):
    @staticmethod
    def validate(comment, user):
        if comment.user_id != user.id:
            raise PermissionDenied


class PermitRoutineHandle(permissions.BasePermission):
    @staticmethod
    def routine_permission(routine, user):
        return routine.recurrence is not None and PeriodicRelation.objects.filter(user=user, task=routine).exists()

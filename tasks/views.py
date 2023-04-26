import datetime
import requests
import os
from django.http import Http404
from arccanet import permissions, views
from arccanet.response import Response
from arccanet.exceptions import ValidationError
from .serializers import CategorySerializer, GroupSerializer, UserTaskSerializer, ResponseSerializer, CommentSerializer, RoutineSerializer, \
    PeriodicRelationSerializer, ReasonChoiceSerializer, ReasonSerializer
from arccanetBackend.serializers import StoreQuery, BrandQuery, DatesStoreQuery, BrandCategoriesDatesStoreQuery, IsConcludedQuery, DataQuery, FilesQuery, \
    CategoryDatesFilterStoreUserQuery
from authentication.permissions import PermitHolding, PermitAdmin
from .models import Category, Group, Task, UserTask, PeriodicRelation, Response as TaskResponse, Comment, SeenComment, ReasonChoice
from .controllers import launch_comment_notification, _validate_supporting, launch_task_notification, get_ifood_token, update_ifood_reviews
from .permissions import PermitDetail, PermitRoutine, PermitTask, PermitUserTask, PermitTaskEdition, PermitCommentHandle, PermitRoutineHandle
from django.conf import settings
from brands.controllers import get_brand_by_request
from arccanet import conditionbuilder as cb, general, responsebuilder as rb


class GroupAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        qp = BrandQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        q_set = Group.objects.filter(brand=data.get('brand')).order_by("order")
        resp = GroupSerializer(q_set, many=True).data
        return Response(resp, status=200)


class CategoryAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        qp = BrandQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        q_set = Category.objects.filter(brand=data.get('brand')).order_by('title')
        resp = CategorySerializer(q_set, many=True).data
        return Response(resp, status=200)


class TaskDetailAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        ut = general.search_object(UserTask, pk)
        PermitDetail().validate(request, ut)
        if os.environ.get("ENVIRON") == "production" and ut.ifood_relation_id is not None and ut.is_concluded is None:
            update_ifood_reviews(ut)
        uid = request.user.id
        query = \
            """ with unread as (
                    select count(*) unread
                    from tasks_comment c 
                        left join tasks_seencomment sc 
                            on sc.comment_id = c.id
                            and sc.user_id = {}
                    where c.user_id != {}
                        and sc.id is null
                        and c.user_task_id = {}
                ), supporting as (
                    select type, link, array_agg(concat('{}', data)) datas
                    from tasks_supporting
                    where task_id = {}
                    group by type, link
                ), registered_users as (
                    select array_agg(user_id) users
                    from tasks_periodicrelation
                    where task_id = {}
                )
                select ut.id, ut.obs, ut.deadline, ut.created_at, ut.is_concluded, ut.concluded_at, t.title, t.description, t.motivation, t.recurrence, 
                    t.suggested_time, s.type, s.title, s.description, s.min_objects, s.max_objects, t.group_id, u.id, concat(u.first_name, ' ', u.last_name), 
                    u.profile_group_id, c.id, c.title, ut.title_extension, un.unread, ut.ifood_relation_id is not null, sup.type, sup.link, sup.datas, ir.id, 
                    ir.sale_created_at, ir.moderation_status, reg.users
                from tasks_usertask ut
                    join tasks_task t
                        on ut.task_id = t.id
                        and ut.id = {}
                    join tasks_submission s
                        on s.id = t.submission_id
                    join authentication_user u
                        on u.id = ut.user_id
                    left join tasks_category c
                        on c.id = t.category_id
                    left join ifood_reviews ir
                        on ir.id = ut.ifood_relation_id
                    left join supporting sup
                        on true
                    left join registered_users reg
                        on true
                    cross join unread un
            """.format(uid, uid, pk, settings.MEDIA_URL, ut.task_id, ut.task_id, pk)
        self.cursor.execute(query)
        fields = ["id", "obs", "deadline", "created_at", "is_concluded", "concluded_at", "title", "description", "motivation", "recurrence", "suggested_time",
                  "submission_type", "submission_title", "submission_description", "submission_min", "submission_max", "group_id", "user_id", "name",
                  "profile_group", "category_id", "category", "title_extension", "unread", "replies_ifood", "supporting_type", "supporting_link",
                  "supporting_data", "ifood_relation_id", "ifood_order_date", "moderation_status", "routine_users"]
        resp = rb.obj(self.cursor.fetchone(), fields)
        resp = _validate_supporting(resp)
        return Response(resp, status=200)


class UserTaskAdminAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        PermitAdmin().validate(request)
        qp = StoreQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        query = \
            """ select ut.id, t.title, ut.is_active, concat(u.first_name, ' ', u.last_name), ut.deadline, ut.is_concluded, ut.created_at, t.is_editable
                from tasks_usertask ut
                    join tasks_task t
                        on ut.task_id = t.id
                        and t.store_id = {}
                        and t.recurrence is null
                        and t.deleted_at is null
                    join authentication_user u
                        on u.id = ut.user_id
                order by ut.created_at desc
            """.format(data['store'])
        self.cursor.execute(query)
        resp = rb.obj_list(self.cursor.fetchall(), ["id", "task", "is_active", "user", "deadline", "is_concluded", "created_at", "is_editable"])
        return Response(resp, status=200)


class UserTaskListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _get_ordering(field):
        return 'ut.concluded_at desc' if field == 'concluded_at' else 'suggested_datetime_utc, ut.id'

    @staticmethod
    def _get_date_filter(field, initial, final):
        if field == 'concluded_at':
            return """  ut.is_concluded is not null and
                                compare_dts((ut.concluded_at - tz.minutes_offset * interval '1 minute')::timestamp, '{}'::timestamp, '{}'::timestamp)
                            """.format(initial, final + datetime.timedelta(days=1))
        else:
            now = datetime.datetime.utcnow()
            return """  (
                                    (ut.is_concluded is null and 
                                        ((ut.deadline between '{}' and '{}') or ut.deadline < ('{}'::timestamp - tz.minutes_offset * interval '1 minute')::date)
                                    ) or
                                    (ut.is_concluded is not null and '{}'::timestamp - ut.concluded_at < interval '12 hours')
                                )
                            """.format(initial, final, now, now)

    def _get_store_filter(self, store):
        if store is None:
            brand = get_brand_by_request(self.request)
            return "st.brand_id = {}".format(brand.id)
        return "st.id = {}".format(store)

    def _get_pg_filter(self):
        pg_condition = cb.profile_group(None, exclude_holding=not PermitHolding.user_permission(self.request.user), prepend="and ")
        if pg_condition == "":
            return ""
        return """  join authentication_profilegroup pg
                            on pg.id = u.profile_group_id
                        join authentication_hierarchy h
                            on h.id = pg.hierarchy_id
                            {}
                        """.format(pg_condition)

    @staticmethod
    def _get_user_condition(user):
        if user is None:
            return ""
        return f"""  left join tasks_periodicrelation pr
                        on pr.task_id = t.id
                        and pr.user_id = {user}
                    where pr.id is not null or ut.user_id = {user}
        """

    def get(self, request):
        qp = CategoryDatesFilterStoreUserQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        user_condition = self._get_user_condition(data["user"])
        category_condition = cb.single("category_id", data["category"], prepend="and ")
        pg_condition = self._get_pg_filter()
        store_condition = self._get_store_filter(data["store"])
        date_filter = self._get_date_filter(data["filter"], data["initialDate"], data["finalDate"])
        uid = request.user.id
        query = \
            f""" with unread as (
                    select c.user_task_id user_task, count(*) unread
                    from tasks_comment c
                        left join tasks_seencomment sc
                            on sc.comment_id = c.id
                            and sc.user_id = {uid}
                    where c.user_id != {uid}
                        and sc.id is null
                    group by c.user_task_id
                )
                select ut.id, ut.deadline, ut.is_concluded, t.title, t.group_id, concat(u.first_name, ' ', u.last_name), ut.title_extension, 
                    (ut.deadline + t.suggested_time) + tz.minutes_offset * interval '1 minute' suggested_datetime_utc, s.type, u.id, ut.concluded_at, 
                    coalesce(unread.unread, 0), u.profile_group_id, t.recurrence
                from tasks_usertask ut
                    join tasks_task t
                        on ut.task_id = t.id
                        {category_condition}
                        and ut.is_active = true
                    join stores_store st
                        on t.store_id = st.id
                        and {store_condition}
                    join stores_timezone tz
                        on tz.id = st.timezone_id
                        and {date_filter}
                    join authentication_user u
                        on u.id = ut.user_id
                    {pg_condition}
                    join tasks_submission s
                        on s.id = t.submission_id
                    left join unread
                        on unread.user_task = ut.id
                    {user_condition}
                order by {self._get_ordering(data["filter"])}
            """
        self.cursor.execute(query)
        fields = ["id", "deadline", "is_concluded", "title", "group_id", "name", "title_extension", "suggested_datetime_utc", "submission_type", "user_id",
                  "concluded_at", "unread", "profile_group", "recurrence"]
        resp = rb.obj_list(self.cursor.fetchall(), fields)
        return Response(resp)


class UserTaskAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request, pk):
        ut = general.search_object(UserTask, pk)
        PermitTask().validate(ut.task, request.user)
        return Response(UserTaskSerializer(ut).data, status=200)

    @staticmethod
    def delete(request, pk):
        ut = general.search_object(UserTask, pk)
        PermitTask().validate(ut.task, request.user)
        t = ut.task
        ut.delete()
        if not UserTask.objects.filter(task=t).exists():
            t.delete()
            sub = t.submission
            if not Task.objects.filter(submission=sub):
                sub.delete()
        return Response(status=204)

    @staticmethod
    def patch(request, pk):
        ut = general.search_object(UserTask, pk)
        PermitTask().validate(ut.task, request.user)
        PermitTaskEdition().validate(ut.task)
        serializer = UserTaskSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.update(ut, serializer.validated_data)
        return Response(status=204)

    @staticmethod
    def post(request):
        PermitAdmin().validate(request)
        serializer = UserTaskSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        ut = serializer.save()
        launch_task_notification(ut, "{}, uma nova tarefa foi atribuída a você.".format(ut.user.first_name), "Faça a tarefa: {}.".format(ut.task.title))
        return Response(status=204)


class RoutinesAdminAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        PermitAdmin().validate(request)
        qp = StoreQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        query = \
            """ select t.id, t.title, t.recurrence, c.title, s.type
                from tasks_task t
                    left join tasks_category c
                        on t.category_id = c.id
                    join tasks_submission s
                        on t.submission_id = s.id
                where t.recurrence is not null
                    and t.store_id = {}
                    and t.deleted_at is null
                order by t.title
            """.format(data['store'])
        self.cursor.execute(query)
        resp = rb.obj_list(self.cursor.fetchall(), ["id", "task", "recurrence", "category", "submission"])
        for line in resp:
            query = \
                """ select concat(u.first_name, ' ', u.last_name)
                    from tasks_periodicrelation pr
                        join authentication_user u
                            on u.id = pr.user_id
                    where task_id = {}
                """.format(line['id'])
            self.cursor.execute(query)
            line['users'] = [x[0] for x in self.cursor.fetchall()]
        return Response(resp, status=200)


class RoutineAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        PermitAdmin().validate(request)
        routine_serializer = RoutineSerializer(data=request.data, context={'request': request})
        routine_serializer.is_valid(raise_exception=True)
        pr_serializer = PeriodicRelationSerializer(data=general.parse_json(request.data.get('periodic_relations')), many=True,
                                                   context={'routine': routine_serializer.validated_data})
        pr_serializer.is_valid(raise_exception=True)
        routine = routine_serializer.save()
        for i in range(len(pr_serializer.validated_data)):
            pr_serializer.validated_data[i]['task'] = routine
        pr_serializer.save()
        return Response(status=204)

    @staticmethod
    def delete(request, pk):
        routine = general.search_object_with_soft_delete(Task, pk)
        PermitRoutine().validate(routine, request.user)
        UserTask.objects.filter(task=routine).update(is_active=False)
        routine.deleted_at = datetime.datetime.now().astimezone()
        routine.save()
        PeriodicRelation.objects.filter(task=routine).delete()
        return Response(status=204)

    @staticmethod
    def get(request, pk):
        routine = general.search_object_with_soft_delete(Task, pk)
        PermitRoutine().validate(routine, request.user)
        return Response(RoutineSerializer(routine).data, status=200)

    @staticmethod
    def patch(request, pk):
        routine = general.search_object_with_soft_delete(Task, pk)
        PermitRoutine().validate(routine, request.user)
        routine_serializer = RoutineSerializer(data=request.data, context={'request': request})
        routine_serializer.is_valid(raise_exception=True)
        routine_serializer.update(routine, routine_serializer.validated_data)
        return Response(status=204)


class PeriodicRelationAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request, pk):
        routine = general.search_object_with_soft_delete(Task, pk)
        PermitRoutine().validate(routine, request.user)
        prs = PeriodicRelation.objects.values('id', 'user', 'obs', 'priority').filter(task=routine).order_by('priority')
        return Response(prs, status=200)

    @staticmethod
    def delete(request, pk):
        pr = general.search_object(PeriodicRelation, pk)
        PermitRoutine().validate(pr.task, request.user)
        pr.delete()
        return Response(status=204)

    @staticmethod
    def patch(request, pk):
        pr = general.search_object(PeriodicRelation, pk)
        PermitRoutine().validate(pr.task, request.user)
        pr_serializer = PeriodicRelationSerializer(data=request.data, context={'routine': {'store': pr.task.store}})
        pr_serializer.is_valid(raise_exception=True)
        pr_serializer.update(pr, pr_serializer.validated_data)
        return Response(status=204)

    @staticmethod
    def post(request, pk):
        routine = general.search_object_with_soft_delete(Task, pk)
        PermitRoutine().validate(routine, request.user)
        pr_serializer = PeriodicRelationSerializer(data=request.data, context={'routine': {'store': routine.store}})
        pr_serializer.is_valid(raise_exception=True)
        pr_serializer.validated_data['task'] = routine
        pr_serializer.save()
        return Response(status=204)


class ResponseAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def create_ifood_response(ut, reply):
        token = get_ifood_token()
        if token is not None:
            r = requests.post(
                'https://merchant-api.ifood.com.br/review/v1.0/merchants/{}/reviews/{}/answers'.format(ut.ifood_relation.merchant_id, ut.ifood_relation_id),
                json={'text': reply},
                headers={"Authorization": "Bearer {}".format(token)}
            )
            if r.status_code != 201:
                raise ValidationError(r.json())

    def _text_response(self, ut, min_objects, max_objects):
        ts = DataQuery(data=self.request.data, context={'min_objects': min_objects, 'max_objects': max_objects})
        ts.is_valid(raise_exception=True)
        if ut.ifood_relation is not None and os.environ.get("ENVIRON") == "production":
            self.create_ifood_response(ut, ts.validated_data.get('data'))
        TaskResponse.objects.filter(user_task=ut).delete()
        TaskResponse.objects.create(text=ts.validated_data.get('data'), user_task=ut)

    def _file_response(self, ut, min_objects, max_objects):
        fs = FilesQuery(data=self.request.data, context={'min_objects': min_objects, 'max_objects': max_objects})
        fs.is_valid(raise_exception=True)
        data = fs.validated_data
        old_files = data.get('old_files')
        new_files = data.get('new_files')
        new_files_image = data.get('new_files_image')
        TaskResponse.objects.filter(user_task=ut).exclude(id__in=old_files if old_files is not None else []).delete()
        if new_files is not None:
            for i in range(len(new_files)):
                TaskResponse.objects.create(file=new_files[i], user_task=ut, is_image=new_files_image[i])

    def post(self, request, pk):
        ut = general.search_object(UserTask, pk)
        user = request.user
        if ut.user_id != user.id and not PermitHolding.user_permission(user) and not PermitRoutineHandle.routine_permission(ut.task, user):
            raise Http404
        ss = IsConcludedQuery(data=request.data)
        ss.is_valid(raise_exception=True)
        data = ss.data
        if ut.is_concluded is None and data["is_concluded"] is not None:
            if data["is_concluded"]:
                submission = ut.task.submission
                if submission.type == "t":
                    self._text_response(ut, submission.min_objects, submission.max_objects)
                elif submission.type == "f":
                    self._file_response(ut, submission.min_objects, submission.max_objects)
            else:
                TaskResponse.objects.filter(user_task=ut).delete()
                reason = ReasonSerializer(data=request.data.get('reason'))
                reason.is_valid(raise_exception=True)
                ut.reason = reason.save()
            ut.is_concluded = data["is_concluded"]
            ut.concluded_at = datetime.datetime.now().astimezone()
            ut.concluded_by_user = True
            ut.concluded_by = request.user
            ut.save()
        elif ut.is_concluded is not None and data["is_concluded"] is None:
            if ut.is_concluded and request.user.id != ut.user_id:
                launch_task_notification(ut, "{}, sua tarefa foi cancelada.".format(ut.user), "A resposta de sua tarefa não foi aceita, revise-a.")
            ut.is_concluded = None
            ut.concluded_at = None
            ut.concluded_by_user = True
            ut.save()
        else:
            return Response(status=400)
        return Response({'is_concluded': ut.is_concluded, 'concluded_at': ut.concluded_at}, status=200)

    @staticmethod
    def get(request, pk):
        ut = general.search_object(UserTask, pk)
        PermitUserTask().validate(ut, request.user)
        if ut.is_concluded is False:
            resp = ReasonSerializer(ut.reason).data
        else:
            q_set = TaskResponse.objects.filter(user_task=ut)
            resp = ResponseSerializer(q_set, many=True).data
        return Response(resp, status=200)


class CommentAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request, pk):
        ut = general.search_object(UserTask, pk)
        PermitUserTask().validate(ut, request.user)
        q_set = Comment.objects.filter(user_task=ut).order_by("-created_at")
        resp = CommentSerializer(q_set, many=True).data
        return Response(resp, status=200)

    @staticmethod
    def post(request, pk):
        ut = general.search_object(UserTask, pk)
        PermitUserTask().validate(ut, request.user)
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        c = Comment.objects.create(content=serializer.validated_data.get('content'), user_task=ut, user=request.user)
        launch_comment_notification(c)
        return Response(CommentSerializer(c).data, status=200)

    @staticmethod
    def delete(request, pk):
        comment = general.search_object(Comment, pk)
        PermitCommentHandle().validate(comment, request.user)
        comment.delete()
        return Response(status=204)

    @staticmethod
    def patch(request, pk):
        comment = general.search_object(Comment, pk)
        PermitCommentHandle().validate(comment, request.user)
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment.content = serializer.validated_data.get('content')
        comment.save()
        return Response(status=204)


class TaskUserRankingAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qp = DatesStoreQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        today = general.get_store_today(data['timezone'])
        query = \
            """ select concat(u.first_name, ' ', u.last_name), json_object_agg(status, count), sum(count)
                from (
                    select ut.user_id, case
                        when ut.is_concluded is true then 'concluded'
                        when ut.is_concluded is false then 'not_concluded'
                        when deadline < '{}' then 'late'
                        else 'pending' end status, count(*)
                    from tasks_usertask ut
                        join tasks_task t
                            on ut.task_id = t.id
                            and store_id = {}
                            and ut.is_active = true
                            and (ut.deadline < '{}' or (ut.deadline >= '{}' and ut.deadline <= '{}'))
                    group by ut.user_id, status) status_count
                join authentication_user u
                    on u.id = status_count.user_id
                group by u.id
            """.format(today, data.get('store'), today, data.get('initialDate'), data.get('finalDate'))
        self.cursor.execute(query)
        resp = rb.obj_list(self.cursor.fetchall(), ["user", "status", "total"])
        return Response(resp, status=200)


class SeenCommentAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request, pk):
        user = request.user
        ut = general.search_object(UserTask, pk)
        PermitUserTask().validate(ut, user)
        comments = Comment.objects.filter(user_task=ut).exclude(user=user)
        for comment in comments:
            if not SeenComment.objects.filter(comment=comment, user=user).exists():
                SeenComment.objects.create(comment=comment, user=user)
        return Response(status=200)


class PicturesAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qp = BrandCategoriesDatesStoreQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        categories_condition = cb.multiple('category_id', data.get("category"))
        tz = datetime.timedelta(minutes=data['timezone'])
        in_dt = datetime.datetime.combine(data.get("initialDate"), datetime.time()) + tz
        fin_dt = datetime.datetime.combine(data.get("finalDate"), datetime.time()) + tz + datetime.timedelta(days=1)
        query = \
            """ select concat('{}', r.file), t.title, t.recurrence, c.title, ut.concluded_at, concat(u.first_name, ' ', u.last_name), ut.id
                from tasks_usertask ut
                    join tasks_task t
                        on ut.task_id = t.id
                        and t.{}
                        and t.store_id = {}
                        and ut.is_active = true
                        and ut.is_concluded = true
                        and ut.concluded_at >= '{}'
                        and ut.concluded_at < '{}'
                    join tasks_submission s
                        on s.id = t.submission_id
                        and s.type = 'f'
                    join authentication_user u
                        on u.id = ut.user_id
                    join tasks_response r
                        on r.user_task_id = ut.id
                    join tasks_category c
                        on c.id = t.category_id
                order by ut.concluded_at desc
            """.format(settings.MEDIA_URL, categories_condition, data.get('store'), in_dt, fin_dt)
        self.cursor.execute(query)
        resp = rb.obj_list(self.cursor.fetchall(), ["picture", "task_title", "task_recurrence", "category", "created_at", "user", "usertask_id"])
        return Response(resp)


class PicturesCategoriesAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qp = DatesStoreQuery(data=request.query_params, context={'request': request})
        qp.is_valid(raise_exception=True)
        data = qp.validated_data
        tz = datetime.timedelta(minutes=data['timezone'])
        in_dt = datetime.datetime.combine(data.get("initialDate"), datetime.time()) + tz
        fin_dt = datetime.datetime.combine(data.get("finalDate"), datetime.time()) + tz + datetime.timedelta(days=1)
        query = \
            """ select c.id, c.title
                from tasks_usertask ut
                    join tasks_task t
                        on ut.task_id = t.id
                        and t.store_id = {}
                        and ut.is_active = true
                        and ut.is_concluded = true
                        and ut.concluded_at >= '{}'
                        and ut.concluded_at < '{}'
                    join tasks_submission s
                        on s.id = t.submission_id
                        and s.type = 'f'
                    join tasks_category c
                        on c.id = t.category_id
                group by c.id
                order by c.title
            """.format(data.get('store'), in_dt, fin_dt)
        self.cursor.execute(query)
        resp = rb.obj_list(self.cursor.fetchall(), ["id", "title"])
        return Response(resp)


class ReasonChoiceAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        rc = ReasonChoice.objects.all().order_by('id')
        resp = ReasonChoiceSerializer(rc, many=True).data
        return Response(resp)

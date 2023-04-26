from django.core.management.base import BaseCommand
from django.db import connection
import datetime
from tasks.models import UserTask
from authentication.controllers import is_work_day
from arccanet import conditionbuilder as cb
from tasks.controllers import launch_task_notification


class Command(BaseCommand):
    cursor = None

    def add_arguments(self, parser):
        parser.add_argument('-brand', type=int)

    @staticmethod
    def check_task(relation, today, today_weekday):
        recurrence = relation[2]
        advance_days = relation[4]
        index = relation[3]
        return recurrence == "d" or (recurrence == "w" and (today_weekday + advance_days) % 7 == index) or (recurrence == "m" and (today + datetime.timedelta(days=advance_days)).day == index)

    def handle(self, *args, **options):
        self.cursor = connection.cursor()
        brand_condition = cb.single('s.brand_id', options['brand'], prepend='and ')
        query = \
            """ select pr.user_id, pr.task_id, t.recurrence, t.recurrence_index, t.advance_days, pr.obs, pr.priority, t.store_id, s.country_id, s.state_id
                from tasks_periodicrelation pr
                    join tasks_task t
                        on t.id = pr.task_id
                        and t.recurrence is not null
                        and t.deleted_at is null
                    join authentication_user u
                        on pr.user_id = u.id
                        and u.is_active = true
                    join stores_store s
                        on s.id = t.store_id
                        and s.is_active = true
                        {}
                order by pr.task_id, pr.priority
            """.format(brand_condition)
        self.cursor.execute(query)
        relations = self.cursor.fetchall()
        today = datetime.datetime.utcnow().date()
        today_weekday = today.weekday()
        i = 0
        while i < len(relations):
            task = relations[i][1]
            is_day_of_task_creation = self.check_task(relations[i], today, today_weekday)
            priority_level = None
            while i < len(relations) and relations[i][1] == task:
                if is_day_of_task_creation and (priority_level is None or priority_level == relations[i][6]):
                    yesterday = datetime.datetime.combine(today - datetime.timedelta(days=1), datetime.time(23, 59)).astimezone()
                    UserTask.objects.filter(user_id=relations[i][0], task_id=task, is_concluded=None, deadline__lt=today)\
                        .update(is_concluded=False, concluded_by_user=False, concluded_at=yesterday)
                    deadline = today + datetime.timedelta(days=relations[i][4])
                    if is_work_day(relations[i][0], relations[i][7], deadline, relations[i][8], relations[i][9]):
                        if not UserTask.objects.filter(deadline=deadline, task_id=task, user_id=relations[i][0]).exists():
                            ut = UserTask.objects.create(deadline=deadline, obs=relations[i][5], task_id=task, user_id=relations[i][0])
                            launch_task_notification(ut, "{}, uma nova rotina foi atribuída a você.".format(ut.user), "Faça a rotina: {}.".format(ut.task.title))
                            priority_level = relations[i][6]
                i += 1
                

from django.core.management.base import BaseCommand
from django.db import connection
from tasks.models import UserTask
from arccanet import general
from tasks.controllers import update_ifood_reviews
import datetime


class Command(BaseCommand):
    cursor = None

    def update_ifood_tasks(self):
        today = datetime.datetime.utcnow().date()
        query = """select ut.id
                    from tasks_usertask ut
                        join ifood_reviews r
                            on ut.ifood_relation_id = r.id
                            and ut.is_concluded is null
                            and ut.deadline >= '{}'
                """.format(today)
        query = """select ut.id
                            from tasks_usertask ut
                                join ifood_reviews r
                                    on ut.ifood_relation_id = r.id
                                    and ut.is_concluded is null
                        """
        self.cursor.execute(query)
        tasks = self.cursor.fetchall()
        for task in tasks:
            ut_id = task[0]
            ut = general.search_object(UserTask, ut_id)
            update_ifood_reviews(ut)

    def handle(self, *args, **options):
        self.cursor = connection.cursor()
        self.update_ifood_tasks()

from django.core.management.base import BaseCommand
from django.db import connection
import datetime
from tasks.models import Category, Task, Submission, UserTask
from authentication.models import User
from tasks.controllers import launch_task_notification, get_sale_details


class Command(BaseCommand):
    cursor = None

    def create_ifood_tasks(self):
        def get_category(brand):
            try:
                return Category.objects.get(title="Atendimento", brand_id=brand)
            except Category.DoesNotExist:
                return Category.objects.create(title="Atendimento", brand_id=brand)

        def get_submission():
            submission_obj = {
                'type': 't',
                'title': 'Responda a avaliação do iFood diretamente pelo campo abaixo',
                'description': 'Utilize o campo abaixo para responder diretamente na plataforma do iFood. Atenção, escreva a resposta exatamente como responderia no iFood.',
                'min_objects': 10,
                'max_objects': 300
            }
            try:
                return Submission.objects.get(**submission_obj)
            except Submission.DoesNotExist:
                return Submission.objects.create(**submission_obj)

        def get_task(store, brand):
            task_obj = {
                'title': 'Responda a avaliação no iFood',
                'description': '',
                'motivation': 'A nota iFood é um dos principais indicadores de qualidade de atendimento!',
                'store_id': store,
                'category': get_category(brand),
                'submission': get_submission(),
                'group': None,
                'recurrence': None,
                'advance_days': None,
                'recurrence_index': None,
                'is_editable': False
            }
            try:
                return Task.objects.get(**task_obj)
            except Task.DoesNotExist:
                return Task.objects.create(**task_obj)

        def build_obj(r, sale_details):
            resp = "<b>Comentário:</b> {}<br/><b>Nota:</b> {}".format(r[3] if r[3] is not None else '', r[2])
            resp += "<br/><b>Cliente:</b> {}".format(r[7] if r[7] is not None else '')
            resp += "<br/><b>Data da venda:</b> {}".format(r[4].strftime('%d/%m/%Y %H:%M') if r[4] is not None else '')
            resp += "<br/><b>Data da avaliação:</b> {}".format(r[5].strftime('%d/%m/%Y %H:%M') if r[5] is not None else '')
            resp = build_sale_details(resp, sale_details)
            return resp

        def build_sale_details(resp, sale_details):
            if len(sale_details) != 0:
                resp += "<br/><b>Conteúdo do pedido na Saipos:</b> "
                for sale_detail in sale_details:
                    if sale_detail[1] == 'Diversos' or sale_detail[2] == 'Diversos':
                        resp += "<br/><p>&emsp; {0}".format('; '.join(sale_detail[3]) if sale_detail[3] is not None else '')
                        resp += "<br/>&emsp; <b><u>OBS:</u></b> Houve um erro de integração entre o cardápio da Saipos e do Ifood. </p>"
                    else:
                        resp += "<br/><p>&emsp; {0} {1} {2} - {3} </p>".format(sale_detail[0] if sale_detail[0] is not None else '',sale_detail[1].upper() if sale_detail[1] is not None else '',sale_detail[2].upper() if sale_detail[2] is not None else '',', '.join(sale_detail[3]).upper() if sale_detail[3] is not None else '')
            return resp
        def get_user(store):
            manager = User.objects.filter(store=store, profile_group__value="M", is_active=True).order_by('created_at')
            if manager.exists():
                return manager[0]
            operator = User.objects.filter(store=store, profile_group__value="P", is_active=True).order_by('created_at')
            if operator.exists():
                return operator[0]
            franch = User.objects.filter(store=store, profile_group__value="F", is_active=True).order_by('created_at')
            if franch.exists():
                return franch[0]
            leader = User.objects.filter(store=store, profile_group__value="L", is_active=True).order_by('created_at')
            if leader.exists():
                return leader[0]
            return None

        today = datetime.datetime.utcnow().date()
        query = \
            """ select s.id, s.brand_id, r.average, r.comment, r.sale_created_at - tz.minutes_offset * interval '1 minute', r.created_at - tz.minutes_offset * interval '1 minute', r.id, r.customer_name
                from ifood_reviews r
                    join stores_store s
                        on s.id = r.store_id
                        and s.is_active = true
                        and now() - r.created_at < interval '24 hours'
                        and r.comment != ''
                    join stores_timezone tz
                        on tz.id = s.timezone_id
            """
        self.cursor.execute(query)
        reviews = self.cursor.fetchall()
        for review in reviews:
            task = get_task(review[0], review[1])
            sale_details = get_sale_details(review[6])
            user_task_obj = {
                'task': task,
                'deadline': today,
                'obs': build_obj(review, sale_details),
                'title_extension': ('venda do dia {}'.format(review[4].strftime("%d/%m/%Y")) if review[4] is not None else ''),
                'ifood_relation_id': review[6]
            }
            responsible = get_user(review[0])
            if responsible is not None:
                ut = UserTask.objects.create(**user_task_obj, user=responsible)
                launch_task_notification(ut, "{}, uma nova tarefa foi atribuída a você.".format(ut.user), "Faça a tarefa: {}.".format(ut.task.title))

    def handle(self, *args, **options):
        self.cursor = connection.cursor()
        self.create_ifood_tasks()

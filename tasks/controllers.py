from .models import Task, Supporting
from authentication.models import Notification, NotificationUser
from arccanet import responsebuilder as rb
from django.db import connection
import requests
import datetime
import os
from arccanet.exceptions import ValidationError


def get_supporting(obj):
    if isinstance(obj, Task):
        supports = Supporting.objects.filter(task_id=obj.id)
        if len(supports) > 0:
            support_type = supports[0].type
            support_link = supports[0].link
            support_data = []
            if support_type == 'f':
                for i in range(len(supports)):
                    support_data.append({'data': supports[i].data.url, 'type': support_type, 'size': supports[i].data.size})
                sup_list = support_data
            else:
                sup_list = {'link': support_link, 'type': support_type}
            return sup_list
    return None


def launch_comment_notification(comment):
    cursor = connection.cursor()
    query = \
        """ select * from (
                select user_id
                from tasks_comment c
                where c.user_task_id = {}

                union

                select {} user_id

                union

                select u.id user_id
                from authentication_user u
                    join authentication_user_store us
                        on u.id = us.user_id
                    join authentication_profilegroup pg
                        on pg.id = u.profile_group_id
                where u.is_active = true
                    and us.store_id = {}
                    and pg.value in ('M', 'F', 'P', 'L', 'S')
            ) users
            where user_id != {}
        """.format(comment.user_task_id, comment.user_task.user_id, comment.user_task.task.store_id, comment.user_id)
    cursor.execute(query)
    users = rb.obj_list(cursor.fetchall(), ["id"])
    notification = {
        "title": "{} comentou na tarefa: {}.".format(comment.user, comment.user_task.task.title),
        "description": "",
        "action": "/task/{}/".format(comment.user_task.id),
        "brand": comment.user_task.task.store.brand
    }
    if len(users) > 0:
        notification = Notification.objects.create(**notification)
        NotificationUser.objects.bulk_create([NotificationUser(notification=notification, user_id=user['id']) for user in users])


def _validate_supporting(resp):
    if isinstance(resp, list):
        for r in resp:
            if r['supporting_type'] != 'f' and r['supporting_data'] is not None:
                r['supporting_data'] = None
    else:
        if resp['supporting_type'] != 'f' and resp['supporting_data'] is not None:
            resp['supporting_data'] = None
    return resp


def launch_task_notification(user_task, title, description):
    if user_task.is_active:
        notification = {
            "title": title,
            "description": description,
            "action": "/tasks/{}/".format(user_task.id),
            "brand": user_task.task.store.brand
        }
        notification = Notification.objects.create(**notification)
        NotificationUser.objects.create(notification=notification, user=user_task.user)


def get_ifood_token():
    cursor = connection.cursor()
    cursor.execute("select value from cache where cache_key = 'ifood-token' and expires > now()")
    resp = cursor.fetchone()
    if resp is None:
        r = requests.post(
            'https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token',
            "grantType=client_credentials&clientId={}&clientSecret={}".format(os.environ.get('IFOOD_CLIENT_ID'), os.environ.get('IFOOD_CLIENT_SECRET')),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        if r.status_code == 200:
            resp = r.json()
            cursor.execute("""
                delete from cache where cache_key = 'ifood-token';

                insert into cache(cache_key, value, expires) values('ifood-token', '{}', '{}');
            """.format(resp['accessToken'], (datetime.datetime.utcnow() + datetime.timedelta(seconds=resp['expiresIn'] - 60)).replace(microsecond=0)))
            connection.commit()
            token = resp['accessToken']
        else:
            raise Exception("Ifood Login failed with status " + str(r.status_code))
    else:
        token = resp[0]
    return token


def validate_ifood_review(ut):
    if ut.ifood_relation_id is None or ut.ifood_relation.merchant_id is None:
        raise ValidationError("This is not a valid ifood user-task")


def update_ifood_reviews(obj):
    cursor = connection.cursor()
    token = get_ifood_token()
    validate_ifood_review(obj)
    old_customer = obj.ifood_relation.customer_name
    r = requests.get(
        'https://merchant-api.ifood.com.br/review/v1.0/merchants/{}/reviews/{}'.format(obj.ifood_relation.merchant_id, obj.ifood_relation_id),
        headers={"Authorization": "Bearer {}".format(token)}
    )
    if r.status_code != 200:
        raise ValidationError(r.json())
    else:
        resp = r.json()
        customer_name = resp.get('customerName')
        moderation_status = resp.get('moderationStatus')
        cursor.execute(
            """ update ifood_reviews
                set customer_name = {}, moderation_status = {}
                where id = '{}' 
            """.format(repr(customer_name) if customer_name is not None else 'null', repr(moderation_status) if moderation_status is not None else 'null',
                       obj.ifood_relation_id)
        )
        connection.commit()
        index_for_update_sale_detail = obj.obs.find('Conteúdo do pedido na Saipos')
        if index_for_update_sale_detail == -1:
            update_sale_details(obj.obs, obj.ifood_relation_id, obj.id)
        if moderation_status == 'APPROVED':
            obj.is_concluded = True
            obj.concluded_by_user = False
            obj.concluded_at = datetime.datetime.now().astimezone()
            obj.save()
            launch_task_notification(obj, '{}, uma tarefa do iFood foi concluída'.format(obj.user.first_name),
                                     'Essa tarefa foi concluída pois sua avaliação teve a moderação aprovada.')
        if moderation_status == 'REQUESTED':
            obj.deadline = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).date()
            obj.save()
        if old_customer is None and customer_name is not None:
            obs = obj.obs
            index = obs.find('Cliente: <br/>')
            if index != -1:
                new_obs = obs[:index + 9] + customer_name + obs[index + 9:]
                obj.obs = new_obs
                obj.save()


def update_sale_details(obs, review_id, ut_id):
    sale_details = get_sale_details(review_id)
    obs += "<br/><b>Conteúdo do pedido na Saipos:</b> "
    for sale_detail in sale_details:
        if sale_detail[1] == 'Diversos' or sale_detail[2] == 'Diversos':
            obs += "<br/><p>&emsp; {0}".format('; '.join(sale_detail[3]) if sale_detail[3] is not None else '')
            obs += "<br/>&emsp; <b><u>OBS:</u></b> Houve um erro de integração entre o cardápio da Saipos e do Ifood. </p>"
        else:
            obs += "<br/><p>&emsp; {0} {1} {2} - {3} </p>".format(sale_detail[0] if sale_detail[0] is not None else '', sale_detail[1].upper() if sale_detail[1] is not None else '', sale_detail[2].upper() if sale_detail[2] is not None else '', ', '.join(sale_detail[3]).upper() if sale_detail[3] is not None else '')
    cursor = connection.cursor()
    cursor.execute(
        """ update tasks_usertask
            set obs = {}
            where id = {}
        """.format(repr(obs) if obs is not None else 'null', ut_id)
    )
    connection.commit()


def get_sale_details(review_id):
    update_sale_details_query = """select ss_item.quantity,item.description, products_variation.description as "variation", ARRAY_AGG(ss_itemchoice.fraction|| ' ' ||products_choice.description) as choices
                                                from saipos_saleitem ss_item
                                                    join products_item item
                                                        on item.id = ss_item.item_id
                                                    join saipos_sales ss
                                                        on ss.id_sale = ss_item.sale_id
                                                    join ifood_reviews r
                                                        on r.sale_id = ss.cod_sale1
                                                    join products_variation
                                                        on products_variation.id = ss_item.variation_id
                                                    join saipos_saleitemchoice ss_itemchoice
                                                        on ss_itemchoice.sale_item_id = ss_item.id
                                                    join products_choice
                                                        on products_choice.id = ss_itemchoice.choice_id
                                                    where r.id ='{0}'
                                                    group by ss_item.quantity,item.description, products_variation.description""".format(review_id)

    cursor = connection.cursor()
    cursor.execute(update_sale_details_query)
    sale_details = cursor.fetchall()
    return sale_details

from arccanet.test import APITestCase
from django.urls import reverse
from stores.models import Store, Timezone
from authentication.models import User, ProfileGroup, Hierarchy
from brands.models import Brand
from .models import Task, Group, Category, Comment, Submission, UserTask, PeriodicRelation, SeenComment, Reason, ReasonChoice, Supporting
import datetime
import json
from copy import deepcopy
from django.core.files.uploadedfile import SimpleUploadedFile
from stores.management.commands.createdbfunctions import Command

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)


class TaskTests(APITestCase):
    def setUp(self):
        Command().handle()
        h0 = Hierarchy.objects.create(value=0, description='Holding')
        h1 = Hierarchy.objects.create(value=1, description='Franqueado')
        h2 = Hierarchy.objects.create(value=2, description='Gerente')
        h3 = Hierarchy.objects.create(value=3, description='Funcionário')
        h = ProfileGroup.objects.create(id=1, value='H', description='Holding', hierarchy=h0)
        f = ProfileGroup.objects.create(id=2, value='F', description='Franqueado', hierarchy=h1)
        m = ProfileGroup.objects.create(id=3, value='M', description='Gerente', hierarchy=h2)
        e = ProfileGroup.objects.create(id=4, value='E', description='Funcionário', hierarchy=h3)
        Brand.objects.create(id=1, name="M1", subdomain='vezpanet')
        Brand.objects.create(id=2, name="M2")
        t = Timezone.objects.create(javascript_description='America/Sao_Paulo', minutes_offset=180)
        Store.objects.create(id=1, name='L1M1', store_code='1', is_holding=True, brand_id=1, timezone=t, country_id=1)
        Store.objects.create(id=2, name='L2M1', store_code='2', brand_id=1, timezone=t, country_id=1)
        Store.objects.create(id=3, name='L3M1', store_code='3', brand_id=1, timezone=t, country_id=1)
        Store.objects.create(id=4, name='L4M2', store_code='4', brand_id=2, timezone=t, country_id=1)
        u1 = User.objects.create(email="h@h.com", profile_group=h)
        u1.store.set([1, 2, 3])
        u2 = User.objects.create(email="m@m.com", profile_group=m)
        u2.store.set([1, 2])
        u3 = User.objects.create(email="e@e.com", profile_group=e)
        u3.store.set([1, 2])
        u4 = User.objects.create(email="e2@e.com", profile_group=e)
        Category.objects.create(id=1, title='c1', brand_id=1)
        Category.objects.create(id=2, title='c2', brand_id=2)
        Group.objects.create(id=1, title='g1', brand_id=1, order=1)
        Group.objects.create(id=2, title='g2', brand_id=2, order=1)
        Submission.objects.create(id=10, type='s', title='s1')
        Submission.objects.create(id=11, type='t', title='s2', min_objects=1, max_objects=10)
        Task.objects.create(id=5, title='t1', store_id=1, category_id=1, submission_id=10)
        Task.objects.create(id=6, title='r1', store_id=1, category_id=1, submission_id=11, recurrence='d')
        Supporting.objects.create(id=20, task_id=5, type='l', link="www.google.com")
        Supporting.objects.create(id=21, task_id=6, type='l', link="www.globo.com")
        UserTask.objects.create(id=5, task_id=5, user=u3, deadline=datetime.date.today())
        UserTask.objects.create(id=6, task_id=6, user=u3, deadline=datetime.date.today())
        UserTask.objects.create(id=7, task_id=6, user=u4, deadline=datetime.date.today())
        UserTask.objects.create(id=8, task_id=6, user=u4, deadline=datetime.date.today())
        UserTask.objects.create(id=9, task_id=6, user=u4, deadline=datetime.date.today(), is_active=False)
        Reason.objects.create(id=30, reason_choice_id=7, description="bla bla bla")
        ReasonChoice.objects.create(id=7, type="t", description="transito")

    def test_category(self):
        url = reverse('category')
        self.client.force_login(user=User.objects.get(email="h@h.com"))

        r = self.client.get(url, {'brand': 1})
        self.assertEqual(r.data, [{'id': 1, 'title': 'c1', 'brand': 1}])

    def test_group(self):
        url = reverse('group')
        self.client.force_login(user=User.objects.get(email="h@h.com"))

        r = self.client.get(url, {'brand': 1})
        self.assertEqual(r.data, [{'id': 1, 'title': 'g1'}])

    def test_user_task(self):
        # Get Admin
        url = reverse('user-task-admin')
        self.client.force_login(user=User.objects.get(email="e@e.com"))
        today = datetime.date.today()

        r = self.client.get(url, {'store': 1})
        self.assertEqual(r.status_code, 403)

        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.get(url, {'store': 1})
        self.assertEqual([x['id'] for x in r.data], [5])

        # Get
        url = reverse('user-task-list')
        self.client.force_login(user=User.objects.get(email="e@e.com"))
        r = self.client.get(url, {'category': '', 'user': '', 'store': 1, 'initialDate': today, 'finalDate': today, 'filter': 'deadline'})
        self.assertEqual([x['id'] for x in r.data], [5, 6])

        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.get(url, {'category': '', 'user': User.objects.get(email="e@e.com").id, 'store': 1, 'initialDate': today, 'finalDate': today, 'filter': 'concluded_at'})
        self.assertEqual(r.data, [])

        r = self.client.get(url, {'category': '', 'user': '', 'store': 10, 'initialDate': today, 'finalDate': today, 'filter': 'concluded_at'})
        self.assertEqual(r.status_code, 400)

        r = self.client.get(url, {'category': '', 'user': '', 'store': 1, 'initialDate': today, 'finalDate': '2000-01-01', 'filter': 'concluded_at'})
        self.assertEqual(r.status_code, 400)

        # Post
        url = reverse('user-task')
        self.client.force_login(user=User.objects.get(email="e@e.com"))
        obj = {
            "task.category": 1,
            "task.motivation": "mooo",
            "task.description": "desc",
            "task.store": 1,
            "task.submission.description": "",
            "task.submission.max_objects": 1,
            "task.submission.min_objects": 0,
            "task.submission.title": "Insira os arquivos",
            "task.submission.type": "t",
            "task.submission.verbose": "Arquivo",
            "task.supporting.type": "l",
            "task.supporting.link": "http://www.aeitaonline.com.br/wiki/index.php?title=Turma_de_2024",
            "task.supporting.data": [],
            "task.title": "titaa",
            "deadline": "2021-12-16",
            "user": User.objects.get(email="h@h.com").id,
            "is_active": True
        }

        r = self.client.post(url, obj, format='multipart')
        self.assertEqual(r.status_code, 403)
        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.post(url, obj, format='multipart')
        self.assertEqual(r.status_code, 204)
        self.assertEqual(Task.objects.filter(title="titaa").exists(), True)
        new_id = UserTask.objects.get(task__title="titaa").id

        obj2 = deepcopy(obj)
        obj2['task.title'] = 'ut2'
        obj2['task.submission.description'] = 'desc'
        r = self.client.post(url, obj2, format='multipart')
        self.assertEqual(r.status_code, 204)

        obj3 = deepcopy(obj)
        obj3['task.category'] = 2
        r = self.client.post(url, obj3, format='multipart')
        self.assertEqual(r.status_code, 400)

        obj3['task.store'] = 4
        r = self.client.post(url, obj3, format='multipart')
        self.assertEqual(r.status_code, 400)

        obj3['task.submission.max_objects'] = -1
        r = self.client.post(url, obj3, format='multipart')
        self.assertEqual(r.status_code, 400)

        # Get single
        r = self.client.get(reverse('user-task', args=[new_id]))
        self.assertEqual(r.status_code, 200)

        r = self.client.get(reverse('user-task', args=[100]))
        self.assertEqual(r.status_code, 404)

        r = self.client.get(reverse('user-task', args=[6]))
        self.assertEqual(r.status_code, 403)

        # Patch
        obj['is_active'] = False
        r = self.client.patch(reverse('user-task', args=[new_id]), obj, format='multipart')
        self.assertEqual(UserTask.objects.get(id=new_id).is_active, False)

        obj['task.submission.title'] = 'new_tit'
        r = self.client.patch(reverse('user-task', args=[new_id]), obj, format='multipart')
        self.assertEqual(r.status_code, 204)

        obj['task.supporting.type'] = 'l'
        obj['task.supporting.link'] = 'https://www.mytecbits.com/microsoft/sql-server'
        r = self.client.patch(reverse('user-task', args=[new_id]), obj, format='multipart')
        self.assertEqual(r.status_code, 204)

        obj['task.supporting.type'] = 'f'
        obj['task.supporting.data'].append(SimpleUploadedFile('small.gif', SMALL_GIF, content_type='image/gif'))
        r = self.client.patch(reverse('user-task', args=[new_id]), obj, format='multipart')
        self.assertEqual(r.status_code, 204)

        # Get with supporting
        r = self.client.get(reverse('user-task', args=[new_id]))
        self.assertEqual(r.status_code, 200)

        # Patch again
        r = self.client.patch(reverse('user-task', args=[new_id]), {}, format='multipart')
        self.assertEqual(r.status_code, 400)

        # Delete
        self.client.delete(reverse('user-task', args=[new_id]))
        self.assertEqual(UserTask.objects.filter(id=new_id).exists(), False)

    def test_routine(self):
        # Get list
        url = reverse('routines-admin')
        self.client.force_login(user=User.objects.get(email="e@e.com"))

        r = self.client.get(url, {'store': 1})
        self.assertEqual(r.status_code, 403)

        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.get(url, {'store': 1})
        self.assertEqual(r.data, [{'id': 6, 'task': 'r1', 'recurrence': 'd', 'category': 'c1', 'submission': 't', 'users': []}])

        # Post
        url = reverse('routines')
        obj = {
            "title": "routine1",
            "description": "desc",
            "motivation": "mot",
            "category": 1,
            "group": 1,
            "store": 1,
            "recurrence": "d",
            "recurrence_index": None,
            "advance_days": 0,
            "submission": {
                "description": "",
                "max_objects": 1,
                "min_objects": 0,
                "title": "Insira os arquivossd",
                "type": "t",
                "verbose": "Arquivo"
            },
            "suggested_time": "20:20",
            "supporting": {
                "type": "l",
                "link": "http://www.aeitaonline.com.br/wiki/index.php?title=Turma_de_2024",
                "data": []
            },
            "periodic_relations": json.dumps([{"user": User.objects.get(email="h@h.com").id, "obs": "oi"}])
        }
        self.client.force_login(user=User.objects.get(email="e@e.com"))
        r = self.client.post(url, obj)
        self.assertEqual(r.status_code, 403)

        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.post(url, obj)
        self.assertEqual(Task.objects.filter(title="routine1").exists(), True)
        new_id = Task.objects.get(title="routine1").id

        obj2 = deepcopy(obj)
        obj2['periodic_relations'] = json.dumps([{"user": User.objects.get(email="e2@e.com").id, "obs": "oi"}])
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['recurrence'] = 'm'
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['advance_days'] = None
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['recurrence'] = None
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['suggested_time'] = None
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['group'] = 2
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['category'] = 2
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        obj2['store'] = 4
        r = self.client.post(url, obj2)
        self.assertEqual(r.status_code, 400)

        # Get Single
        r = self.client.get(reverse('routines', args=[100]))
        self.assertEqual(r.status_code, 404)

        self.client.force_login(user=User.objects.get(email="e@e.com"))
        r = self.client.get(reverse('routines', args=[new_id]))
        self.assertEqual(r.status_code, 403)

        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.get(reverse('routines', args=[new_id]))
        self.assertEqual(r.status_code, 200)

        # Patch
        obj['submission']['description'] = 'new_desc'
        obj['title'] = 'new_title'
        r = self.client.patch(reverse('routines', args=[new_id]), obj)
        self.assertEqual(Task.objects.get(id=new_id).title, 'new_title')

        obj['supporting'] = {'type': 'l', 'link': 'https://www.mytecbits.com/microsoft/sql-server', 'data': []}
        r = self.client.patch(reverse('routines', args=[new_id]), obj)
        self.assertEqual(r.status_code, 204)

        # Delete
        self.client.delete(reverse('routines', args=[new_id]))
        self.assertEqual(Task.objects.filter(id=new_id, deleted_at=None).exists(), False)

    def test_pr(self):
        self.client.force_login(user=User.objects.get(email="h@h.com"))

        # Post
        uid = User.objects.get(email="h@h.com").id
        obj = {
            "user": uid,
            "obs": "oi"
        }
        r = self.client.post(reverse('periodic-relation', args=[6]), obj)
        self.assertEqual(PeriodicRelation.objects.filter(task_id=6, user_id=uid).exists(), True)
        new_id = PeriodicRelation.objects.get(task_id=6, user_id=uid).id

        obj["obs"] = ""
        r = self.client.post(reverse('periodic-relation', args=[6]), obj)
        self.assertEqual(PeriodicRelation.objects.get(id=new_id).obs, "")

        # Get
        r = self.client.get(reverse('periodic-relation', args=[6]))
        self.assertEqual(r.data[0]['id'], new_id)

        # Patch
        obj['user'] = User.objects.get(email="e@e.com").id
        r = self.client.patch(reverse('periodic-relation', args=[100]), obj)
        self.assertEqual(r.status_code, 404)

        r = self.client.patch(reverse('periodic-relation', args=[new_id]), obj)
        self.assertEqual(PeriodicRelation.objects.get(id=new_id).user_id, obj['user'])

        # Delete
        self.client.delete(reverse('periodic-relation', args=[new_id]))
        self.assertEqual(PeriodicRelation.objects.filter(id=new_id).exists(), False)

    def test_user_ranking(self):
        url = reverse('task-user-ranking')
        self.client.force_login(user=User.objects.get(email="h@h.com"))

        r = self.client.get(url, {'store': 1, 'initialDate': datetime.date.today(), 'finalDate': datetime.date.today()})
        self.assertEqual(r.data[0]['status']['pending'], 2)

    def test_comment(self):
        self.client.force_login(user=User.objects.get(email="h@h.com"))

        # Post
        obj = {"content": "<asdasd>"}
        r = self.client.post(reverse('comment', args=[7]), obj)
        self.assertEqual(r.status_code, 403)

        r = self.client.post(reverse('comment', args=[6]), obj)
        self.assertEqual(Comment.objects.filter(user_task_id=6).exists(), True)
        new_id = Comment.objects.get(user_task_id=6).id

        # Get
        r = self.client.get(reverse('comment', args=[6]))
        self.assertEqual(r.data[0]['content'], obj['content'])

        # Patch
        aux_comment = Comment.objects.create(user_task_id=6, content="")
        obj = {"content": "123"}
        r = self.client.patch(reverse('comment', args=[100]), obj)
        self.assertEqual(r.status_code, 404)

        r = self.client.patch(reverse('comment', args=[aux_comment.id]), obj)
        self.assertEqual(r.status_code, 403)

        r = self.client.patch(reverse('comment', args=[new_id]), obj)
        self.assertEqual(Comment.objects.get(id=new_id).content, "123")

        # Delete
        r = self.client.delete(reverse('comment', args=[aux_comment.id]))
        self.assertEqual(r.status_code, 403)

        r = self.client.delete(reverse('comment', args=[new_id]))
        self.assertEqual(Comment.objects.filter(id=new_id).exists(), False)

        # Seen
        r = self.client.post(reverse('seen-comment', args=[6]))
        self.assertEqual(SeenComment.objects.filter(user=User.objects.get(email="h@h.com")).exists(), True)

    def test_response(self):
        self.client.force_login(user=User.objects.get(email="e@e.com"))

        r = self.client.post(reverse('response', args=[7]))
        self.assertEqual(r.status_code, 404)

        r = self.client.post(reverse('response', args=[6]), {'is_concluded': None})
        self.assertEqual(r.status_code, 400)

        r = self.client.post(reverse('response', args=[6]), {'is_concluded': False, "reason": None})
        self.assertEqual(r.status_code, 400)

        obj_reason = {
            "reason_choice": 7,
            "description": "bla bla bla"
        }
        r = self.client.post(reverse('response', args=[6]), {'is_concluded': False, "reason": obj_reason})
        self.assertEqual(UserTask.objects.get(id=6).is_concluded, False)

        r = self.client.post(reverse('response', args=[6]), {'is_concluded': None})
        self.assertEqual(UserTask.objects.get(id=6).is_concluded, None)

        r = self.client.post(reverse('response', args=[6]), {'is_concluded': True, 'data': ''})
        self.assertEqual(r.status_code, 400)

        r = self.client.post(reverse('response', args=[6]), {'is_concluded': True, 'data': 'a'})
        self.assertEqual(r.status_code, 200)

        r = self.client.get(reverse('response', args=[6]))
        self.assertEqual(r.data[0]['text'], 'a')

        # Send file
        UserTask.objects.filter(id=6).update(is_concluded=None)
        Submission.objects.filter(id=11).update(type='f')

        obj = {
            'is_concluded': True,
            'old_files': [],
            'new_files': [],
            'new_files_image': []
        }
        r = self.client.post(reverse('response', args=[6]), obj)
        self.assertEqual(r.status_code, 400)

        obj['new_files_image'].append(True)
        r = self.client.post(reverse('response', args=[6]), obj)

        obj['new_files'].append(SimpleUploadedFile('small.gif', SMALL_GIF, content_type='image/gif'))
        r = self.client.post(reverse('response', args=[6]), obj, format='multipart')
        self.assertEqual(r.status_code, 200)

        r = self.client.get(reverse('response', args=[6]))
        self.assertEqual(r.data[0]['file']['is_image'], True)

        url = reverse('pictures-categories')
        self.client.force_login(user=User.objects.get(email="h@h.com"))

        r = self.client.get(url, {'store': 1, 'initialDate': datetime.date.today(), 'finalDate': datetime.date.today()})
        self.assertEqual(r.data, [{'id': 1, 'title': 'c1'}])

        url = reverse('pictures')

        r = self.client.get(url, {'brand': 1, 'store': 1, 'initialDate': datetime.date.today(), 'finalDate': datetime.date.today(), 'category': 1})
        self.assertEqual(r.data[0]['usertask_id'], 6)

        r = self.client.get(url, {'brand': 1, 'store': 10, 'initialDate': datetime.date.today(), 'finalDate': datetime.date.today(), 'category': 1})
        self.assertEqual(r.status_code, 400)

        r = self.client.get(url, {'brand': 1, 'store': 1, 'initialDate': datetime.date.today(), 'finalDate': datetime.date.today(), 'category': 10})
        self.assertEqual(r.status_code, 400)

        r = self.client.get(url, {'brand': 1, 'store': 1, 'initialDate': datetime.date.today(), 'finalDate': '2000-01-01', 'category': 1})
        self.assertEqual(r.status_code, 400)

    def test_reason_choice(self):
        # Get
        url = reverse('reason-choices')
        self.client.force_login(user=User.objects.get(email="h@h.com"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_task_detail(self):
        # Get
        url = reverse('task', args=[9])
        self.client.force_login(user=User.objects.get(email="e@e.com"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

        url = reverse('task', args=[6])
        self.client.force_login(user=User.objects.get(email="e@e.com"))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

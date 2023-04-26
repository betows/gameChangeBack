from django.core.management.base import BaseCommand
from tasks.models import Task


class Command(BaseCommand):
    cursor = None

    def add_arguments(self, parser):
        parser.add_argument('-store_from', type=int)
        parser.add_argument('-store_to', type=int)

    def handle(self, *args, **options):
        tasks = Task.objects.filter(store_id=options['store_from']).exclude(recurrence=None)
        for t in tasks:
            x = {
                'title': t.title,
                'description': t.description,
                'motivation': t.motivation,
                'recurrence': t.recurrence,
                'recurrence_index': t.recurrence_index,
                'advance_days': t.advance_days,
                'category': t.category,
                'group': t.group,
                'submission': t.submission
            }
            q_set = Task.objects.filter(**x, store_id=options['store_to'])
            if not q_set:
                Task.objects.create(**x, store_id=options['store_to'])

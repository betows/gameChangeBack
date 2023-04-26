from arccanet import serializers
from .models import Category, Group, Task, Submission, UserTask, PeriodicRelation, Response, Comment, Reason, ReasonChoice, Supporting
from .controllers import get_supporting
from authentication.serializers import UserSimplifiedSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "title"]


class SubmissionSerializer(serializers.ModelSerializer):
    def validate(self, obj):
        minimum = obj.get('min_objects')
        maximum = obj.get('max_objects')
        if obj.get('type') != 's':
            if minimum is None or maximum is None or minimum < 0 or maximum < 0 or maximum < minimum:
                raise serializers.ValidationError({'submission': 'Insira valores válidos de mínimo e máximo.'})
        return obj

    def create(self, validated_data):
        q_set = Submission.objects.filter(**validated_data)
        if not q_set.exists():
            return Submission.objects.create(**validated_data)
        return q_set[0]

    class Meta:
        model = Submission
        fields = '__all__'


class SupportingSerializer(serializers.ModelSerializer):
    data = serializers.ListField(child=serializers.FileField(), required=False, max_length=3, allow_null=True)
    MAX_FILE_SIZE = 41943040

    def validate(self, obj):
        if obj['type'] == 'f':
            obj['link'] = None
            if obj.get('data') is None:
                raise serializers.ValidationError({'data': 'Favor fornecer os arquivos.'})
            for sup in obj['data']:
                if sup.size > self.MAX_FILE_SIZE:
                    raise serializers.ValidationError({'support': 'O arquivo {} excedeu o tamanho máximo de {} bytes.'.format(sup, self.MAX_FILE_SIZE)})
        else:
            obj['data'] = None
            if obj.get('link') is None:
                raise serializers.ValidationError({'link': 'Favor fornecer o link.'})
        return obj

    def create(self, validated_data):
        if validated_data['type'] != 'f':
            return Supporting.objects.create(**validated_data)
        else:
            for sup in validated_data['data']:
                ret = Supporting.objects.create(data=sup, type=validated_data['type'], task=validated_data['task'])
            return ret

    class Meta:
        model = Supporting
        fields = ['data', 'link', 'type']


class RoutineSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    supporting = SupportingSerializer(write_only=True, required=False)
    supporting_changed = serializers.BooleanField(default=False, write_only=True)

    def validate(self, obj):
        if not self.context['request'].user.store.filter(id=obj['store'].id).exists():
            raise serializers.ValidationError({'store': 'Não encontrada.'})
        brand = obj['store'].brand.id
        if obj.get('category') is not None and obj.get('category').brand_id != brand:
            raise serializers.ValidationError({'category': 'Não encontrada.'})
        if obj.get('group') is not None and obj.get('group').brand_id != brand:
            raise serializers.ValidationError({'group': 'Não encontrado.'})
        if obj.get('recurrence') is None:
            raise serializers.ValidationError({'recurrence': 'Não pode ser nula.'})
        if obj.get('advance_days') is None or obj['advance_days'] < 0:
            raise serializers.ValidationError({'advance_day': 'Não pode ser nulo.'})
        if obj.get('suggested_time') is None:
            raise serializers.ValidationError({'suggested_time': 'Não pode ser nulo.'})
        if obj['recurrence'] == 'd':
            obj['recurrence_index'] = None
        elif obj.get('recurrence_index') is None or \
                (obj['recurrence'] == 'w' and (obj['recurrence_index'] < 0 or obj['recurrence_index'] > 6)) or \
                (obj['recurrence'] == 'm' and (obj['recurrence_index'] < 1 or obj['recurrence_index'] > 31)):
            raise serializers.ValidationError({'recurrence_index': 'Não pode ser nulo.'})
        return obj

    def create(self, validated_data):
        validated_data.pop('supporting_changed')
        sub = self['submission'].create(validated_data.pop('submission'))
        t = Task.objects.create(**validated_data, submission=sub)
        if 'supporting' in validated_data:
            validated_data['supporting']['task'] = t
            self['supporting'].create(validated_data['supporting'])
        return t

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title')
        instance.description = validated_data.get('description')
        instance.motivation = validated_data.get('motivation')
        instance.category = validated_data.get('category')
        instance.group = validated_data.get('group')
        instance.recurrence = validated_data.get('recurrence')
        instance.recurrence_index = validated_data.get('recurrence_index')
        instance.advance_days = validated_data.get('advance_days')
        instance.suggested_time = validated_data.get('suggested_time')
        old_sub = instance.submission
        instance.submission = self['submission'].create(validated_data['submission'])
        instance.save()
        if instance.submission.id != old_sub.id and not Task.objects.filter(submission=old_sub).exists():
            old_sub.delete()
        if validated_data['supporting_changed'] is True:
            Supporting.objects.filter(task=instance).delete()
            supporting = validated_data.get('supporting')
            if supporting is not None:
                validated_data['supporting']['task'] = instance
                self['supporting'].create(validated_data['supporting'])

    def to_representation(self, instance):
        representation = super(serializers.ModelSerializer, self).to_representation(instance)
        representation['supporting'] = get_supporting(instance)
        return representation

    class Meta:
        model = Task
        fields = ['title', 'description', 'motivation', 'store', 'category', 'group', 'submission', 'recurrence', 'recurrence_index', 'advance_days',
                  'suggested_time', 'supporting', 'supporting_changed']


class TaskSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer()
    supporting = SupportingSerializer(write_only=True, required=False)
    supporting_changed = serializers.BooleanField(default=False, write_only=True)

    def validate(self, obj):
        cat = obj.get('category')
        if cat and cat.brand_id != obj.get('store').brand_id:
            raise serializers.ValidationError({'category': 'Categoria inválida.'})
        return obj

    def create(self, validated_data):
        validated_data.pop('supporting_changed')
        sub = self['submission'].create(validated_data.pop('submission'))
        t = Task.objects.create(**validated_data, submission=sub)
        if 'supporting' in validated_data:
            validated_data['supporting']['task'] = t
            self['supporting'].create(validated_data['supporting'])
        return t

    def to_representation(self, instance):
        representation = super(serializers.ModelSerializer, self).to_representation(instance)
        representation["supporting"] = get_supporting(instance)
        return representation

    class Meta:
        model = Task
        fields = ['title', 'description', 'store', 'category', 'submission', 'motivation', 'suggested_time', 'supporting', 'supporting_changed']


class UserTaskSerializer(serializers.ModelSerializer):
    task = TaskSerializer()

    def validate(self, obj):
        u = self.context['request'].user
        req_u = obj.get('user')
        store = obj.get('task').get('store')
        if not (store.is_active and u.store.filter(id=store.id).exists() and req_u.store.filter(id=store.id).exists()):
            raise serializers.ValidationError({'user': 'Usuário não encontrado.'})
        return obj

    def create(self, validated_data):
        task = self['task'].create(validated_data.pop('task'))
        return UserTask.objects.create(**validated_data, task=task)

    def update(self, instance, validated_data):
        instance.user = validated_data.get('user')
        instance.deadline = validated_data.get('deadline')
        instance.is_active = validated_data.get('is_active', True)
        task = instance.task
        task.category = validated_data['task'].get('category')
        task.motivation = validated_data['task'].get('motivation')
        task.suggested_time = validated_data['task'].get('suggested_time')
        task.description = validated_data['task'].get('description')
        task.title = validated_data['task'].get('title')
        old_sub = task.submission
        task.submission = self['task']['submission'].create(validated_data['task']['submission'])
        task.save()
        instance.save()
        if task.submission.id != old_sub.id and not Task.objects.filter(submission=old_sub).exists():
            old_sub.delete()
        if validated_data['task']['supporting_changed'] is True:
            Supporting.objects.filter(task=instance.task).delete()
            supporting = validated_data['task'].get('supporting')
            if supporting is not None:
                validated_data['task']['supporting']['task'] = instance.task
                self['task']['supporting'].create(validated_data['task']['supporting'])

    class Meta:
        model = UserTask
        fields = ["id", "is_active", "task", "user", "deadline"]


class PeriodicRelationSerializer(serializers.ModelSerializer):
    def validate(self, obj):
        if not obj['user'].store.filter(id=self.context['routine']['store'].id).exists() or not obj['user'].is_active:
            raise serializers.ValidationError({'user': 'Não encontrado.'})
        return obj

    def create(self, validated_data):
        q_set = PeriodicRelation.objects.filter(task=validated_data['task'], user=validated_data['user'])
        if not q_set.exists():
            return PeriodicRelation.objects.create(**validated_data)
        q_set.update(**validated_data)
        return q_set[0]

    class Meta:
        model = PeriodicRelation
        fields = ["user", "obs", "priority"]


class ResponseSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    @staticmethod
    def get_file(obj):
        try:
            return {'url': obj.file.url, 'size': obj.file.size, 'id': obj.id, 'is_image': obj.is_image}
        except ValueError:
            return None

    class Meta:
        model = Response
        fields = ["file", "text"]


class CommentSerializer(serializers.ModelSerializer):
    user = UserSimplifiedSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "user", "content", "created_at"]


class ReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reason
        fields = ["reason_choice", "description"]


class ReasonChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReasonChoice
        fields = ["id", "type", "description"]

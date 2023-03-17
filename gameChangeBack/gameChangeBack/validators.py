from channels.models import Channel
from products.models import ItemCategory, ChoiceCategory, Item, Choice
from brands.models import SubBrand
from tasks.models import Category as TaskCategory
from arccanet import general
from arccanet import serializers


def validate_brand(user, brand):
    store_matching = user.store.filter(brand=brand, is_active=True)
    if not store_matching.exists():
        raise serializers.ValidationError({"brand": "Marca não encontrada."})


def validate_channels(channels, brand):
    channels_matching = Channel.objects.filter(id__in=channels, brand=brand)
    if not channels_matching.count() == len(channels):
        raise serializers.ValidationError({'channel': 'Algum canal não foi encontrado.'})


def validate_dates(initial, final, max_days=None, aggregation_period=None):
    date_diff = (final - initial).days
    aggregation_data = None
    if aggregation_period is not None:
        aggregation_data = general.AggregationPeriod(aggregation_period)
        date_diff /= aggregation_data.approximate_days
    if date_diff < 0 or (max_days is not None and date_diff > max_days):
        raise serializers.ValidationError({"initialDate": "Datas inválidas."})
    return aggregation_data


def validate_product_choice(choice, brand):
    if not Choice.objects.filter(code=choice, brand=brand).exists():
        raise serializers.ValidationError({'choice': 'Escolha não foi encontrada.'})


def validate_product_choice_category(choice_category, brand):
    if not ChoiceCategory.objects.filter(id=choice_category, brand=brand).exists():
        raise serializers.ValidationError({'choiceCategory': 'Alguma categoria de escolha não foi encontrada.'})


def validate_product_item(item, brand):
    if not Item.objects.filter(id=item, brand=brand).exists():
        raise serializers.ValidationError({'item': 'Item não foi encontrado.'})


def validate_product_item_categories(item_categories, brand):
    categories_matching = ItemCategory.objects.filter(id__in=item_categories, brand=brand)
    if not categories_matching.count() == len(item_categories):
        raise serializers.ValidationError({'itemCategory': 'Alguma categoria de item não foi encontrada.'})


def validate_product_item_category(item_category, brand):
    categories_matching = ItemCategory.objects.filter(id=item_category, brand=brand)
    if not categories_matching.exists():
        raise serializers.ValidationError({'itemCategory': 'Alguma categoria de item não foi encontrada.'})


def validate_store(user, store, brand=None):
    store_matching = user.store.filter(id=store, is_active=True)
    if brand is not None:
        store_matching = store_matching.filter(brand=brand)
    if not store_matching.exists():
        raise serializers.ValidationError({"store": "Loja não encontrada."})
    return store_matching[0]


def validate_stores(user, stores, brand, allow_holding=False):
    stores_matching = user.store.filter(id__in=stores, brand_id=brand)
    if not allow_holding:
        stores_matching = stores_matching.filter(is_holding=False)
    if not stores_matching.count() == len(stores):
        raise serializers.ValidationError({'store': 'Alguma loja não foi encontrada.'})


def validate_sub_brand(sub_brand, brand):
    if sub_brand is not None and not SubBrand.objects.filter(id=sub_brand, brand=brand).exists():
        raise serializers.ValidationError({'subBrand': 'Sub marca inválida.'})


def validate_task_categories(categories, brand):
    if not TaskCategory.objects.filter(id__in=categories, brand=brand).count() == len(categories):
        raise serializers.ValidationError({"category": "Alguma categoria não foi encontrada."})

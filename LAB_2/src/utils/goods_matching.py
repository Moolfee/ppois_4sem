from src.models.filters import GoodsFilterCriteria
from src.models.goods import Goods


def goods_matches(goods: Goods, criteria: GoodsFilterCriteria) -> bool:
    normalized = criteria.normalized()

    if normalized.goods_name:
        if normalized.goods_name.casefold() not in goods.goods_name.casefold():
            return False

    if normalized.quantity_in_stock is not None:
        if goods.quantity_in_stock != normalized.quantity_in_stock:
            return False

    if normalized.manufacturer_name:
        if normalized.manufacturer_name.casefold() not in goods.manufacturer_name.casefold():
            return False

    if normalized.manufacturer_tin:
        if goods.manufacturer_tin_text != normalized.manufacturer_tin:
            return False

    if normalized.warehouse_addres:
        if normalized.warehouse_addres.casefold() not in goods.warehouse_addres.casefold():
            return False

    return True

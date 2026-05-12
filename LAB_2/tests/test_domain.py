from __future__ import annotations

import pytest

from src.db.in_memory_database import InMemoryGoodsDatabase
from src.fetch.goods_fetch_service import GoodsFetchService
from src.models.filters import GoodsFilterCriteria
from src.models.goods import Goods, GoodsValidationError
from src.models.pagination import PageRequest, PageResult
from src.repo.goods_repository import GoodsRepository
from src.utils.goods_matching import goods_matches


def test_goods_normalizes_fields_and_formats_values() -> None:
    goods = Goods(
        goods_name="  Принтер  ",
        manufacturer_name="  БелЭлектроСнаб ",
        manufacturer_tin=123456789,
        quantity_in_stock=0,
        warehouse_addres="  Минск, Склад 1  ",
    )

    assert goods.goods_name == "Принтер"
    assert goods.manufacturer_name == "БелЭлектроСнаб"
    assert goods.warehouse_addres == "Минск, Склад 1"
    assert goods.manufacturer_tin_text == "123456789"
    assert goods.quantity_display == "нет на складе"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "goods_name": " ",
                "manufacturer_name": "БелЭлектроСнаб",
                "manufacturer_tin": 123456789,
                "quantity_in_stock": 1,
                "warehouse_addres": "Минск",
            },
            "Название товара не может быть пустым.",
        ),
        (
            {
                "goods_name": "Принтер",
                "manufacturer_name": " ",
                "manufacturer_tin": 123456789,
                "quantity_in_stock": 1,
                "warehouse_addres": "Минск",
            },
            "Название производителя не может быть пустым.",
        ),
        (
            {
                "goods_name": "Принтер",
                "manufacturer_name": "БелЭлектроСнаб",
                "manufacturer_tin": 1234,
                "quantity_in_stock": 1,
                "warehouse_addres": "Минск",
            },
            "УНП производителя должен состоять ровно из 9 цифр.",
        ),
        (
            {
                "goods_name": "Принтер",
                "manufacturer_name": "БелЭлектроСнаб",
                "manufacturer_tin": 123456789,
                "quantity_in_stock": -1,
                "warehouse_addres": "Минск",
            },
            "Количество на складе не может быть отрицательным.",
        ),
        (
            {
                "goods_name": "Принтер",
                "manufacturer_name": "БелЭлектроСнаб",
                "manufacturer_tin": 123456789,
                "quantity_in_stock": 1,
                "warehouse_addres": " ",
            },
            "Адрес склада не может быть пустым.",
        ),
    ],
)
def test_goods_validation_errors(payload: dict[str, object], message: str) -> None:
    with pytest.raises(GoodsValidationError, match=message):
        Goods(**payload)


def test_filter_criteria_normalizes_and_detects_active_filters() -> None:
    criteria = GoodsFilterCriteria(
        goods_name="  Прин ",
        quantity_in_stock=5,
        manufacturer_name="  Электро  ",
        manufacturer_tin=" 123456789 ",
        warehouse_addres=" Минск ",
    )

    normalized = criteria.normalized()

    assert normalized.goods_name == "Прин"
    assert normalized.manufacturer_name == "Электро"
    assert normalized.manufacturer_tin == "123456789"
    assert normalized.warehouse_addres == "Минск"
    assert normalized.has_active_filters() is True
    assert GoodsFilterCriteria().has_active_filters() is False


def test_goods_matches_checks_all_filter_fields(sample_goods: Goods) -> None:
    assert goods_matches(sample_goods, GoodsFilterCriteria(goods_name="ринт"))
    assert goods_matches(sample_goods, GoodsFilterCriteria(quantity_in_stock=15))
    assert goods_matches(sample_goods, GoodsFilterCriteria(manufacturer_name="электро"))
    assert goods_matches(sample_goods, GoodsFilterCriteria(manufacturer_tin="123456789"))
    assert goods_matches(sample_goods, GoodsFilterCriteria(warehouse_addres="склад 1"))

    assert not goods_matches(sample_goods, GoodsFilterCriteria(goods_name="сканер"))
    assert not goods_matches(sample_goods, GoodsFilterCriteria(quantity_in_stock=10))
    assert not goods_matches(sample_goods, GoodsFilterCriteria(manufacturer_name="пром"))
    assert not goods_matches(sample_goods, GoodsFilterCriteria(manufacturer_tin="000000000"))
    assert not goods_matches(sample_goods, GoodsFilterCriteria(warehouse_addres="гомель"))


def test_page_result_properties() -> None:
    empty_page = PageResult(items=[], page=1, page_size=10, total_items=0)
    filled_page = PageResult(items=[1, 2], page=2, page_size=2, total_items=5)

    assert empty_page.total_pages == 1
    assert empty_page.shown_items == 0
    assert filled_page.total_pages == 3
    assert filled_page.shown_items == 2


def test_in_memory_database_transaction_rolls_back(sample_goods: Goods) -> None:
    database = InMemoryGoodsDatabase()
    database.write_all([sample_goods])

    with pytest.raises(RuntimeError, match="boom"):
        with database.transaction():
            database.write_all([])
            raise RuntimeError("boom")

    assert database.read_all() == [sample_goods]


def test_repository_crud_and_remove_matching(more_goods: list[Goods], sample_goods: Goods) -> None:
    repository = GoodsRepository(InMemoryGoodsDatabase())

    repository.add(sample_goods)
    repository.add_many(more_goods[1:])

    assert repository.count() == 3
    assert repository.list_all()[0] == sample_goods

    deleted_count = repository.remove_matching(GoodsFilterCriteria(manufacturer_name="электро"))
    assert deleted_count == 2
    assert repository.count() == 1

    repository.replace_all(more_goods)
    assert repository.list_all() == more_goods


def test_fetch_service_filters_and_clamps_page_bounds(more_goods: list[Goods]) -> None:
    repository = GoodsRepository(InMemoryGoodsDatabase())
    repository.replace_all(more_goods)
    service = GoodsFetchService(repository)

    filtered_page = service.fetch_page(
        criteria=GoodsFilterCriteria(manufacturer_name="бел"),
        page_request=PageRequest(page=5, page_size=1),
    )
    zero_page_size = service.fetch_page(
        criteria=None,
        page_request=PageRequest(page=0, page_size=0),
    )

    assert [goods.goods_name for goods in filtered_page.items] == ["Сканер"]
    assert filtered_page.page == 2
    assert filtered_page.page_size == 1
    assert filtered_page.total_items == 2

    assert zero_page_size.page == 1
    assert zero_page_size.page_size == 1
    assert zero_page_size.total_items == 3

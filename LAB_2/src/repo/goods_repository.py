from collections.abc import Iterator

from src.db.in_memory_database import InMemoryGoodsDatabase
from src.models.filters import GoodsFilterCriteria
from src.models.goods import Goods
from src.utils.goods_matching import goods_matches


class GoodsRepository:
    def __init__(self, database: InMemoryGoodsDatabase) -> None:
        self._database = database

    def transaction(self) -> Iterator[None]:
        return self._database.transaction()

    def add(self, goods: Goods) -> None:
        records = self._database.read_all()
        records.append(goods)
        self._database.write_all(records)

    def add_many(self, goods_list: list[Goods]) -> None:
        records = self._database.read_all()
        records.extend(goods_list)
        self._database.write_all(records)

    def replace_all(self, goods_list: list[Goods]) -> None:
        self._database.write_all(list(goods_list))

    def list_all(self) -> list[Goods]:
        return self._database.read_all()

    def count(self) -> int:
        return len(self._database.read_all())

    def remove_matching(self, criteria: GoodsFilterCriteria) -> int:
        normalized = criteria.normalized()
        records = self._database.read_all()
        remaining_records = [record for record in records if not goods_matches(record, normalized)]
        deleted_count = len(records) - len(remaining_records)
        self._database.write_all(remaining_records)
        return deleted_count

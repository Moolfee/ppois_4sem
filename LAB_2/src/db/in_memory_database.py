from collections.abc import Iterator
from contextlib import contextmanager

from src.models.goods import Goods


class InMemoryGoodsDatabase:
    def __init__(self) -> None:
        self._records: list[Goods] = []

    @contextmanager
    def transaction(self) -> Iterator[None]:
        snapshot = list(self._records)
        try:
            yield
        except Exception:
            self._records = snapshot
            raise

    def read_all(self) -> list[Goods]:
        return list(self._records)

    def write_all(self, goods_list: list[Goods]) -> None:
        self._records = list(goods_list)

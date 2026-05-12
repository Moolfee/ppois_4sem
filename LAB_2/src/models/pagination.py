from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class PageRequest:
    page: int = 1
    page_size: int = 10


@dataclass(slots=True)
class PageResult(Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total_items: int

    @property
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 1
        return ceil(self.total_items / self.page_size)

    @property
    def shown_items(self) -> int:
        return len(self.items)

from src.models.filters import GoodsFilterCriteria
from src.models.goods import Goods
from src.models.pagination import PageRequest, PageResult
from src.repo.goods_repository import GoodsRepository
from src.utils.goods_matching import goods_matches


class GoodsFetchService:
    def __init__(self, repository: GoodsRepository) -> None:
        self._repository = repository

    def fetch_page(
        self,
        criteria: GoodsFilterCriteria | None,
        page_request: PageRequest,
    ) -> PageResult[Goods]:
        records = self._repository.list_all()

        if criteria is not None:
            normalized = criteria.normalized()
            records = [record for record in records if goods_matches(record, normalized)]

        total_items = len(records)
        page_size = max(1, page_request.page_size)
        total_pages = 1 if total_items == 0 else ((total_items - 1) // page_size) + 1
        page = min(max(1, page_request.page), total_pages)

        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        return PageResult(
            items=records[start_index:end_index],
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

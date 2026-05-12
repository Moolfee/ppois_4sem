from dataclasses import dataclass


@dataclass(slots=True)
class GoodsFilterCriteria:
    goods_name: str = ""
    quantity_in_stock: int | None = None
    manufacturer_name: str = ""
    manufacturer_tin: str = ""
    warehouse_addres: str = ""

    def normalized(self) -> "GoodsFilterCriteria":
        return GoodsFilterCriteria(
            goods_name=self.goods_name.strip(),
            quantity_in_stock=self.quantity_in_stock,
            manufacturer_name=self.manufacturer_name.strip(),
            manufacturer_tin=self.manufacturer_tin.strip(),
            warehouse_addres=self.warehouse_addres.strip(),
        )

    def has_active_filters(self) -> bool:
        normalized = self.normalized()
        return any(
            [
                bool(normalized.goods_name),
                normalized.quantity_in_stock is not None,
                bool(normalized.manufacturer_name),
                bool(normalized.manufacturer_tin),
                bool(normalized.warehouse_addres),
            ]
        )

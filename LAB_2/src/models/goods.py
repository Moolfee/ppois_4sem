from dataclasses import dataclass


class GoodsValidationError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class Goods:
    goods_name: str
    manufacturer_name: str
    manufacturer_tin: int
    quantity_in_stock: int
    warehouse_addres: str

    def __post_init__(self) -> None:
        normalized_goods_name = self.goods_name.strip()
        normalized_manufacturer_name = self.manufacturer_name.strip()
        normalized_warehouse = self.warehouse_addres.strip()
        tin_text = str(self.manufacturer_tin)

        if not normalized_goods_name:
            raise GoodsValidationError("Название товара не может быть пустым.")
        if not normalized_manufacturer_name:
            raise GoodsValidationError("Название производителя не может быть пустым.")
        if not tin_text.isdigit() or len(tin_text) != 9:
            raise GoodsValidationError("УНП производителя должен состоять ровно из 9 цифр.")
        if self.quantity_in_stock < 0:
            raise GoodsValidationError("Количество на складе не может быть отрицательным.")
        if not normalized_warehouse:
            raise GoodsValidationError("Адрес склада не может быть пустым.")

        object.__setattr__(self, "goods_name", normalized_goods_name)
        object.__setattr__(self, "manufacturer_name", normalized_manufacturer_name)
        object.__setattr__(self, "warehouse_addres", normalized_warehouse)

    @property
    def manufacturer_tin_text(self) -> str:
        return f"{self.manufacturer_tin:09d}"

    @property
    def quantity_display(self) -> str:
        if self.quantity_in_stock == 0:
            return "нет на складе"
        return str(self.quantity_in_stock)

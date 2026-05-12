from PySide6.QtGui import QStandardItem, QStandardItemModel

from src.models.goods import Goods


class GoodsTreeModel(QStandardItemModel):
    HEADERS = [
        "Поле",
        "Значение",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setHorizontalHeaderLabels(self.HEADERS)

    def update_records(self, records: list[Goods]) -> None:
        self.clear()
        self.setHorizontalHeaderLabels(self.HEADERS)

        for index, goods in enumerate(records, start=1):
            parent_row = [
                QStandardItem(f"Запись {index}: {goods.goods_name}"),
                QStandardItem(goods.manufacturer_name),
            ]

            for item in parent_row:
                item.setEditable(False)

            field_pairs = [
                ("Название товара", goods.goods_name),
                ("Название производителя", goods.manufacturer_name),
                ("УНП производителя", goods.manufacturer_tin_text),
                ("Количество на складе", goods.quantity_display),
                ("Адрес склада", goods.warehouse_addres),
            ]

            for key, value in field_pairs:
                child_row = [
                    QStandardItem(key),
                    QStandardItem(value),
                ]
                for child in child_row:
                    child.setEditable(False)
                parent_row[0].appendRow(child_row)

            self.appendRow(parent_row)

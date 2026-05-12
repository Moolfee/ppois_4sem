from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from src.models.goods import Goods


class GoodsTableModel(QAbstractTableModel):
    HEADERS = [
        "Название товара",
        "Название производителя",
        "УНП производителя",
        "Количество на складе",
        "Адрес склада",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._records: list[Goods] = []

    def update_records(self, records: list[Goods]) -> None:
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._records)):
            return None

        goods = self._records[index.row()]

        if role == Qt.DisplayRole:
            row_values = [
                goods.goods_name,
                goods.manufacturer_name,
                goods.manufacturer_tin_text,
                goods.quantity_display,
                goods.warehouse_addres,
            ]
            return row_values[index.column()]

        if role == Qt.TextAlignmentRole:
            if index.column() in {2, 3}:
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def headerData(self, section: int, orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

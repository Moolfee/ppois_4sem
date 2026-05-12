from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.filters import GoodsFilterCriteria


class GoodsFilterForm(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._tin_validator = QRegularExpressionValidator(QRegularExpression(r"\d{0,9}"), self)
        self._non_negative_int_validator = QIntValidator(0, 1_000_000_000, self)

        self.goods_name_edit = QLineEdit()
        self.goods_name_edit.setPlaceholderText("Например: Принтер")
        self.quantity_edit = QLineEdit()
        self.quantity_edit.setValidator(self._non_negative_int_validator)
        self.quantity_edit.setPlaceholderText("Например: 15")
        self.manufacturer_name_edit = QLineEdit()
        self.manufacturer_name_edit.setPlaceholderText("Например: БелЭлектроСнаб")
        self.manufacturer_tin_edit = QLineEdit()
        self.manufacturer_tin_edit.setValidator(self._tin_validator)
        self.manufacturer_tin_edit.setPlaceholderText("9 цифр")
        self.warehouse_edit = QLineEdit()
        self.warehouse_edit.setPlaceholderText("Например: Минск")

        form_layout = QFormLayout()
        form_layout.addRow("Название товара:", self.goods_name_edit)
        form_layout.addRow("Количество на складе:", self.quantity_edit)
        form_layout.addRow("Название производителя:", self.manufacturer_name_edit)
        form_layout.addRow("УНП производителя:", self.manufacturer_tin_edit)
        form_layout.addRow("Адрес склада:", self.warehouse_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)

    def build_criteria(self) -> GoodsFilterCriteria:
        goods_name_text = self.goods_name_edit.text().strip()
        quantity_text = self.quantity_edit.text().strip()
        manufacturer_name_text = self.manufacturer_name_edit.text().strip()
        manufacturer_tin_text = self.manufacturer_tin_edit.text().strip()

        if goods_name_text and quantity_text:
            raise ValueError(
                
            )

        if manufacturer_name_text and manufacturer_tin_text:
            raise ValueError(
                
            )

        if manufacturer_tin_text and len(manufacturer_tin_text) != 9:
            raise ValueError("УНП производителя в фильтре должен состоять ровно из 9 цифр.")

        return GoodsFilterCriteria(
            goods_name=goods_name_text,
            quantity_in_stock=int(quantity_text) if quantity_text else None,
            manufacturer_name=manufacturer_name_text,
            manufacturer_tin=manufacturer_tin_text,
            warehouse_addres=self.warehouse_edit.text(),
        )

    def clear(self) -> None:
        self.goods_name_edit.clear()
        self.quantity_edit.clear()
        self.manufacturer_name_edit.clear()
        self.manufacturer_tin_edit.clear()
        self.warehouse_edit.clear()

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from src.models.goods import Goods, GoodsValidationError


class AddGoodsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить товар")
        self.resize(460, 240)

        tin_validator = QRegularExpressionValidator(QRegularExpression(r"\d{0,9}"), self)

        self.goods_name_edit = QLineEdit()
        self.manufacturer_name_edit = QLineEdit()
        self.manufacturer_tin_edit = QLineEdit()
        self.manufacturer_tin_edit.setValidator(tin_validator)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000_000)
        self.warehouse_edit = QLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("Название товара:", self.goods_name_edit)
        form_layout.addRow("Название производителя:", self.manufacturer_name_edit)
        form_layout.addRow("УНП производителя:", self.manufacturer_tin_edit)
        form_layout.addRow("Количество на складе:", self.quantity_spin)
        form_layout.addRow("Адрес склада:", self.warehouse_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(buttons)

    def build_goods(self) -> Goods:
        tin_text = self.manufacturer_tin_edit.text().strip()
        if len(tin_text) != 9:
            raise GoodsValidationError("УНП производителя должен состоять ровно из 9 цифр.")

        return Goods(
            goods_name=self.goods_name_edit.text(),
            manufacturer_name=self.manufacturer_name_edit.text(),
            manufacturer_tin=int(tin_text),
            quantity_in_stock=self.quantity_spin.value(),
            warehouse_addres=self.warehouse_edit.text(),
        )

    def _handle_accept(self) -> None:
        try:
            self.build_goods()
        except GoodsValidationError as error:
            QMessageBox.warning(self, "Ошибка валидации", str(error))
            return
        self.accept()

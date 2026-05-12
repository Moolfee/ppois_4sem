from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from src.models.filters import GoodsFilterCriteria
from src.view.filter_form import GoodsFilterForm


class DeleteDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Удаление по условиям")
        self.resize(700, 420)

        self.filter_form = GoodsFilterForm(self)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Удалить")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.filter_form)
        layout.addWidget(buttons)

    def build_criteria(self) -> GoodsFilterCriteria:
        return self.filter_form.build_criteria()

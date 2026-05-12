from PySide6.QtCore import Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from src.models.filters import GoodsFilterCriteria
from src.models.pagination import PageResult
from src.models.goods import Goods
from src.view.filter_form import GoodsFilterForm
from src.view.goods_table_model import GoodsTableModel
from src.view.pagination_widget import PaginationWidget


class SearchDialog(QDialog):
    search_requested = Signal()
    reset_requested = Signal()
    page_requested = Signal(int)
    page_size_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Поиск товаров")
        self.resize(1100, 720)

        self.filter_form = GoodsFilterForm(self)
        self.table_model = GoodsTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setStretchLastSection(False)
        self._apply_header_widths()

        self.pagination_widget = PaginationWidget()

        self.search_button = QPushButton("Найти")
        self.reset_button = QPushButton("Сбросить")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.search_button)
        action_layout.addWidget(self.reset_button)
        action_layout.addStretch(1)
        action_layout.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(self.filter_form)
        layout.addLayout(action_layout)
        layout.addWidget(self.table_view)
        layout.addWidget(self.pagination_widget)

        self.search_button.clicked.connect(self.search_requested.emit)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        self.pagination_widget.page_requested.connect(self.page_requested.emit)
        self.pagination_widget.page_size_changed.connect(self.page_size_changed.emit)

    def build_criteria(self) -> GoodsFilterCriteria:
        return self.filter_form.build_criteria()

    def _apply_header_widths(self) -> None:
        font_metrics = QFontMetrics(self.table_view.horizontalHeader().font())
        for column, header_text in enumerate(self.table_model.HEADERS):
            width = font_metrics.horizontalAdvance(header_text) + 36
            self.table_view.setColumnWidth(column, width)

    def reset_filters(self) -> None:
        self.filter_form.clear()

    def set_results(self, page_result: PageResult[Goods]) -> None:
        self.table_model.update_records(page_result.items)
        self.pagination_widget.update_state(
            page=page_result.page,
            total_pages=page_result.total_pages,
            shown_items=page_result.shown_items,
            total_items=page_result.total_items,
        )

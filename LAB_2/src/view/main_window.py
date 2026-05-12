from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFontMetrics
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QTableView,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from src.models.goods import Goods
from src.models.pagination import PageResult
from src.view.goods_table_model import GoodsTableModel
from src.view.goods_tree_model import GoodsTreeModel
from src.view.pagination_widget import PaginationWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LAB_2 - Учёт товаров")
        self.resize(1280, 760)

        self.add_action = self._create_action("Добавить")
        self.search_action = self._create_action("Поиск")
        self.delete_action = self._create_action("Удаление по условиям")
        self.load_action = self._create_action("Загрузить из XML")
        self.save_action = self._create_action("Сохранить в XML")
        self.toggle_view_action = self._create_action("Переключить Таблица / Дерево")
        self.exit_action = self._create_action("Выход")

        self._create_menu()
        self._create_toolbar()

        self.table_model = GoodsTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setStretchLastSection(False)
        self._apply_header_widths(self.table_view, self.table_model.HEADERS)

        self.tree_model = GoodsTreeModel()
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.header().setStretchLastSection(False)
        self._apply_header_widths(self.tree_view, self.tree_model.HEADERS)

        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.table_view)
        self.view_stack.addWidget(self.tree_view)

        self.pagination_widget = PaginationWidget()

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.addWidget(self.view_stack)
        central_layout.addWidget(self.pagination_widget)
        self.setCentralWidget(central_widget)

        self.setStatusBar(QStatusBar())
        self.show_table_view()

    def _create_action(self, text: str):
        return QAction(text, self)

    def _apply_header_widths(self, view: QTableView | QTreeView, headers: list[str]) -> None:
        if isinstance(view, QTreeView):
            header = view.header()
        else:
            header = view.horizontalHeader()

        font_metrics = QFontMetrics(header.font())
        for column, header_text in enumerate(headers):
            width = font_metrics.horizontalAdvance(header_text) + 36
            view.setColumnWidth(column, width)

    def _create_menu(self) -> None:
        menu = self.menuBar().addMenu("Команды")
        for action in self._ordered_actions:
            menu.addAction(action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Главная панель")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        for action in self._ordered_actions:
            toolbar.addAction(action)

    @property
    def _ordered_actions(self):
        return [
            self.add_action,
            self.search_action,
            self.delete_action,
            self.load_action,
            self.save_action,
            self.toggle_view_action,
            self.exit_action,
        ]

    def set_page(self, page_result: PageResult[Goods]) -> None:
        self.table_model.update_records(page_result.items)
        self.tree_model.update_records(page_result.items)
        self.tree_view.expandAll()
        self.pagination_widget.update_state(
            page=page_result.page,
            total_pages=page_result.total_pages,
            shown_items=page_result.shown_items,
            total_items=page_result.total_items,
        )
        self.statusBar().showMessage(f"Всего записей в массиве: {page_result.total_items}")

    def show_table_view(self) -> None:
        self.view_stack.setCurrentWidget(self.table_view)

    def show_tree_view(self) -> None:
        self.view_stack.setCurrentWidget(self.tree_view)

    def is_tree_view_active(self) -> bool:
        return self.view_stack.currentWidget() is self.tree_view

    def show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str) -> None:
        QMessageBox.information(self, title, message)

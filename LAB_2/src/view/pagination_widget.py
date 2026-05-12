from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class PaginationWidget(QWidget):
    page_requested = Signal(int)
    page_size_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page = 1
        self._total_pages = 1

        self._first_button = QPushButton("1")
        self._prev_button = QPushButton("<<")
        self._next_button = QPushButton(">>")
        self._last_button = QPushButton("1")
        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["5", "10", "25", "50"])
        self._page_size_combo.setCurrentText("10")
        self._info_label = QLabel("Стр. 1 из 1")
        self._info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Страницы:"))
        layout.addWidget(self._first_button)
        layout.addWidget(self._prev_button)
        layout.addWidget(self._next_button)
        layout.addWidget(self._last_button)
        layout.addSpacing(16)
        layout.addWidget(QLabel("Размер страницы:"))
        layout.addWidget(self._page_size_combo)
        layout.addSpacing(16)
        layout.addWidget(self._info_label)

        self._first_button.clicked.connect(lambda: self.page_requested.emit(1))
        self._prev_button.clicked.connect(lambda: self.page_requested.emit(max(1, self._current_page - 1)))
        self._next_button.clicked.connect(
            lambda: self.page_requested.emit(min(self._total_pages, self._current_page + 1))
        )
        self._last_button.clicked.connect(lambda: self.page_requested.emit(self._total_pages))
        self._page_size_combo.currentTextChanged.connect(
            lambda text: self.page_size_changed.emit(int(text))
        )

        self._sync_buttons()

    @property
    def page_size(self) -> int:
        return int(self._page_size_combo.currentText())

    def set_page_size(self, page_size: int) -> None:
        self._page_size_combo.setCurrentText(str(page_size))

    def update_state(
        self,
        page: int,
        total_pages: int,
        shown_items: int,
        total_items: int,
    ) -> None:
        self._current_page = max(1, page)
        self._total_pages = max(1, total_pages)
        self._last_button.setText(str(self._total_pages))
        self._info_label.setText(f"Стр. {self._current_page} из {self._total_pages}")
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        has_previous = self._current_page > 1
        has_next = self._current_page < self._total_pages
        self._first_button.setEnabled(has_previous)
        self._prev_button.setEnabled(has_previous)
        self._next_button.setEnabled(has_next)
        self._last_button.setEnabled(has_next)

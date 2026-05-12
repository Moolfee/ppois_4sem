from __future__ import annotations

from PySide6.QtCore import Qt

from src.models.filters import GoodsFilterCriteria
from src.models.pagination import PageResult
from src.view.main_window import MainWindow
from src.view.search_dialog import SearchDialog


def test_main_window_sets_page_and_switches_views(qapp, monkeypatch, more_goods) -> None:
    window = MainWindow()
    page_result = PageResult(items=more_goods[:2], page=1, page_size=10, total_items=2)
    critical_calls: list[tuple[str, str]] = []
    info_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "src.view.main_window.QMessageBox.critical",
        lambda parent, title, message: critical_calls.append((title, message)),
    )
    monkeypatch.setattr(
        "src.view.main_window.QMessageBox.information",
        lambda parent, title, message: info_calls.append((title, message)),
    )

    window.set_page(page_result)
    window.show_tree_view()
    assert window.is_tree_view_active() is True
    window.show_table_view()
    window.show_error("Ошибка", "Не получилось")
    window.show_info("Готово", "Успех")

    assert window.is_tree_view_active() is False
    assert window.table_model.rowCount() == 2
    assert window.tree_model.rowCount() == 2
    assert window.statusBar().currentMessage() == "Всего записей в массиве: 2"
    assert critical_calls == [("Ошибка", "Не получилось")]
    assert info_calls == [("Готово", "Успех")]
    assert len(window._ordered_actions) == 7


def test_search_dialog_builds_results_and_forwards_signals(qapp, more_goods) -> None:
    dialog = SearchDialog()
    page_events: list[int] = []
    size_events: list[int] = []
    search_events: list[bool] = []
    reset_events: list[bool] = []

    dialog.page_requested.connect(page_events.append)
    dialog.page_size_changed.connect(size_events.append)
    dialog.search_requested.connect(lambda: search_events.append(True))
    dialog.reset_requested.connect(lambda: reset_events.append(True))

    dialog.filter_form.goods_name_edit.setText("Принтер")
    criteria = dialog.build_criteria()
    dialog.set_results(PageResult(items=more_goods[:1], page=1, page_size=10, total_items=1))

    dialog.search_button.click()
    dialog.reset_button.click()
    dialog.pagination_widget.update_state(page=1, total_pages=3, shown_items=1, total_items=3)
    dialog.pagination_widget._next_button.click()
    dialog.pagination_widget.set_page_size(25)
    dialog.reset_filters()

    assert isinstance(criteria, GoodsFilterCriteria)
    assert criteria.goods_name == "Принтер"
    assert dialog.table_model.rowCount() == 1
    assert dialog.pagination_widget._info_label.text() == "Стр. 1 из 3"
    assert search_events == [True]
    assert reset_events == [True]
    assert page_events == [2]
    assert size_events[-1] == 25
    assert dialog.filter_form.goods_name_edit.text() == ""

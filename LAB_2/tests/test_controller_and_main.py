from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from src.db.postgres_probe import PostgresConnectionError
from src.models.filters import GoodsFilterCriteria
from src.models.goods import Goods
from src.models.pagination import PageResult


class DummySignal:
    def __init__(self) -> None:
        self._callbacks: list = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class DummyAction:
    def __init__(self) -> None:
        self.triggered = DummySignal()


class DummyPaginationWidget:
    def __init__(self, page_size: int = 10) -> None:
        self.page_requested = DummySignal()
        self.page_size_changed = DummySignal()
        self.page_size = page_size
        self.set_page_size_calls: list[int] = []

    def set_page_size(self, page_size: int) -> None:
        self.page_size = page_size
        self.set_page_size_calls.append(page_size)


class DummyStatusBar:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def showMessage(self, message: str) -> None:
        self.messages.append(message)


class DummyMainWindow:
    def __init__(self) -> None:
        self.add_action = DummyAction()
        self.search_action = DummyAction()
        self.delete_action = DummyAction()
        self.load_action = DummyAction()
        self.save_action = DummyAction()
        self.toggle_view_action = DummyAction()
        self.exit_action = DummyAction()
        self.pagination_widget = DummyPaginationWidget()
        self._status_bar = DummyStatusBar()
        self._tree_active = False
        self.pages: list[PageResult] = []
        self.errors: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []
        self.show_calls = 0
        self.close_calls = 0

    def show(self) -> None:
        self.show_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def set_page(self, page_result: PageResult) -> None:
        self.pages.append(page_result)

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def show_info(self, title: str, message: str) -> None:
        self.infos.append((title, message))

    def is_tree_view_active(self) -> bool:
        return self._tree_active

    def show_table_view(self) -> None:
        self._tree_active = False

    def show_tree_view(self) -> None:
        self._tree_active = True

    def statusBar(self) -> DummyStatusBar:
        return self._status_bar


class ProbeOk:
    def check_connection(self) -> None:
        return None


class ProbeFails:
    def check_connection(self) -> None:
        raise PostgresConnectionError("dsn failed")


def build_controller(monkeypatch, probe_factory=ProbeOk):
    import src.controller.main_controller as main_controller

    monkeypatch.setattr(main_controller, "MainWindow", DummyMainWindow)
    monkeypatch.setattr(main_controller, "OptionalPostgresProbe", probe_factory)
    controller = main_controller.MainController()
    return controller, main_controller


def make_goods(index: int) -> Goods:
    return Goods(
        goods_name=f"Товар {index}",
        manufacturer_name=f"Производитель {index}",
        manufacturer_tin=123456780 + index,
        quantity_in_stock=index,
        warehouse_addres=f"Склад {index}",
    )


def test_main_controller_initializes_and_handles_probe_errors(monkeypatch) -> None:
    controller, _ = build_controller(monkeypatch, ProbeFails)

    assert controller._main_window.errors == [("Ошибка подключения к Postgres", "dsn failed")]
    assert controller._main_window.pages[-1].page == 1
    assert controller._main_window.pagination_widget.set_page_size_calls[-1] == 10


def test_main_controller_show_and_main_pagination_signals(monkeypatch) -> None:
    controller, _ = build_controller(monkeypatch)
    controller._repository.replace_all([make_goods(1), make_goods(2), make_goods(3)])

    controller.show()
    controller._main_window.pagination_widget.page_requested.emit(3)
    controller._main_window.pagination_widget.page_size_changed.emit(2)
    controller._main_window.exit_action.triggered.emit()

    assert controller._main_window.show_calls == 1
    assert controller._current_page == 1
    assert controller._page_size == 2
    assert controller._main_window.close_calls == 1


def test_open_add_dialog_cancel_build_error_and_success(monkeypatch) -> None:
    controller, main_controller = build_controller(monkeypatch)
    good = make_goods(1)

    class CancelDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, parent):
            self.parent = parent

        def exec(self) -> int:
            return 0

    monkeypatch.setattr(main_controller, "AddGoodsDialog", CancelDialog)
    controller._open_add_dialog()
    assert controller._repository.count() == 0

    class ErrorDialog(CancelDialog):
        def exec(self) -> int:
            return 1

        def build_goods(self):
            raise RuntimeError("invalid")

    monkeypatch.setattr(main_controller, "AddGoodsDialog", ErrorDialog)
    controller._open_add_dialog()
    assert controller._main_window.errors[-1] == ("Ошибка добавления", "invalid")

    class SuccessDialog(CancelDialog):
        def exec(self) -> int:
            return 1

        def build_goods(self):
            return good

    monkeypatch.setattr(main_controller, "AddGoodsDialog", SuccessDialog)
    controller._open_add_dialog()

    assert controller._repository.count() == 1
    assert controller._main_window.infos[-1] == ("Добавление", "Новая запись успешно добавлена.")


def test_open_search_dialog_success_and_validation_warning(monkeypatch) -> None:
    controller, main_controller = build_controller(monkeypatch)
    controller._repository.replace_all([make_goods(1), make_goods(2), make_goods(3)])
    warnings: list[tuple[object, str, str]] = []

    monkeypatch.setattr(
        main_controller.QMessageBox,
        "warning",
        lambda parent, title, message: warnings.append((parent, title, message)),
    )

    class SearchDialogOk:
        def __init__(self, parent):
            self.parent = parent
            self.pagination_widget = DummyPaginationWidget(page_size=2)
            self.search_requested = DummySignal()
            self.reset_requested = DummySignal()
            self.page_requested = DummySignal()
            self.page_size_changed = DummySignal()
            self.results: list[PageResult] = []
            self.reset_calls = 0

        def build_criteria(self):
            return GoodsFilterCriteria(goods_name="Товар")

        def set_results(self, page_result: PageResult) -> None:
            self.results.append(page_result)

        def reset_filters(self) -> None:
            self.reset_calls += 1

        def exec(self) -> int:
            self.search_requested.emit()
            self.page_requested.emit(2)
            self.page_size_changed.emit(1)
            self.reset_requested.emit()
            return 0

    created_dialogs: list[SearchDialogOk] = []

    def search_factory(parent):
        dialog = SearchDialogOk(parent)
        created_dialogs.append(dialog)
        return dialog

    monkeypatch.setattr(main_controller, "SearchDialog", search_factory)
    controller._open_search_dialog()

    dialog = created_dialogs[0]
    assert [result.page_size for result in dialog.results] == [2, 2, 2, 1, 1]
    assert dialog.reset_calls == 1
    assert warnings == []

    class SearchDialogInvalid(SearchDialogOk):
        def build_criteria(self):
            raise ValueError("bad filter")

    monkeypatch.setattr(main_controller, "SearchDialog", SearchDialogInvalid)
    controller._open_search_dialog()
    assert warnings[-1][1:] == ("Ошибка фильтра", "bad filter")


def test_search_helper_methods_update_search_state(monkeypatch) -> None:
    controller, _ = build_controller(monkeypatch)

    class Dialog:
        def __init__(self):
            self.reset_calls = 0

        def reset_filters(self) -> None:
            self.reset_calls += 1

    dialog = Dialog()
    state = {"page": 5, "page_size": 10, "criteria": "x"}
    calls: list[bool] = []

    controller._reset_search_dialog(dialog, state, lambda reset_page: calls.append(reset_page))
    controller._change_search_page(3, state, lambda reset_page: calls.append(reset_page))
    controller._change_search_page_size(25, state, lambda reset_page: calls.append(reset_page))

    assert dialog.reset_calls == 1
    assert state == {"page": 1, "page_size": 25, "criteria": None}
    assert calls == [True, False, True]


def test_open_delete_dialog_covers_all_branches(monkeypatch) -> None:
    controller, main_controller = build_controller(monkeypatch)
    controller._repository.replace_all([make_goods(1), make_goods(2)])
    warnings: list[tuple[object, str, str]] = []

    monkeypatch.setattr(
        main_controller.QMessageBox,
        "warning",
        lambda parent, title, message: warnings.append((parent, title, message)),
    )

    class BaseDeleteDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, parent):
            self.parent = parent

        def exec(self) -> int:
            return 1

    class InvalidDeleteDialog(BaseDeleteDialog):
        def build_criteria(self):
            raise ValueError("bad criteria")

    monkeypatch.setattr(main_controller, "DeleteDialog", InvalidDeleteDialog)
    controller._open_delete_dialog()
    assert warnings[-1][1:] == ("Ошибка фильтра", "bad criteria")

    class EmptyDeleteDialog(BaseDeleteDialog):
        def build_criteria(self):
            return GoodsFilterCriteria()

    monkeypatch.setattr(main_controller, "DeleteDialog", EmptyDeleteDialog)
    controller._open_delete_dialog()
    assert warnings[-1][1:] == (
        "Ошибка удаления",
        "Для удаления нужно указать хотя бы одно условие фильтрации.",
    )

    class RemoveDeleteDialog(BaseDeleteDialog):
        def build_criteria(self):
            return GoodsFilterCriteria(goods_name="Товар 1")

    monkeypatch.setattr(main_controller, "DeleteDialog", RemoveDeleteDialog)
    controller._open_delete_dialog()
    assert controller._main_window.infos[-1] == ("Удаление завершено", "Удалено записей: 1.")

    class NothingDeleteDialog(BaseDeleteDialog):
        def build_criteria(self):
            return GoodsFilterCriteria(goods_name="нет совпадений")

    monkeypatch.setattr(main_controller, "DeleteDialog", NothingDeleteDialog)
    controller._open_delete_dialog()
    assert controller._main_window.infos[-1] == ("Удаление завершено", "Ничего не найдено.")


def test_load_and_save_xml_cover_cancel_error_and_success(monkeypatch, tmp_path) -> None:
    controller, main_controller = build_controller(monkeypatch)
    controller._repository.replace_all([make_goods(1)])
    exported: list[tuple[str, list[Goods]]] = []

    monkeypatch.setattr(main_controller.QFileDialog, "getOpenFileName", lambda *args: ("", ""))
    controller._load_from_xml()

    monkeypatch.setattr(main_controller.QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    controller._save_to_xml()

    class FailingImporter:
        def import_from_file(self, path: str):
            raise RuntimeError("broken xml")

    controller._xml_importer = FailingImporter()
    monkeypatch.setattr(main_controller.QFileDialog, "getOpenFileName", lambda *args: ("input.xml", ""))
    controller._load_from_xml()
    assert controller._main_window.errors[-1] == ("Ошибка загрузки", "broken xml")

    class GoodImporter:
        def import_from_file(self, path: str):
            return [make_goods(5), make_goods(6)]

    controller._xml_importer = GoodImporter()
    controller._load_from_xml()
    assert controller._repository.count() == 2
    assert controller._main_window.infos[-1] == ("Загрузка завершена", "Загружено записей: 2.")

    class FailingExporter:
        def export_to_file(self, path: str, goods_list: list[Goods]) -> None:
            raise RuntimeError("write failed")

    controller._xml_exporter = FailingExporter()
    monkeypatch.setattr(main_controller.QFileDialog, "getSaveFileName", lambda *args: ("out", ""))
    controller._save_to_xml()
    assert controller._main_window.errors[-1] == ("Ошибка сохранения", "write failed")

    class GoodExporter:
        def export_to_file(self, path: str, goods_list: list[Goods]) -> None:
            exported.append((path, list(goods_list)))

    controller._xml_exporter = GoodExporter()
    controller._save_to_xml()
    assert exported == [("out.xml", controller._repository.list_all())]
    assert controller._main_window.infos[-1] == ("Сохранение завершено", "Файл сохранён: out.xml")


def test_toggle_view_mode_switches_between_table_and_tree(monkeypatch) -> None:
    controller, _ = build_controller(monkeypatch)

    controller._toggle_view_mode()
    controller._toggle_view_mode()

    assert controller._main_window.statusBar().messages == [
        "Активен режим дерева.",
        "Активен режим таблицы.",
    ]


def test_main_entry_run_constructs_app_and_controller(monkeypatch) -> None:
    import src.main as main_module

    events: dict[str, object] = {}

    class FakeApp:
        def __init__(self, argv):
            events["argv"] = argv

        def exec(self) -> int:
            events["exec_called"] = True
            return 42

    class FakeController:
        def show(self) -> None:
            events["show_called"] = True

    monkeypatch.setattr(main_module, "QApplication", FakeApp)
    monkeypatch.setattr(main_module, "MainController", FakeController)

    assert main_module.run() == 42
    assert events["show_called"] is True
    assert events["exec_called"] is True

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from src.db.in_memory_database import InMemoryGoodsDatabase
from src.db.postgres_probe import OptionalPostgresProbe, PostgresConnectionError
from src.fetch.goods_fetch_service import GoodsFetchService
from src.ingest.xml_goods_io import GoodsXmlDomExporter, GoodsXmlSaxImporter
from src.models.pagination import PageRequest
from src.repo.goods_repository import GoodsRepository
from src.view.add_goods_dialog import AddGoodsDialog
from src.view.delete_dialog import DeleteDialog
from src.view.main_window import MainWindow
from src.view.search_dialog import SearchDialog


class MainController:

    def __init__(self) -> None:
        self._database = InMemoryGoodsDatabase()
        self._repository = GoodsRepository(self._database)
        self._fetch_service = GoodsFetchService(self._repository)
        self._xml_exporter = GoodsXmlDomExporter()
        self._xml_importer = GoodsXmlSaxImporter()
        self._postgres_probe = OptionalPostgresProbe()

        self._main_window = MainWindow()
        self._current_page = 1
        self._page_size = 10

        self._connect_main_window()
        self._probe_optional_postgres()
        self._refresh_main_page()

    def show(self) -> None:
        self._main_window.show()

    def _connect_main_window(self) -> None:
        self._main_window.add_action.triggered.connect(self._open_add_dialog)
        self._main_window.search_action.triggered.connect(self._open_search_dialog)
        self._main_window.delete_action.triggered.connect(self._open_delete_dialog)
        self._main_window.load_action.triggered.connect(self._load_from_xml)
        self._main_window.save_action.triggered.connect(self._save_to_xml)
        self._main_window.toggle_view_action.triggered.connect(self._toggle_view_mode)
        self._main_window.exit_action.triggered.connect(self._main_window.close)
        self._main_window.pagination_widget.page_requested.connect(self._change_main_page)
        self._main_window.pagination_widget.page_size_changed.connect(self._change_main_page_size)

    def _probe_optional_postgres(self) -> None:
        try:
            self._postgres_probe.check_connection()
        except PostgresConnectionError as error:
            self._main_window.show_error("Ошибка подключения к Postgres", str(error))

    def _refresh_main_page(self) -> None:
        page_result = self._fetch_service.fetch_page(
            criteria=None,
            page_request=PageRequest(page=self._current_page, page_size=self._page_size),
        )
        self._current_page = page_result.page
        self._page_size = page_result.page_size
        self._main_window.pagination_widget.set_page_size(self._page_size)
        self._main_window.set_page(page_result)

    def _change_main_page(self, page: int) -> None:
        self._current_page = page
        self._refresh_main_page()

    def _change_main_page_size(self, page_size: int) -> None:
        self._page_size = page_size
        self._current_page = 1
        self._refresh_main_page()

    def _open_add_dialog(self) -> None:
        dialog = AddGoodsDialog(self._main_window)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        try:
            goods = dialog.build_goods()
        except Exception as error:
            self._main_window.show_error("Ошибка добавления", str(error))
            return

        with self._repository.transaction():
            self._repository.add(goods)

        self._current_page = 1
        self._refresh_main_page()
        self._main_window.show_info("Добавление", "Новая запись успешно добавлена.")

    def _open_search_dialog(self) -> None:
        dialog = SearchDialog(self._main_window)
        search_state = {
            "page": 1,
            "page_size": dialog.pagination_widget.page_size,
            "criteria": None,
        }

        def run_search(reset_page: bool) -> None:
            if reset_page:
                search_state["page"] = 1

            try:
                criteria = dialog.build_criteria()
            except ValueError as error:
                QMessageBox.warning(dialog, "Ошибка фильтра", str(error))
                return

            search_state["criteria"] = criteria
            page_result = self._fetch_service.fetch_page(
                criteria=criteria,
                page_request=PageRequest(
                    page=search_state["page"],
                    page_size=search_state["page_size"],
                ),
            )
            search_state["page"] = page_result.page
            dialog.pagination_widget.set_page_size(search_state["page_size"])
            dialog.set_results(page_result)

        dialog.search_requested.connect(lambda: run_search(True))
        dialog.reset_requested.connect(lambda: self._reset_search_dialog(dialog, search_state, run_search))
        dialog.page_requested.connect(lambda page: self._change_search_page(page, search_state, run_search))
        dialog.page_size_changed.connect(
            lambda page_size: self._change_search_page_size(page_size, search_state, run_search)
        )

        run_search(True)
        dialog.exec()

    def _reset_search_dialog(self, dialog: SearchDialog, search_state: dict, run_search) -> None:
        dialog.reset_filters()
        search_state["page"] = 1
        search_state["criteria"] = None
        run_search(True)

    def _change_search_page(self, page: int, search_state: dict, run_search) -> None:
        search_state["page"] = page
        run_search(False)

    def _change_search_page_size(self, page_size: int, search_state: dict, run_search) -> None:
        search_state["page_size"] = page_size
        search_state["page"] = 1
        run_search(True)

    def _open_delete_dialog(self) -> None:
        dialog = DeleteDialog(self._main_window)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        try:
            criteria = dialog.build_criteria()
        except ValueError as error:
            QMessageBox.warning(self._main_window, "Ошибка фильтра", str(error))
            return

        if not criteria.has_active_filters():
            QMessageBox.warning(
                self._main_window,
                "Ошибка удаления",
                "Для удаления нужно указать хотя бы одно условие фильтрации.",
            )
            return

        with self._repository.transaction():
            deleted_count = self._repository.remove_matching(criteria)

        self._current_page = 1
        self._refresh_main_page()

        if deleted_count:
            self._main_window.show_info(
                "Удаление завершено",
                f"Удалено записей: {deleted_count}.",
            )
        else:
            self._main_window.show_info("Удаление завершено", "Ничего не найдено.")

    def _load_from_xml(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self._main_window,
            "Загрузить XML",
            str(Path.cwd()),
            "XML files (*.xml)",
        )
        if not selected_path:
            return

        try:
            records = self._xml_importer.import_from_file(selected_path)
            with self._repository.transaction():
                self._repository.replace_all(records)
        except Exception as error:
            self._main_window.show_error("Ошибка загрузки", str(error))
            return

        self._current_page = 1
        self._refresh_main_page()
        self._main_window.show_info(
            "Загрузка завершена",
            f"Загружено записей: {len(records)}.",
        )

    def _save_to_xml(self) -> None:
        selected_path, _ = QFileDialog.getSaveFileName(
            self._main_window,
            "Сохранить XML",
            str(Path.cwd() / "goods_export.xml"),
            "XML files (*.xml)",
        )
        if not selected_path:
            return

        if not selected_path.lower().endswith(".xml"):
            selected_path = f"{selected_path}.xml"

        try:
            self._xml_exporter.export_to_file(selected_path, self._repository.list_all())
        except Exception as error:
            self._main_window.show_error("Ошибка сохранения", str(error))
            return

        self._main_window.show_info("Сохранение завершено", f"Файл сохранён: {selected_path}")

    def _toggle_view_mode(self) -> None:
        if self._main_window.is_tree_view_active():
            self._main_window.show_table_view()
            self._main_window.statusBar().showMessage("Активен режим таблицы.")
        else:
            self._main_window.show_tree_view()
            self._main_window.statusBar().showMessage("Активен режим дерева.")

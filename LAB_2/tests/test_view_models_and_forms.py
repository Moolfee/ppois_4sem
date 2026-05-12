from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from src.models.pagination import PageResult
from src.view.add_goods_dialog import AddGoodsDialog
from src.view.delete_dialog import DeleteDialog
from src.view.filter_form import GoodsFilterForm
from src.view.goods_table_model import GoodsTableModel
from src.view.goods_tree_model import GoodsTreeModel
from src.view.pagination_widget import PaginationWidget


def test_add_goods_dialog_builds_goods_and_validates(qapp, monkeypatch) -> None:
    dialog = AddGoodsDialog()
    dialog.goods_name_edit.setText(" Принтер ")
    dialog.manufacturer_name_edit.setText(" БелЭлектроСнаб ")
    dialog.manufacturer_tin_edit.setText("123456789")
    dialog.quantity_spin.setValue(7)
    dialog.warehouse_edit.setText(" Минск ")

    accepted: list[bool] = []
    monkeypatch.setattr(dialog, "accept", lambda: accepted.append(True))

    goods = dialog.build_goods()
    dialog._handle_accept()

    assert goods.goods_name == "Принтер"
    assert goods.manufacturer_name == "БелЭлектроСнаб"
    assert goods.quantity_in_stock == 7
    assert accepted == [True]


def test_add_goods_dialog_shows_warning_on_invalid_tin(qapp, monkeypatch) -> None:
    dialog = AddGoodsDialog()
    dialog.goods_name_edit.setText("Принтер")
    dialog.manufacturer_name_edit.setText("БелЭлектроСнаб")
    dialog.manufacturer_tin_edit.setText("123")
    dialog.warehouse_edit.setText("Минск")

    warnings: list[tuple[object, str, str]] = []
    monkeypatch.setattr(
        "src.view.add_goods_dialog.QMessageBox.warning",
        lambda parent, title, message: warnings.append((parent, title, message)),
    )

    dialog._handle_accept()

    assert warnings == [
        (
            dialog,
            "Ошибка валидации",
            "УНП производителя должен состоять ровно из 9 цифр.",
        )
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("goods_name_edit", "Принтер"),
        ("manufacturer_name_edit", "БелЭлектроСнаб"),
    ],
)
def test_filter_form_rejects_conflicting_filters(qapp, field: str, value: str) -> None:
    form = GoodsFilterForm()
    form.quantity_edit.setText("15")
    form.manufacturer_tin_edit.setText("123456789")
    getattr(form, field).setText(value)

    with pytest.raises(ValueError):
        form.build_criteria()


def test_filter_form_builds_criteria_and_clears_inputs(qapp) -> None:
    form = GoodsFilterForm()
    form.goods_name_edit.setText("  Принтер ")
    form.quantity_edit.setText("")
    form.manufacturer_name_edit.setText(" ")
    form.manufacturer_tin_edit.setText("123456789")
    form.warehouse_edit.setText(" Минск ")

    criteria = form.build_criteria()
    form.clear()

    assert criteria.goods_name == "Принтер"
    assert criteria.quantity_in_stock is None
    assert criteria.manufacturer_tin == "123456789"
    assert criteria.warehouse_addres == " Минск "
    assert form.goods_name_edit.text() == ""
    assert form.manufacturer_tin_edit.text() == ""


def test_delete_dialog_builds_criteria(qapp) -> None:
    dialog = DeleteDialog()
    dialog.filter_form.warehouse_edit.setText("Брест")

    criteria = dialog.build_criteria()

    assert criteria.warehouse_addres == "Брест"


def test_goods_table_model_exposes_rows_columns_and_headers(sample_goods) -> None:
    model = GoodsTableModel()
    model.update_records([sample_goods])

    assert model.rowCount() == 1
    assert model.columnCount() == 5
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Принтер"
    assert model.data(model.index(0, 2), Qt.DisplayRole) == "123456789"
    assert model.data(model.index(0, 3), Qt.DisplayRole) == "15"
    assert model.data(model.index(0, 2), Qt.TextAlignmentRole) == int(Qt.AlignCenter)
    assert model.data(model.index(0, 0), Qt.TextAlignmentRole) == int(Qt.AlignLeft | Qt.AlignVCenter)
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Название товара"
    assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) == "1"


def test_goods_tree_model_builds_parent_and_child_rows(more_goods) -> None:
    model = GoodsTreeModel()
    model.update_records(more_goods[:1])

    assert model.rowCount() == 1
    parent_item = model.item(0, 0)
    assert parent_item.text() == "Запись 1: Принтер"
    assert parent_item.rowCount() == 5
    assert parent_item.child(2, 0).text() == "УНП производителя"
    assert parent_item.child(2, 1).text() == "123456789"


def test_pagination_widget_updates_buttons_and_emits_signals(qapp) -> None:
    widget = PaginationWidget()
    requested_pages: list[int] = []
    page_sizes: list[int] = []

    widget.page_requested.connect(requested_pages.append)
    widget.page_size_changed.connect(page_sizes.append)
    widget.update_state(page=2, total_pages=4, shown_items=5, total_items=20)

    widget._first_button.click()
    widget._prev_button.click()
    widget._next_button.click()
    widget._last_button.click()
    widget.set_page_size(25)

    assert widget.page_size == 25
    assert requested_pages == [1, 1, 3, 4]
    assert page_sizes[-1] == 25
    assert widget._info_label.text() == "Стр. 2 из 4"

    widget.update_state(page=1, total_pages=1, shown_items=0, total_items=0)
    assert widget._first_button.isEnabled() is False
    assert widget._next_button.isEnabled() is False

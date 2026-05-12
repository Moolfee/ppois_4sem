from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_SITE_PACKAGES = (
    PROJECT_ROOT
    / ".venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)

for path in (PROJECT_ROOT, VENV_SITE_PACKAGES):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

from PySide6.QtWidgets import QApplication

from src.models.goods import Goods


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def sample_goods() -> Goods:
    return Goods(
        goods_name="Принтер",
        manufacturer_name="БелЭлектроСнаб",
        manufacturer_tin=123456789,
        quantity_in_stock=15,
        warehouse_addres="Минск, Склад 1",
    )


@pytest.fixture()
def more_goods() -> list[Goods]:
    return [
        Goods(
            goods_name="Принтер",
            manufacturer_name="БелЭлектроСнаб",
            manufacturer_tin=123456789,
            quantity_in_stock=15,
            warehouse_addres="Минск, Склад 1",
        ),
        Goods(
            goods_name="Сканер",
            manufacturer_name="БелЭлектроСнаб",
            manufacturer_tin=123456789,
            quantity_in_stock=3,
            warehouse_addres="Гродно, Склад 2",
        ),
        Goods(
            goods_name="Станок",
            manufacturer_name="ПромТех",
            manufacturer_tin=987654321,
            quantity_in_stock=0,
            warehouse_addres="Брест, Цех 4",
        ),
    ]

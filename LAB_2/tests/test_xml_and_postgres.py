from __future__ import annotations

import builtins
import types

import pytest

from src.db.postgres_probe import OptionalPostgresProbe, PostgresConnectionError
from src.ingest.xml_goods_io import GoodsXmlDomExporter, GoodsXmlSaxImporter


def test_xml_export_and_import_roundtrip(tmp_path, more_goods) -> None:
    export_path = tmp_path / "goods.xml"

    GoodsXmlDomExporter().export_to_file(export_path, more_goods)
    imported = GoodsXmlSaxImporter().import_from_file(export_path)

    assert export_path.exists()
    assert imported == more_goods


def test_postgres_probe_returns_when_dsn_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("GOODS_POSTGRES_DSN", raising=False)

    OptionalPostgresProbe().check_connection()


def test_postgres_probe_wraps_missing_driver(monkeypatch) -> None:
    monkeypatch.setenv("GOODS_POSTGRES_DSN", "postgresql://demo")

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "psycopg":
            raise ModuleNotFoundError("missing psycopg")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(PostgresConnectionError):
        OptionalPostgresProbe().check_connection()


def test_postgres_probe_wraps_connection_errors(monkeypatch) -> None:
    monkeypatch.setenv("GOODS_POSTGRES_DSN", "postgresql://demo")

    class FailingPsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            raise RuntimeError("refused")

    monkeypatch.setitem(__import__("sys").modules, "psycopg", FailingPsycopg)

    with pytest.raises(PostgresConnectionError, match="Не удалось подключиться к Postgres: refused"):
        OptionalPostgresProbe().check_connection()


def test_postgres_probe_uses_connect_timeout(monkeypatch) -> None:
    monkeypatch.setenv("GOODS_POSTGRES_DSN", "postgresql://demo")
    captured: dict[str, object] = {}

    class Connection:
        def __enter__(self):
            captured["entered"] = True
            return self

        def __exit__(self, exc_type, exc, tb):
            captured["exited"] = True
            return False

    class FakePsycopg:
        @staticmethod
        def connect(dsn, connect_timeout):
            captured["dsn"] = dsn
            captured["timeout"] = connect_timeout
            return Connection()

    monkeypatch.setitem(__import__("sys").modules, "psycopg", FakePsycopg)

    OptionalPostgresProbe().check_connection()

    assert captured == {
        "dsn": "postgresql://demo",
        "timeout": 3,
        "entered": True,
        "exited": True,
    }

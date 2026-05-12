# LAB_4

## Структура

```text
LAB_4/
  src/video_player_web/
    app.py              FastAPI-приложение
    lab1_bridge.py      подключение общего кода из LAB_1
    static/             HTML, CSS и JavaScript
  tests/test_api.py     тесты API
  pyproject.toml        зависимости и настройки
```

## Установка

```bash
cd LAB_4
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[test]"
```

## Запуск веб-интерфейса

```bash
cd LAB_4
source .venv/bin/activate
python3 -m uvicorn video_player_web.app:app --reload
```

Адрес:

```text
http://127.0.0.1:8000
```

## Запуск тестов

```bash
cd LAB_4
source .venv/bin/activate
python3 -m pytest
```

Тесты запускаются с проверкой покрытия. Минимальный порог покрытия задан в
`pyproject.toml`: `90%`.

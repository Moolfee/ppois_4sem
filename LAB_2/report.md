# LAB_2 Report
## Структура

- `src/main.py`
  Запуск `QApplication` и создание `MainController`.

- `src/models`
  Доменные сущности и DTO.

- `src/db`
  Хранилище данных и проверка подключения к Postgres.

- `src/repo`
  CRUD и транзакционная запись.

- `src/fetch`
  Чтение, фильтрация и пагинация.

- `src/ingest`
  Импорт и экспорт XML.

- `src/view`
  Окна, диалоги, Qt-модели и виджет пагинации.

- `src/controller`
  Связь между UI и слоями данных.

- `src/utils`
  Чистые вспомогательные функции.

## Логика по слоям

### `src/models/goods.py`

`Goods` хранит поля:

- `goods_name`
- `manufacturer_name`
- `manufacturer_tin`
- `quantity_in_stock`
- `warehouse_addres`

В `__post_init__` выполняется валидация:

- строковые поля не пустые;
- `manufacturer_tin` содержит ровно 9 цифр;
- `quantity_in_stock >= 0`.

Свойство `manufacturer_tin_text` возвращает УНП как строку.

Свойство `quantity_display` возвращает:

- `нет на складе`, если количество равно `0`;
- число как строку в остальных случаях.

### `src/models/filters.py`

`GoodsFilterCriteria` хранит условия поиска и удаления.

В объекте задаются прямые поля фильтра:

- `goods_name`
- `quantity_in_stock`
- `manufacturer_name`
- `manufacturer_tin`
- `warehouse_addres`

Метод `normalized()` подготавливает значения для сравнения.

Метод `has_active_filters()` проверяет, задано ли хотя бы одно условие.

### `src/models/pagination.py`

`PageRequest` хранит номер страницы и размер страницы.

`PageResult` хранит:

- список элементов текущей страницы;
- номер страницы;
- размер страницы;
- общее число записей.

Также вычисляет число страниц и количество элементов на текущей странице.

### `src/db/in_memory_database.py`

`InMemoryGoodsDatabase` хранит список `Goods` в памяти.

Метод `transaction()` создаёт снимок текущего списка. Если внутри транзакции возникает исключение, исходный список восстанавливается.

Методы:

- `read_all()` возвращает копию списка;
- `write_all()` полностью заменяет список.

### `src/db/postgres_probe.py`

`OptionalPostgresProbe` не используется как основное хранилище. Он только проверяет, можно ли подключиться к Postgres, если задана переменная среды `GOODS_POSTGRES_DSN`.

Если подключение невозможно, выбрасывается `PostgresConnectionError`.

### `src/repo/goods_repository.py`

`GoodsRepository` работает поверх `InMemoryGoodsDatabase`.

Методы:

- `add()` добавляет одну запись;
- `add_many()` добавляет список записей;
- `replace_all()` заменяет весь массив;
- `list_all()` возвращает все записи;
- `count()` возвращает количество записей;
- `remove_matching()` удаляет все записи, подходящие под фильтр;
- `transaction()` проксирует транзакцию базы.

Для удаления используется функция `goods_matches()` из `src/utils/goods_matching.py`.

### `src/utils/goods_matching.py`

`goods_matches()` сравнивает объект `Goods` с `GoodsFilterCriteria`.

Проверяются:

- название товара;
- количество;
- название производителя;
- УНП;
- адрес склада.

Сравнение строк выполняется без учёта регистра.

### `src/fetch/goods_fetch_service.py`

`GoodsFetchService` выполняет только чтение.

Метод `fetch_page()`:

1. получает весь список из репозитория;
2. при наличии фильтра оставляет только подходящие записи;
3. вычисляет допустимую страницу;
4. возвращает `PageResult`.

### `src/ingest/xml_goods_io.py`

`GoodsXmlDomExporter` сохраняет список `Goods` в XML через `xml.dom.minidom`.

Корневой тег: `goods_items`.

Тег записи: `goods`.

Поля записи:

- `goods_name`
- `manufacturer_name`
- `manufacturer_tin`
- `quantity_in_stock`
- `warehouse_addres`

`GoodsXmlSaxImporter` загружает XML через `xml.sax`.

Внутренний SAX-обработчик:

- собирает текст полей;
- на закрытии тега записи создаёт объект `Goods`;
- добавляет его в итоговый список.

### `src/view/goods_table_model.py`

`GoodsTableModel` наследуется от `QAbstractTableModel`.

Используется для отображения списка `Goods` в `QTableView`.

Модель:

- задаёт заголовки колонок;
- возвращает значения ячеек;
- выравнивает числовые колонки;
- обновляет список через `update_records()`.

### `src/view/goods_tree_model.py`

`GoodsTreeModel` наследуется от `QStandardItemModel`.

Используется для `QTreeView`.

Для каждой записи создаётся верхний узел.

Дочерние элементы содержат пары:

- название поля;
- значение поля.

### `src/view/pagination_widget.py`

`PaginationWidget` содержит:

- кнопки первой, предыдущей, следующей и последней страницы;
- выбор размера страницы `5/10/25/50`;
- текст `Стр. X из Y`.

Виджет не делает выборку сам. Он только хранит состояние и отправляет сигналы:

- `page_requested`;
- `page_size_changed`.

### `src/view/add_goods_dialog.py`

Диалог добавления одной записи.

Поля ввода:

- название товара;
- название производителя;
- УНП;
- количество;
- адрес склада.

На подтверждении строится объект `Goods`. Если валидация не проходит, показывается `QMessageBox`.

### `src/view/filter_form.py`

Общая форма фильтрации для поиска и удаления.

Содержит обычные поля:

- `Название товара`
- `Количество на складе`
- `Название производителя`
- `УНП производителя`
- `Адрес склада`

Логика:

- в паре `Название товара / Количество на складе` можно задать только одно поле;
- в паре `Название производителя / УНП производителя` можно задать только одно поле;
- если заполнены оба поля пары, выбрасывается ошибка;
- из введённых значений напрямую строится `GoodsFilterCriteria` без дополнительных режимов.

### `src/view/search_dialog.py`

Диалог поиска содержит:

- `GoodsFilterForm`;
- таблицу результатов;
- `PaginationWidget`;
- кнопки поиска, сброса и закрытия.

Результаты показываются в этом же окне.

### `src/view/delete_dialog.py`

Диалог удаления содержит `GoodsFilterForm` и кнопки подтверждения/отмены.

Само удаление выполняет не диалог, а контроллер.

### `src/view/main_window.py`

Главное окно содержит:

- menu;
- toolbar;
- `QTableView`;
- `QTreeView`;
- `QStackedWidget` для переключения режима отображения;
- `PaginationWidget`;
- `QStatusBar`.

Метод `set_page()` обновляет таблицу, дерево и состояние пагинации.

### `src/controller/main_controller.py`

`MainController` создаёт все зависимости:

- базу;
- репозиторий;
- fetch-сервис;
- XML importer/exporter;
- главное окно.

Контроллер:

- подключает действия меню и toolbar;
- открывает диалог добавления и сохраняет запись;
- открывает диалог поиска и обновляет результаты;
- открывает диалог удаления и удаляет подходящие записи;
- загружает XML и заменяет текущий массив;
- сохраняет текущий массив в XML;
- переключает таблицу и дерево;
- обновляет главную страницу после любых изменений;
- показывает сообщения об ошибках и результате операций.

## Потоки данных

### Добавление

`AddGoodsDialog` -> `MainController` -> `GoodsRepository.add()` -> `InMemoryGoodsDatabase`

### Поиск

`SearchDialog` -> `GoodsFilterForm.build_criteria()` -> `GoodsFetchService.fetch_page()` -> `GoodsRepository.list_all()` -> `GoodsTableModel`

### Удаление

`DeleteDialog` -> `GoodsFilterForm.build_criteria()` -> `GoodsRepository.remove_matching()` -> `goods_matches()`

### Загрузка XML

`QFileDialog` -> `GoodsXmlSaxImporter.import_from_file()` -> `GoodsRepository.replace_all()`

### Сохранение XML

`QFileDialog` -> `GoodsRepository.list_all()` -> `GoodsXmlDomExporter.export_to_file()`

## Файлы данных

В `sample_data/` находятся готовые XML-файлы с примерами записей. Приложение использует их только как входные данные для загрузки через меню.

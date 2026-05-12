from pathlib import Path
from xml.dom.minidom import Document
from xml.sax import ContentHandler, make_parser

from src.models.goods import Goods


class GoodsXmlDomExporter:
    ROOT_TAG = "goods_items"
    ITEM_TAG = "goods"
    FIELD_TAGS = (
        "goods_name",
        "manufacturer_name",
        "manufacturer_tin",
        "quantity_in_stock",
        "warehouse_addres",
    )

    def export_to_file(self, file_path: str | Path, goods_list: list[Goods]) -> None:
        document = Document()
        root = document.createElement(self.ROOT_TAG)
        document.appendChild(root)

        for goods in goods_list:
            item_element = document.createElement(self.ITEM_TAG)
            root.appendChild(item_element)

            field_values = {
                "goods_name": goods.goods_name,
                "manufacturer_name": goods.manufacturer_name,
                "manufacturer_tin": goods.manufacturer_tin_text,
                "quantity_in_stock": str(goods.quantity_in_stock),
                "warehouse_addres": goods.warehouse_addres,
            }

            for tag_name in self.FIELD_TAGS:
                field_element = document.createElement(tag_name)
                field_element.appendChild(document.createTextNode(field_values[tag_name]))
                item_element.appendChild(field_element)

        path = Path(file_path)
        with path.open("w", encoding="utf-8") as xml_file:
            xml_file.write(document.toprettyxml(indent="  ", encoding=None))


class _GoodsSaxHandler(ContentHandler):
    def __init__(self) -> None:
        super().__init__()
        self.goods_list: list[Goods] = []
        self._current_record: dict[str, str] = {}
        self._current_tag: str | None = None
        self._buffer: list[str] = []

    def startElement(self, name: str, attrs) -> None:
        if name == GoodsXmlDomExporter.ITEM_TAG:
            self._current_record = {}
        elif name in GoodsXmlDomExporter.FIELD_TAGS:
            self._current_tag = name
            self._buffer = []

    def characters(self, content: str) -> None:
        if self._current_tag is not None:
            self._buffer.append(content)

    def endElement(self, name: str) -> None:
        if name in GoodsXmlDomExporter.FIELD_TAGS and self._current_tag == name:
            self._current_record[name] = "".join(self._buffer).strip()
            self._current_tag = None
            self._buffer = []
            return

        if name == GoodsXmlDomExporter.ITEM_TAG:
            goods = Goods(
                goods_name=self._current_record["goods_name"],
                manufacturer_name=self._current_record["manufacturer_name"],
                manufacturer_tin=int(self._current_record["manufacturer_tin"]),
                quantity_in_stock=int(self._current_record["quantity_in_stock"]),
                warehouse_addres=self._current_record["warehouse_addres"],
            )
            self.goods_list.append(goods)
            self._current_record = {}


class GoodsXmlSaxImporter:
    def import_from_file(self, file_path: str | Path) -> list[Goods]:
        parser = make_parser()
        handler = _GoodsSaxHandler()
        parser.setContentHandler(handler)

        path = Path(file_path)
        with path.open("r", encoding="utf-8") as xml_file:
            parser.parse(xml_file)
        return handler.goods_list

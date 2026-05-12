import sys

from PySide6.QtWidgets import QApplication

from src.controller.main_controller import MainController


def run() -> int:
    app = QApplication(sys.argv)
    controller = MainController()
    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from corporate_serf_tracker.ui.main_window import MainWindow


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / relative_path)

    return str(Path(__file__).resolve().parent / relative_path)


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setWindowIcon(QIcon(get_resource_path("assets/app_icon.ico")))

    window = MainWindow()
    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()

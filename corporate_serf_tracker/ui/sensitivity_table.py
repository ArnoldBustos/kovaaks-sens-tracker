from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SensitivityTableWidget(QWidget):
    def __init__(self, by_cm_scores: dict):
        super().__init__()
        self.by_cm_scores = by_cm_scores

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            [
                "cm / 360",
                "Best Score",
                "Plays",
            ]
        )

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        horizontal_header = self.table.horizontalHeader()
        horizontal_header.setStretchLastSection(True)
        horizontal_header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        horizontal_header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.table.setStyleSheet(
            """
      QTableWidget {
        background: #0f1822;
        color: #f5f7fa;
        border: 1px solid #344152;
        gridline-color: #344152;
        selection-background-color: #22334a;
        selection-color: #3fbcde;
      }

      QHeaderView::section {
        background: #16202c;
        color: #aab4c0;
        border: 1px solid #344152;
        padding: 6px;
        font-weight: 700;
      }

      QTableWidget::item {
        padding: 6px;
      }
      """
        )

        layout.addWidget(self.table)

        self._populate()

    def _populate(self):
        sorted_cms = sorted(self.by_cm_scores.keys())

        self.table.setRowCount(len(sorted_cms))

        for row_index, cm_value in enumerate(sorted_cms):
            scores = self.by_cm_scores[cm_value]
            best_score = max(scores)
            play_count = len(scores)

            cm_item = QTableWidgetItem(f"{cm_value:.4g}")
            score_item = QTableWidgetItem(str(int(best_score)))
            count_item = QTableWidgetItem(str(play_count))

            cm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row_index, 0, cm_item)
            self.table.setItem(row_index, 1, score_item)
            self.table.setItem(row_index, 2, count_item)

        self.table.resizeRowsToContents()

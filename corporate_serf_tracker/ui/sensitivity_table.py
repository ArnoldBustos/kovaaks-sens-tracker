from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from corporate_serf_tracker.formatting import fmt_score


class SensitivityTableWidget(QWidget):
    def __init__(self, by_cm_scores: dict):
        super().__init__()
        self.by_cm_scores = by_cm_scores

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                "CM/360",
                "Best Score",
                "Bar",
                "Median",
                "Plays",
            ]
        )

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)

        horizontal_header = self.table.horizontalHeader()
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        horizontal_header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        horizontal_header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        horizontal_header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        horizontal_header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        horizontal_header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )

        self.table.setStyleSheet(
            """
      QTableWidget {
        background: #131a24;
        color: #f5f7fa;
        border: none;
        outline: none;
        selection-background-color: #182632;
        selection-color: #f5f7fa;
      }

      QTableWidget QWidget {
        background: transparent;
      }

      QTableCornerButton::section {
        background: #131a24;
        border: none;
      }

      QHeaderView::section {
        background: #131a24;
        color: #aab4c0;
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding: 10px 12px;
        font-size: 10px;
        font-weight: 700;
      }

      QTableWidget::item {
        border: none;
        padding: 6px 8px;
      }

      QScrollBar:vertical {
        background: #0f1822;
        width: 10px;
        margin: 0;
      }

      QScrollBar::handle:vertical {
        background: #22334a;
        min-height: 28px;
      }

      QScrollBar::add-line:vertical,
      QScrollBar::sub-line:vertical {
        height: 0;
      }
      """
        )

        layout.addWidget(self.table)

        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._populate()

    def _update_table_height(self):
        header_height = self.table.horizontalHeader().height()
        row_total = 0

        for row_index in range(self.table.rowCount()):
            row_total += self.table.rowHeight(row_index)

        frame_height = self.table.frameWidth() * 2
        extra_padding = 6

        total_height = header_height + row_total + frame_height + extra_padding
        self.table.setFixedHeight(total_height)

    def _populate(self):
        sorted_cms = sorted(self.by_cm_scores.keys())
        self.table.setRowCount(len(sorted_cms))

        if not sorted_cms:
            return

        row_payloads = []
        global_best_score = None
        global_worst_score = None
        best_cm = None
        worst_cm = None

        for cm_value in sorted_cms:
            scores = self.by_cm_scores[cm_value]
            best_score = max(scores)
            play_count = len(scores)
            sorted_scores = sorted(scores)
            score_count = len(sorted_scores)
            midpoint = score_count // 2

            if score_count % 2:
                median_score = sorted_scores[midpoint]
            else:
                median_score = (
                    sorted_scores[midpoint - 1] + sorted_scores[midpoint]
                ) / 2

            row_payloads.append(
                {
                    "cm": cm_value,
                    "best_score": best_score,
                    "median_score": median_score,
                    "play_count": play_count,
                }
            )

            if global_best_score is None or best_score > global_best_score:
                global_best_score = best_score
                best_cm = cm_value

            if global_worst_score is None or best_score < global_worst_score:
                global_worst_score = best_score
                worst_cm = cm_value

        score_range = global_best_score - global_worst_score

        for row_index, row_payload in enumerate(row_payloads):
            cm_value = row_payload["cm"]
            best_score = row_payload["best_score"]
            median_score = row_payload["median_score"]
            play_count = row_payload["play_count"]

            cm_item = QTableWidgetItem(f"{cm_value:.4g}")
            best_item = QTableWidgetItem(fmt_score(best_score))
            bar_item = QTableWidgetItem("")
            median_item = QTableWidgetItem(fmt_score(median_score))
            plays_item = QTableWidgetItem(str(play_count))

            cm_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            best_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            median_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            plays_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            self.table.setItem(row_index, 0, cm_item)
            self.table.setItem(row_index, 1, best_item)
            self.table.setItem(row_index, 2, bar_item)
            self.table.setItem(row_index, 3, median_item)
            self.table.setItem(row_index, 4, plays_item)

            bar_widget = self._build_bar_widget(
                best_score=best_score,
                global_best_score=global_best_score,
                is_best_row=(cm_value == best_cm),
                is_worst_row=(cm_value == worst_cm and worst_cm != best_cm),
            )
            self.table.setCellWidget(row_index, 2, bar_widget)

            self._style_row(
                row_index=row_index,
                cm_value=cm_value,
                best_score=best_score,
                median_score=median_score,
                global_best_score=global_best_score,
                global_worst_score=global_worst_score,
                best_cm=best_cm,
                worst_cm=worst_cm,
                score_range=score_range,
            )

        self.table.resizeRowsToContents()
        self.table.verticalHeader().setDefaultSectionSize(28)
        self._update_table_height()

    def _build_bar_widget(
        self,
        best_score: float,
        global_best_score: float,
        is_best_row: bool,
        is_worst_row: bool,
    ) -> QWidget:
        outer_widget = QWidget()
        outer_widget.setStyleSheet("background: transparent;")
        outer_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(10, 4, 20, 4)
        outer_layout.setSpacing(0)
        outer_widget.setLayout(outer_layout)

        track_widget = QWidget()
        track_widget.setFixedHeight(8)
        track_widget.setMinimumWidth(140)
        track_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        track_widget.setStyleSheet(
            """
            background: #18212b;
            border: none;
            border-radius: 4px;
            """
        )

        if global_best_score <= 0:
            fill_ratio = 0.0
        else:
            fill_ratio = best_score / global_best_score
            fill_ratio *= 0.92

        if fill_ratio < 0:
            fill_ratio = 0.0

        if fill_ratio > 1:
            fill_ratio = 1.0

        if is_best_row:
            fill_color = "#81ecff"
        elif is_worst_row:
            fill_color = "#ff5c93"
        else:
            fill_color = "#d6dbe3"

        fill_stretch = int(fill_ratio * 100)
        if fill_stretch < 1:
            fill_stretch = 1

        empty_stretch = 100 - fill_stretch
        if empty_stretch < 0:
            empty_stretch = 0

        track_layout = QHBoxLayout()
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(0)
        track_widget.setLayout(track_layout)

        fill_widget = QWidget()
        fill_widget.setFixedHeight(8)
        fill_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        fill_widget.setStyleSheet(
            f"""
            background: {fill_color};
            border: none;
            border-radius: 4px;
            """
        )

        spacer_widget = QWidget()
        spacer_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        spacer_widget.setStyleSheet("background: transparent; border: none;")

        track_layout.addWidget(fill_widget, fill_stretch)
        track_layout.addWidget(spacer_widget, empty_stretch)

        outer_layout.addWidget(track_widget)
        return outer_widget

    def _style_row(
        self,
        row_index: int,
        cm_value: float,
        best_score: float,
        median_score: float,
        global_best_score: float,
        global_worst_score: float,
        best_cm: float,
        worst_cm: float,
        score_range: float,
    ):
        default_background = QColor("#131a24")
        hover_like_background = QColor("#17202a")
        best_background = QColor("#101c26")
        worst_background = QColor("#1d1218")

        default_text = QColor("#f5f7fa")
        muted_text = QColor("#aab4c0")
        accent_text = QColor("#81ecff")
        best_text = QColor("#81ecff")
        worst_text = QColor("#ff5c93")

        is_best_row = cm_value == best_cm
        is_worst_row = cm_value == worst_cm and worst_cm != best_cm

        for column_index in range(self.table.columnCount()):
            table_item = self.table.item(row_index, column_index)

            if table_item is None:
                continue

            table_item.setBackground(default_background)
            table_item.setForeground(default_text)

            if column_index >= 3:
                table_item.setForeground(muted_text)

        if row_index % 2 == 1:
            for column_index in range(self.table.columnCount()):
                table_item = self.table.item(row_index, column_index)
                if table_item is not None:
                    table_item.setBackground(hover_like_background)

        if is_best_row:
            for column_index in range(self.table.columnCount()):
                table_item = self.table.item(row_index, column_index)
                if table_item is not None:
                    table_item.setBackground(best_background)

            self.table.item(row_index, 0).setForeground(best_text)
            self.table.item(row_index, 1).setForeground(best_text)
            self.table.item(row_index, 3).setForeground(best_text)
            self.table.item(row_index, 4).setForeground(best_text)

        if is_worst_row:
            for column_index in range(self.table.columnCount()):
                table_item = self.table.item(row_index, column_index)
                if table_item is not None:
                    table_item.setBackground(worst_background)

            self.table.item(row_index, 0).setForeground(worst_text)
            self.table.item(row_index, 1).setForeground(worst_text)

        self.table.item(row_index, 0).setFont(self._font(weight=QFont.Weight.Bold))
        self.table.item(row_index, 1).setFont(self._font(weight=QFont.Weight.Bold))
        self.table.item(row_index, 3).setFont(self._font())
        self.table.item(row_index, 4).setFont(self._font())

    def _font(self, family: str = "Segoe UI", weight=QFont.Weight.Medium):
        from PySide6.QtGui import QFont

        font = QFont(family)
        font.setWeight(weight)
        return font

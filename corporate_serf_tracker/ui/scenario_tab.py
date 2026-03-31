from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from corporate_serf_tracker.formatting import fmt_score
from corporate_serf_tracker.ui.chart_widget import ScoreChartWidget
from corporate_serf_tracker.ui.scenario_data import (
    build_summary_stats,
    parse_optional_float,
)
from corporate_serf_tracker.ui.sensitivity_table import SensitivityTableWidget


class ScenarioTab(QWidget):
    def __init__(self, scenario_name: str, plays: list, assignments: dict, ranks: dict):
        super().__init__()
        self.scenario_name = scenario_name
        self.plays = plays
        self.assignments = assignments
        self.ranks = ranks

        self.last_8_only = False
        self.cm_min_text = ""
        self.cm_max_text = ""

        self._build_ui()
        self._apply_styles()
        self._refresh_content()

    def _build_ui(self):
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        self.setLayout(outer_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        self.root_layout = QVBoxLayout()
        self.root_layout.setContentsMargins(16, 16, 16, 16)
        self.root_layout.setSpacing(12)
        scroll_content.setLayout(self.root_layout)

        self.header_row = self._build_header_row()
        self.filter_row = self._build_filter_row()

        self.overview_container = QWidget()
        self.content_container = QWidget()

        self.root_layout.addWidget(self.header_row)
        self.root_layout.addWidget(self.filter_row)
        self.root_layout.addWidget(self.overview_container)
        self.root_layout.addWidget(self.content_container)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

    def _build_header_row(self) -> QWidget:
        container = QFrame()
        container.setObjectName("sectionCard")

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        container.setLayout(layout)

        title_label = QLabel(self.scenario_name)
        title_label.setObjectName("scenarioTitle")

        self.play_count_label = QLabel(f"Loaded plays: {len(self.plays)}")
        self.play_count_label.setObjectName("scenarioMeta")

        left_column = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        left_column.setLayout(left_layout)
        left_layout.addWidget(title_label)
        left_layout.addWidget(self.play_count_label)

        layout.addWidget(left_column)
        layout.addStretch(1)

        return container

    def _build_filter_row(self) -> QWidget:
        container = QFrame()
        container.setObjectName("sectionCard")

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        container.setLayout(layout)

        heading_label = QLabel("FILTERS")
        heading_label.setObjectName("sectionHeading")

        self.last_8_checkbox = QCheckBox("Last 8 only")
        self.last_8_checkbox.stateChanged.connect(self._handle_filters_changed)

        min_label = QLabel("Min cm")
        min_label.setObjectName("filterLabel")

        self.cm_min_input = QLineEdit()
        self.cm_min_input.setPlaceholderText("e.g. 60")
        self.cm_min_input.setFixedWidth(90)
        self.cm_min_input.editingFinished.connect(self._handle_filters_changed)

        max_label = QLabel("Max cm")
        max_label.setObjectName("filterLabel")

        self.cm_max_input = QLineEdit()
        self.cm_max_input.setPlaceholderText("e.g. 80")
        self.cm_max_input.setFixedWidth(90)
        self.cm_max_input.editingFinished.connect(self._handle_filters_changed)

        reset_button = QPushButton("Reset Filters")
        reset_button.clicked.connect(self._reset_filters)

        layout.addWidget(heading_label)
        layout.addSpacing(8)
        layout.addWidget(self.last_8_checkbox)
        layout.addSpacing(8)
        layout.addWidget(min_label)
        layout.addWidget(self.cm_min_input)
        layout.addWidget(max_label)
        layout.addWidget(self.cm_max_input)
        layout.addWidget(reset_button)
        layout.addStretch(1)

        return container

    def _handle_filters_changed(self):
        self.last_8_only = self.last_8_checkbox.isChecked()
        self.cm_min_text = self.cm_min_input.text()
        self.cm_max_text = self.cm_max_input.text()
        self._refresh_content()

    def _reset_filters(self):
        self.last_8_checkbox.setChecked(False)
        self.cm_min_input.setText("")
        self.cm_max_input.setText("")
        self.last_8_only = False
        self.cm_min_text = ""
        self.cm_max_text = ""
        self._refresh_content()

    def _refresh_content(self):
        cm_min = parse_optional_float(self.cm_min_text)
        cm_max = parse_optional_float(self.cm_max_text)

        summary_stats = build_summary_stats(
            plays=self.plays,
            assignments=self.assignments,
            last_8_only=self.last_8_only,
            cm_min=cm_min,
            cm_max=cm_max,
        )

        self.play_count_label.setText(f"Loaded plays: {summary_stats['total_plays']}")

        self._replace_widget(
            container_widget=self.overview_container,
            replacement_widget=self._build_overview_section(summary_stats),
        )
        self._replace_widget(
            container_widget=self.content_container,
            replacement_widget=self._build_content_column(
                summary_stats["by_cm_scores"]
            ),
        )

    def _replace_widget(self, container_widget: QWidget, replacement_widget: QWidget):
        layout = container_widget.layout()

        if layout is None:
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            container_widget.setLayout(layout)
        else:
            while layout.count():
                child_item = layout.takeAt(0)
                child_widget = child_item.widget()
                if child_widget is not None:
                    child_widget.deleteLater()

        layout.addWidget(replacement_widget)

    def _build_overview_section(self, summary_stats: dict) -> QWidget:
        container = QFrame()
        container.setObjectName("sectionCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        container.setLayout(layout)

        heading_label = QLabel("OVERVIEW")
        heading_label.setObjectName("sectionHeading")
        layout.addWidget(heading_label)

        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(10)
        stats_grid.setVerticalSpacing(10)

        stat_cards = [
            ("OVERALL BEST", fmt_score(summary_stats["best_score"]), "goldValue"),
            ("CM FOR BEST", summary_stats["cm_for_best_label"], "accentValue"),
            ("BEST CROSSHAIR", summary_stats["best_crosshair_label"], "accentValue"),
            ("MEDIAN", fmt_score(summary_stats["median_score"]), "defaultValue"),
            ("TOTAL PLAYS", str(summary_stats["total_plays"]), "defaultValue"),
            ("EST. BEST CM", summary_stats["estimated_best_label"], "greenValue"),
            ("WORST CM", summary_stats["worst_cm_label"], "worstValue"),
            ("NEXT CM TO TEST", summary_stats["next_cm_label"], "greenValue"),
        ]

        for stat_index, stat_data in enumerate(stat_cards):
            title_text, value_text, value_style = stat_data
            row_index = stat_index // 4
            column_index = stat_index % 4

            stat_card = self._build_stat_card(
                title_text=title_text,
                value_text=value_text,
                value_style=value_style,
            )
            stats_grid.addWidget(stat_card, row_index, column_index)

        layout.addLayout(stats_grid)

        return container

    def _build_content_column(self, by_cm_scores: dict) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        container.setLayout(layout)

        chart_card = self._build_chart_card(by_cm_scores)
        table_card = self._build_table_card(by_cm_scores)

        layout.addWidget(chart_card)
        layout.addWidget(table_card)

        return container

    def _build_chart_card(self, by_cm_scores: dict) -> QWidget:
        container = QFrame()
        container.setObjectName("sectionCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        container.setLayout(layout)

        title_label = QLabel("CHART")
        title_label.setObjectName("sectionHeading")

        chart_widget = ScoreChartWidget(by_cm_scores=by_cm_scores)
        chart_widget.setMinimumHeight(360)

        layout.addWidget(title_label)
        layout.addWidget(chart_widget)

        return container

    def _build_table_card(self, by_cm_scores: dict) -> QWidget:
        container = QFrame()
        container.setObjectName("sectionCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        container.setLayout(layout)

        title_label = QLabel("SENSITIVITY TABLE")
        title_label.setObjectName("sectionHeading")

        table_widget = SensitivityTableWidget(by_cm_scores=by_cm_scores)
        table_widget.setMinimumHeight(280)

        layout.addWidget(title_label)
        layout.addWidget(table_widget)

        return container

    def _build_stat_card(
        self, title_text: str, value_text: str, value_style: str
    ) -> QWidget:
        container = QFrame()
        container.setObjectName("statCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        container.setLayout(layout)

        title_label = QLabel(title_text)
        title_label.setObjectName("statTitle")

        value_label = QLabel(value_text)
        value_label.setObjectName(value_style)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch(1)

        return container

    def _apply_styles(self):
        self.setStyleSheet(
            """
      QScrollArea {
        background: #0b0f14;
        border: none;
      }

      QScrollArea > QWidget > QWidget {
        background: #0b0f14;
      }

      #sectionCard {
        background: #0f1822;
        border: 1px solid #344152;
      }

      #statCard {
        background: #16202c;
        border: 1px solid #344152;
        min-height: 92px;
      }

      #scenarioTitle {
        color: #3fbcde;
        font-size: 18px;
        font-weight: 700;
      }

      #scenarioMeta {
        color: #aab4c0;
        font-size: 12px;
      }

      #sectionHeading {
        color: #aab4c0;
        font-size: 11px;
        font-weight: 700;
      }

      #statTitle {
        color: #aab4c0;
        font-size: 10px;
        font-weight: 700;
      }

      #filterLabel {
        color: #aab4c0;
        font-size: 11px;
      }

      #goldValue {
        color: #e8d84a;
        font-size: 16px;
        font-weight: 700;
      }

      #accentValue {
        color: #3fbcde;
        font-size: 16px;
        font-weight: 700;
      }

      #greenValue {
        color: #01986f;
        font-size: 16px;
        font-weight: 700;
      }

      #defaultValue {
        color: #f5f7fa;
        font-size: 16px;
        font-weight: 700;
      }

      #worstValue {
        color: #ff5c93;
        font-size: 16px;
        font-weight: 700;
      }

      QLineEdit {
        background: #1a2330;
        color: #f5f7fa;
        border: 1px solid #344152;
        padding: 6px 8px;
      }

      QCheckBox {
        color: #f5f7fa;
      }

      QPushButton {
        background: #1a2330;
        color: #aab4c0;
        border: 1px solid #344152;
        padding: 6px 10px;
      }
      """
        )

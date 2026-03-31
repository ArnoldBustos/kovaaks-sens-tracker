from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from datetime import datetime


class ScenarioTab(QWidget):
    def __init__(
        self,
        scenario_name: str,
        plays: list,
        assignments: dict,
        ranks: dict,
        app_state,
        save_ui_state_callback,
    ):
        super().__init__()
        self.scenario_name = scenario_name
        self.plays = plays
        self.assignments = assignments
        self.ranks = ranks

        self.last_8_only = False
        self.cm_min_text = ""
        self.cm_max_text = ""
        self.app_state = app_state
        self.save_ui_state_callback = save_ui_state_callback

        self.is_chart_expanded = self.app_state.chart_expanded
        self.is_table_expanded = self.app_state.table_expanded

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
        self.root_layout.setSpacing(6)
        scroll_content.setLayout(self.root_layout)

        self.filter_row = self._build_filter_row()

        self.overview_container = QWidget()
        self.content_container = QWidget()

        self.root_layout.addWidget(self.overview_container)
        self.root_layout.addWidget(self.filter_row)
        self.root_layout.addWidget(self.content_container)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

    def _build_filter_row(self) -> QWidget:
        container = QFrame()
        container.setObjectName("sectionCard")

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 8, 14, 8)
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
        export_button = QPushButton("Export PDF")
        export_button.clicked.connect(self._handle_export_pdf)

        layout.addWidget(export_button)

        layout.addStretch(1)

        return container

    def _handle_export_pdf(self):
        import tempfile

        cm_min = parse_optional_float(self.cm_min_text)
        cm_max = parse_optional_float(self.cm_max_text)

        summary_stats = build_summary_stats(
            plays=self.plays,
            assignments=self.assignments,
            last_8_only=self.last_8_only,
            cm_min=cm_min,
            cm_max=cm_max,
        )

        from corporate_serf_tracker.export.pdf_export import export_scenario_pdf

        last_export_directory = getattr(self.app_state, "last_export_directory", "")

        if not last_export_directory:
            default_directory = str(Path.home() / "Documents")
        else:
            default_directory = last_export_directory

        timestamp_text = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_file_name = (
            f"{self.scenario_name.replace(' ', '_')}_{timestamp_text}_report.pdf"
        )
        default_path = str(Path(default_directory) / safe_file_name)

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF Report",
            default_path,
            "PDF Files (*.pdf)",
        )

        if not output_path:
            return

        if not output_path.lower().endswith(".pdf"):
            output_path = f"{output_path}.pdf"

        temporary_chart_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temporary_chart_path = temp_file.name

            if hasattr(self, "chart_widget") and self.chart_widget is not None:
                self.chart_widget.save_chart_image(temporary_chart_path)

            export_scenario_pdf(
                output_path=output_path,
                scenario_name=self.scenario_name,
                summary_stats=summary_stats,
                by_cm_scores=summary_stats["by_cm_scores"],
                filters={
                    "last_8_only": self.last_8_only,
                    "cm_min": self.cm_min_text,
                    "cm_max": self.cm_max_text,
                },
                chart_image_path=temporary_chart_path,
            )

            export_directory = str(Path(output_path).parent)
            self.app_state.last_export_directory = export_directory
            self.save_ui_state_callback()

            message_box = QMessageBox(self)
            message_box.setIcon(QMessageBox.Icon.Information)
            message_box.setWindowTitle("Export Complete")
            message_box.setText(f"Saved PDF report to:\n{output_path}")
            message_box.setStandardButtons(QMessageBox.StandardButton.Ok)

            message_box.setStyleSheet("""
            QMessageBox {
            background-color: #0f1822;
            }

            QLabel {
            color: #d3dbe5;
            font-size: 12px;
            }

            QPushButton {
            background-color: #1a2330;
            color: #aab4c0;
            border: 1px solid #344152;
            padding: 6px 14px;
            min-width: 60px;
            }

            QPushButton:hover {
            color: #f5f7fa;
            }
            """)

            message_box.exec()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Could not export PDF.\n\n{error}",
            )
        finally:
            if temporary_chart_path:
                temporary_path_object = Path(temporary_chart_path)
                if temporary_path_object.exists():
                    temporary_path_object.unlink()

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

    def _toggle_chart_section(self):
        self.is_chart_expanded = not self.is_chart_expanded
        self.app_state.chart_expanded = self.is_chart_expanded
        self.save_ui_state_callback()

        if hasattr(self, "chart_content_widget"):
            self.chart_content_widget.setVisible(self.is_chart_expanded)

        if hasattr(self, "chart_toggle_button"):
            self.chart_toggle_button.setText(
                "▼ CHART" if self.is_chart_expanded else "▶ CHART"
            )

    def _toggle_table_section(self):
        self.is_table_expanded = not self.is_table_expanded
        self.app_state.table_expanded = self.is_table_expanded
        self.save_ui_state_callback()

        if hasattr(self, "table_content_widget"):
            self.table_content_widget.setVisible(self.is_table_expanded)

        if hasattr(self, "table_toggle_button"):
            self.table_toggle_button.setText(
                "▼ PERFORMANCE TABLE"
                if self.is_table_expanded
                else "▶ PERFORMANCE TABLE"
            )

    def _build_section_toggle_button(self, text: str, click_handler) -> QPushButton:
        toggle_button = QPushButton(text)
        toggle_button.setObjectName("sectionToggleButton")
        toggle_button.clicked.connect(click_handler)
        return toggle_button

    def _build_section_header_row(self, toggle_button: QPushButton) -> QWidget:
        header_row = QWidget()

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_row.setLayout(header_layout)

        header_layout.addWidget(toggle_button)
        header_layout.addStretch(1)

        return header_row

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

        best_score = summary_stats["best_score"]
        median_score = summary_stats["median_score"]

        overall_best_subtext = ""
        if median_score and median_score > 0:
            difference_percent = ((best_score - median_score) / median_score) * 100
            overall_best_subtext = f"{difference_percent:+.1f}% vs median"

        stat_cards = [
            {
                "title": "OVERALL BEST",
                "value": fmt_score(best_score),
                "value_style": "heroGoldValue",
                "secondary_text": overall_best_subtext,
                "secondary_style": "positiveSecondaryValue",
                "allow_wrap": False,
            },
            {
                "title": "CM FOR BEST",
                "value": summary_stats["cm_for_best_label"],
                "value_style": "heroAccentValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": False,
            },
            {
                "title": "BEST CROSSHAIR",
                "value": summary_stats["best_crosshair_label"],
                "value_style": "heroAccentValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": True,
            },
            {
                "title": "MEDIAN",
                "value": fmt_score(median_score),
                "value_style": "heroDefaultValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": False,
            },
            {
                "title": "TOTAL PLAYS",
                "value": str(summary_stats["total_plays"]),
                "value_style": "defaultValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": False,
            },
            {
                "title": "EST. BEST CM",
                "value": summary_stats["estimated_best_label"],
                "value_style": "greenValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": True,
            },
            {
                "title": "WORST CM",
                "value": summary_stats["worst_cm_label"],
                "value_style": "worstValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": True,
            },
            {
                "title": "NEXT CM TO TEST",
                "value": summary_stats["next_cm_label"],
                "value_style": "greenValue",
                "secondary_text": "",
                "secondary_style": "statSecondaryText",
                "allow_wrap": True,
            },
        ]

        for stat_index, stat_data in enumerate(stat_cards):
            row_index = stat_index // 4
            column_index = stat_index % 4

            stat_card = self._build_stat_card(
                title_text=stat_data["title"],
                value_text=stat_data["value"],
                value_style=stat_data["value_style"],
                secondary_text=stat_data["secondary_text"],
                secondary_style=stat_data["secondary_style"],
                allow_wrap=stat_data["allow_wrap"],
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

        self.chart_toggle_button = self._build_section_toggle_button(
            "▼ CHART" if self.is_chart_expanded else "▶ CHART",
            self._toggle_chart_section,
        )
        header_row = self._build_section_header_row(self.chart_toggle_button)

        self.chart_content_widget = QWidget()
        chart_content_layout = QVBoxLayout()
        chart_content_layout.setContentsMargins(0, 0, 0, 0)
        chart_content_layout.setSpacing(0)
        self.chart_content_widget.setLayout(chart_content_layout)

        self.chart_widget = ScoreChartWidget(by_cm_scores=by_cm_scores)
        self.chart_widget.setMinimumHeight(260)

        chart_content_layout.addWidget(self.chart_widget)
        self.chart_content_widget.setVisible(self.is_chart_expanded)

        layout.addWidget(header_row)
        layout.addWidget(self.chart_content_widget)

        return container

    def _build_table_card(self, by_cm_scores: dict) -> QWidget:
        container = QFrame()
        container.setObjectName("tableSectionCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        container.setLayout(layout)

        self.table_toggle_button = self._build_section_toggle_button(
            "▼ PERFORMANCE TABLE" if self.is_table_expanded else "▶ PERFORMANCE TABLE",
            self._toggle_table_section,
        )
        header_row = self._build_section_header_row(self.table_toggle_button)

        self.table_content_widget = QWidget()
        table_content_layout = QVBoxLayout()
        table_content_layout.setContentsMargins(0, 0, 0, 0)
        table_content_layout.setSpacing(0)
        self.table_content_widget.setLayout(table_content_layout)

        table_widget = SensitivityTableWidget(by_cm_scores=by_cm_scores)
        table_widget.setMinimumHeight(260)

        table_content_layout.addWidget(table_widget)
        self.table_content_widget.setVisible(self.is_table_expanded)

        layout.addWidget(header_row)
        layout.addWidget(self.table_content_widget)

        return container

    def _build_stat_card(
        self,
        title_text: str,
        value_text: str,
        value_style: str,
        secondary_text: str = "",
        secondary_style: str = "statSecondaryText",
        allow_wrap: bool = False,
    ) -> QWidget:
        container = QFrame()
        container.setObjectName("statCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(3)
        container.setLayout(layout)

        title_label = QLabel(title_text)
        title_label.setObjectName("statTitle")

        value_label = QLabel(value_text)
        value_label.setObjectName(value_style)
        value_label.setWordWrap(allow_wrap)
        value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        if secondary_text:
            secondary_label = QLabel(secondary_text)
            secondary_label.setObjectName(secondary_style)
            secondary_label.setWordWrap(False)
            layout.addWidget(secondary_label)

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
      
      #tableSectionCard {
        background: #131a24;
        border: none;
        }

        #sectionHeadingAccent {
        color: #81ecff;
        font-size: 11px;
        font-weight: 700;
        }

      #sectionCard {
        background: #0f1822;
        border: 1px solid #344152;
      }

      #sectionHeading {
        color: #d3dbe5;
        font-size: 12px;
        font-weight: 700;
      }

      #filterLabel {
        color: #c4ced9;
        font-size: 12px;
        font-weight: 600;
      }

      #statCard {
        background: #16202c;
        border: 1px solid #344152;
        min-height: 90px;
        max-height: 110px;
      }

      #statTitle {
        color: #aab4c0;
        font-size: 10px;
        font-weight: 700;
      }

      #heroGoldValue {
        color: #e8d84a;
        font-size: 24px;
        font-weight: 800;
      }

      #heroAccentValue {
        color: #5fd6ff;
        font-size: 24px;
        font-weight: 800;
      }

      #heroDefaultValue {
        color: #ffffff;
        font-size: 24px;
        font-weight: 800;
      }

      #goldValue {
        color: #e8d84a;
        font-size: 18px;
        font-weight: 700;
      }

      #accentValue {
        color: #3fbcde;
        font-size: 18px;
        font-weight: 700;
      }

      #greenValue {
        color: #01986f;
        font-size: 18px;
        font-weight: 700;
      }

      #defaultValue {
        color: #f5f7fa;
        font-size: 18px;
        font-weight: 700;
      }

      #worstValue {
        color: #ff5c93;
        font-size: 18px;
        font-weight: 700;
      }

      #statSecondaryText {
        color: #7f8fa3;
        font-size: 10px;
        font-weight: 600;
      }

      #positiveSecondaryValue {
        color: #01986f;
        font-size: 10px;
        font-weight: 700;
      }

      QLineEdit {
        background: #1a2330;
        color: #f5f7fa;
        border: 1px solid #3f4f63;
        padding: 6px 8px;
        font-size: 12px;
      }

      QCheckBox {
        color: #d3dbe5;
        font-size: 12px;
        font-weight: 600;
      }

      QPushButton {
        background: #1a2330;
        color: #aab4c0;
        border: 1px solid #344152;
        padding: 6px 10px;
      }

      QPushButton#sectionToggleButton {
        background: transparent;
        color: #d3dbe5;
        border: none;
        padding: 0;
        text-align: left;
        font-size: 12px;
        font-weight: 700;
      }

      QPushButton#sectionToggleButton:hover {
        color: #f5f7fa;
        border: none;
      }
      """
        )

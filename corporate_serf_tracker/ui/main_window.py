import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from corporate_serf_tracker.constants import DEFAULT_STATS_PATH, MAX_SELECTED
from corporate_serf_tracker.parsing import load_folder
from corporate_serf_tracker.services.app_state import AppState
from corporate_serf_tracker.storage import load_data
from corporate_serf_tracker.ui.scenario_tab import ScenarioTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState(max_selected=MAX_SELECTED)
        self.storage = load_data()

        persisted_ui_state = self.storage.get("ui_state", {})
        self.state.apply_persisted_dict(persisted_ui_state)
        self.visible_scenario_names = []
        self.search_placeholder_text = "Search scenarios..."

        self.setWindowTitle("Kovaaks Sensitivity Performance Tracker")
        self.resize(1400, 820)
        self.setMinimumSize(980, 640)

        self._build_window()
        self._apply_styles()
        self._attempt_default_load()

    def _build_window(self):
        self._build_status_bar()
        self._build_central_layout()
        self._build_menu()

    def _build_status_bar(self):
        status_bar = QStatusBar()
        status_bar.showMessage("Ready")
        self.setStatusBar(status_bar)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")

        select_folder_action = QAction("Select Stats Folder", self)
        select_folder_action.triggered.connect(self._select_folder)
        file_menu.addAction(select_folder_action)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh)
        file_menu.addAction(refresh_action)

    def _build_central_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        central_widget.setLayout(root_layout)

        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar, 0)

        divider = QFrame()
        divider.setObjectName("dividerLine")
        divider.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(divider, 0)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setObjectName("mainSplitter")

        sidebar = self._build_sidebar()
        main_panel = self._build_main_panel()

        main_splitter.addWidget(sidebar)
        main_splitter.addWidget(main_panel)
        main_splitter.setSizes([320, 1080])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        root_layout.addWidget(main_splitter, 1)

    def _build_top_bar(self) -> QWidget:
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(74)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        top_bar.setLayout(layout)

        title_container = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        title_container.setLayout(title_layout)

        title_label = QLabel("Kovaaks Sensitivity Performance Tracker")
        title_label.setObjectName("titleLabel")

        subtitle_label = QLabel("Inspired by the Corporate Serf method")
        subtitle_label.setObjectName("subtitleLabel")

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)

        layout.addWidget(title_container)
        layout.addStretch(1)

        self.folder_label = QLabel("Waiting for stats folder...")
        self.folder_label.setObjectName("folderLabel")
        self.folder_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh)

        select_folder_button = QPushButton("Select Stats Folder")
        select_folder_button.setObjectName("primaryButton")
        select_folder_button.clicked.connect(self._select_folder)

        layout.addWidget(self.folder_label)
        layout.addWidget(refresh_button)
        layout.addWidget(select_folder_button)

        return top_bar

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(380)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        sidebar.setLayout(layout)

        header_label = QLabel("SCENARIOS")
        header_label.setObjectName("sectionHeader")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.search_placeholder_text)
        self.search_input.textChanged.connect(self._populate_scenario_list)

        self.selected_count_label = QLabel(self.state.selected_count_label())
        self.selected_count_label.setObjectName("selectedCountLabel")
        self.selected_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.scenario_count_label = QLabel("0 scenarios")
        self.scenario_count_label.setObjectName("scenarioCountLabel")

        layout.addWidget(header_label)
        layout.addWidget(self.search_input)
        layout.addWidget(self.selected_count_label)
        layout.addWidget(self.scenario_count_label)

        divider = QFrame()
        divider.setObjectName("dividerLine")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)

        self.scenario_list_widget = QListWidget()
        self.scenario_list_widget.itemClicked.connect(self._handle_scenario_clicked)
        layout.addWidget(self.scenario_list_widget, 1)

        return sidebar

    def _build_main_panel(self) -> QWidget:
        self.main_panel = QFrame()
        self.main_panel.setObjectName("mainPanel")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.main_panel.setLayout(layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._handle_tab_changed)
        self.tab_widget.setTabsClosable(True)

        self.tab_widget.tabCloseRequested.connect(self._handle_tab_close_requested)

        self.empty_state_container = self._build_empty_state()

        layout.addWidget(self.empty_state_container)
        layout.addWidget(self.tab_widget)

        self._update_main_panel_visibility()
        return self.main_panel

    def _build_empty_state(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container.setLayout(layout)

        icon_label = QLabel("◈")
        icon_label.setObjectName("emptyStateIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("NO SCENARIOS SELECTED")
        title_label.setObjectName("emptyStateTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body_label = QLabel(
            "Load your stats folder and select up to 5 scenarios\nfrom the sidebar to begin charting your sensitivity stats."
        )
        body_label.setObjectName("emptyStateBody")
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(body_label)

        return container

    def _apply_styles(self):
        self.setStyleSheet(
            """
      QMainWindow {
        background: #0b0f14;
        color: #f5f7fa;
      }

      QMenuBar {
        background: #131a24;
        color: #f5f7fa;
      }

      QMenuBar::item:selected {
        background: #1a2330;
      }

      QMenu {
        background: #131a24;
        color: #f5f7fa;
      }

      QMenu::item:selected {
        background: #1a2330;
      }

      QStatusBar {
        background: #131a24;
        color: #aab4c0;
      }

      #topBar {
        background: #131a24;
        border-bottom: 1px solid #344152;
      }

      #titleLabel {
        color: #3fbcde;
        font-size: 14px;
        font-weight: 700;
      }

      #subtitleLabel {
        color: #aab4c0;
        font-size: 10px;
      }

      #folderLabel {
        color: #aab4c0;
        font-size: 12px;
        padding-right: 8px;
      }

      #sidebar {
        background: #101720;
        border-right: 1px solid #344152;
      }

      #mainPanel {
        background: #0b0f14;
      }

      #sectionHeader {
        color: #aab4c0;
        font-size: 11px;
        font-weight: 700;
      }

      #selectedCountLabel {
        color: #01986f;
        font-size: 12px;
        font-weight: 700;
      }

      #scenarioCountLabel {
        color: #aab4c0;
        font-size: 12px;
      }

      #dividerLine {
        background: #344152;
        color: #344152;
        border: none;
        max-height: 1px;
      }

      QPushButton {
        background: #1a2330;
        color: #f5f7fa;
        border: 1px solid #344152;
        padding: 6px 10px;
      }

      QPushButton:hover {
        border: 1px solid #3fbcde;
      }

      QPushButton#primaryButton {
        color: #3fbcde;
        font-weight: 700;
      }

      QLineEdit {
        background: #1a2330;
        color: #f5f7fa;
        border: 1px solid #344152;
        padding: 7px 8px;
      }

      QListWidget {
        background: #0f1822;
        color: #f5f7fa;
        border: 1px solid #344152;
        outline: none;
        padding: 4px;
      }

      QListWidget::item {
        padding: 8px 10px;
        margin: 1px 0;
      }

      QListWidget::item:selected {
        background: #22334a;
        color: #3fbcde;
      }

      QTabWidget::pane {
        border: 1px solid #344152;
        background: #0f1822;
        top: -1px;
      }

      QTabBar::tab {
        background: #131a24;
        color: #aab4c0;
        padding: 8px 12px;
        border: 1px solid #344152;
        margin-right: 2px;
      }

      QTabBar::tab:selected {
        background: #0f1822;
        color: #3fbcde;
      }

      #emptyStateIcon {
        color: #627082;
        font-size: 44px;
      }

      #emptyStateTitle {
        color: #aab4c0;
        font-size: 15px;
        font-weight: 700;
      }

      #emptyStateBody {
        color: #627082;
        font-size: 12px;
      }
      
      QScrollBar:vertical {
  background: #0f1822;
  width: 10px;
  border: none;
  margin: 0;
}

QScrollBar::handle:vertical {
  background: #22334a;
  min-height: 28px;
  border: none;
}

QScrollBar::handle:vertical:hover {
  background: #2b3f59;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
  height: 0;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
  background: transparent;
}

QScrollBar:horizontal {
  background: #0f1822;
  height: 10px;
  border: none;
  margin: 0;
}

QScrollBar::handle:horizontal {
  background: #22334a;
  min-width: 28px;
  border: none;
}

QScrollBar::handle:horizontal:hover {
  background: #2b3f59;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
  width: 0;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
  background: transparent;
}
      
      """
        )

    def _save_ui_state(self):
        self.storage["ui_state"] = self.state.to_persisted_dict()
        from corporate_serf_tracker.storage import save_data
        save_data(self.storage)

    def _attempt_default_load(self):
        saved_folder_path = self.state.folder_path

        if saved_folder_path and os.path.exists(saved_folder_path):
            self._load_folder()
            return

        if os.path.exists(DEFAULT_STATS_PATH):
            self.state.set_folder_path(DEFAULT_STATS_PATH)
            self._load_folder()

    def _select_folder(self):
        start_directory = DEFAULT_STATS_PATH
        if not os.path.exists(start_directory):
            start_directory = str(Path.home())

        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Select KovaaK's Stats Folder",
            start_directory,
        )

        if not selected_folder:
            return

        self.state.set_folder_path(selected_folder)
        self._save_ui_state()
        self._load_folder()

    def _refresh(self):
        if not self.state.folder_path:
            self._select_folder()
            return

        self._load_folder()

    def _load_folder(self):
        if not self.state.folder_path:
            return

        self.statusBar().showMessage("Loading stats folder...")
        self.folder_label.setText("Loading...")

        try:
            loaded_scenarios = load_folder(self.state.folder_path)
        except Exception as error:
            self.folder_label.setText("Load failed")
            self.statusBar().showMessage("Failed to load stats folder")
            QMessageBox.critical(
                self,
                "Load Error",
                f"Could not load stats folder.\n\n{error}",
            )
            return

        self.state.set_scenarios(loaded_scenarios)

        folder_name = Path(self.state.folder_path).name
        scenario_count = len(self.state.all_scenarios)
        self.folder_label.setText(f"{folder_name} ({scenario_count} scenarios)")
        self.statusBar().showMessage(f"Loaded {scenario_count} scenarios")

        self._populate_scenario_list()
        self._rebuild_tabs()

    def _populate_scenario_list(self):
        search_text = self.search_input.text()
        self.visible_scenario_names = self.state.filtered_scenario_names(search_text)

        self.scenario_list_widget.clear()

        for scenario_name in self.visible_scenario_names:
            play_count = len(self.state.all_scenarios.get(scenario_name, []))
            item_text = f"{scenario_name} ({play_count})"

            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, scenario_name)

            self.scenario_list_widget.addItem(list_item)

        self.scenario_count_label.setText(
            self.state.scenario_count_label(len(self.visible_scenario_names))
        )
        self.selected_count_label.setText(self.state.selected_count_label())
        self._sync_list_selection_state()

    def _sync_list_selection_state(self):
        for item_index in range(self.scenario_list_widget.count()):
            list_item = self.scenario_list_widget.item(item_index)
            scenario_name = list_item.data(Qt.ItemDataRole.UserRole)

            if scenario_name in self.state.selected_scenarios:
                list_item.setSelected(True)
            else:
                list_item.setSelected(False)

    def _handle_scenario_clicked(self, list_item: QListWidgetItem):
        scenario_name = list_item.data(Qt.ItemDataRole.UserRole)

        selection_succeeded, is_now_selected = self.state.toggle_scenario(scenario_name)
        if not selection_succeeded:
            QMessageBox.information(
                self,
                "Selection Limit",
                f"Max {self.state.max_selected} scenarios. Remove one first.",
            )
            self._sync_list_selection_state()
            return

        if is_now_selected:
            self.statusBar().showMessage(f"Selected {scenario_name}")
        else:
            self.statusBar().showMessage(f"Removed {scenario_name}")

        self.selected_count_label.setText(self.state.selected_count_label())
        self._save_ui_state()
        self._rebuild_tabs()
        self._sync_list_selection_state()

    def _handle_tab_close_requested(self, tab_index: int):
        if tab_index < 0:
            return

        if tab_index >= len(self.state.selected_scenarios):
            return

        scenario_name = self.state.selected_scenarios[tab_index]
        self.state.deselect_scenario(scenario_name)

        self.selected_count_label.setText(self.state.selected_count_label())
        self._save_ui_state()
        self._rebuild_tabs()
        self._sync_list_selection_state()
        self.statusBar().showMessage(f"Closed {scenario_name}")

    def _rebuild_tabs(self):
        self.tab_widget.clear()

        for scenario_name in self.state.selected_scenarios:
            plays = self.state.all_scenarios.get(scenario_name, [])
            assignments = self.storage.get("assignments", {}).get(scenario_name, {})
            ranks = self.storage.get("ranks", {}).get(scenario_name, {})

            scenario_tab = ScenarioTab(
                scenario_name=scenario_name,
                plays=plays,
                assignments=assignments,
                ranks=ranks,
                app_state=self.state,
                save_ui_state_callback=self._save_ui_state,
            )
            tab_label = self._format_tab_name(scenario_name)
            self.tab_widget.addTab(scenario_tab, tab_label)

        if self.state.active_tab_name:
            for tab_index in range(self.tab_widget.count()):
                if (
                    self.state.selected_scenarios[tab_index]
                    == self.state.active_tab_name
                ):
                    self.tab_widget.setCurrentIndex(tab_index)
                    break

        self._update_main_panel_visibility()

    def _update_main_panel_visibility(self):
        has_selected_scenarios = len(self.state.selected_scenarios) > 0
        self.empty_state_container.setVisible(not has_selected_scenarios)
        self.tab_widget.setVisible(has_selected_scenarios)

    def _handle_tab_changed(self, tab_index: int):
        if tab_index < 0:
            return

        if tab_index >= len(self.state.selected_scenarios):
            return

        self.state.active_tab_name = self.state.selected_scenarios[tab_index]
        self._save_ui_state()

    def _format_tab_name(self, scenario_name: str) -> str:
        max_length = 28
        if len(scenario_name) <= max_length:
            return f"  {scenario_name}  "

        return f"  {scenario_name[:max_length]}…  "

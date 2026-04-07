import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
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
from corporate_serf_tracker.ui.sidebar_panel import SidebarPanel
from corporate_serf_tracker.ui.scenario_tab import ScenarioTab


# MainWindow coordinates app-level loading, sidebar actions, and scenario tabs.
class MainWindow(QMainWindow):
    # __init__ restores persisted state and builds the main application shell.
    def __init__(self):
        super().__init__()
        self.state = AppState(max_selected=MAX_SELECTED)
        self.storage = load_data()

        persisted_ui_state = self.storage.get("ui_state", {})
        self.state.apply_persisted_dict(persisted_ui_state)
        self.search_placeholder_text = "Search scenarios..."

        self.setWindowTitle("Kovaaks Sensitivity Performance Tracker")
        self.resize(1400, 820)
        self.setMinimumSize(980, 640)

        self._build_window()
        self._apply_styles()
        self._attempt_default_load()

    # _build_window creates the top-level window structure.
    def _build_window(self):
        self._build_status_bar()
        self._build_central_layout()

    # _build_status_bar creates the footer status messaging area.
    def _build_status_bar(self):
        status_bar = QStatusBar()
        status_bar.showMessage("Ready")
        self.setStatusBar(status_bar)

    # _build_menu defines the legacy menu actions for folder loading and refresh.
    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")

        select_folder_action = QAction("Select Stats Folder", self)
        select_folder_action.triggered.connect(self._select_folder)
        file_menu.addAction(select_folder_action)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh)
        file_menu.addAction(refresh_action)

    # _build_central_layout creates the top bar, sidebar, and main panel split view.
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

    # _build_top_bar creates the title and folder controls above the main split view.
    def _build_top_bar(self) -> QWidget:
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(52)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        top_bar.setLayout(layout)

        title_label = QLabel("Kovaaks Sensitivity Performance Tracker")
        title_label.setObjectName("titleLabel")

        subtitle_label = QLabel("Inspired by the Corporate Serf method")
        subtitle_label.setObjectName("subtitleLabel")

        title_row = QWidget()
        title_row_layout = QHBoxLayout()
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(10)
        title_row.setLayout(title_row_layout)

        title_row_layout.addWidget(title_label)
        title_row_layout.addWidget(subtitle_label)

        layout.addWidget(title_row)
        layout.addStretch(1)

        self.folder_label = QLabel("Waiting for stats folder...")
        self.folder_label.setObjectName("folderLabel")
        self.folder_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("toolbarButton")
        refresh_button.clicked.connect(self._refresh)

        select_folder_button = QPushButton("Select Stats Folder")
        select_folder_button.setObjectName("primaryButton")
        select_folder_button.clicked.connect(self._select_folder)

        layout.addWidget(self.folder_label)
        layout.addWidget(refresh_button)
        layout.addWidget(select_folder_button)

        return top_bar

    # _build_sidebar creates the modular sidebar panel used for search and favorites.
    def _build_sidebar(self) -> QWidget:
        self.sidebar_panel = SidebarPanel(self.search_placeholder_text, self)
        self.sidebar_panel.refresh_requested.connect(self._refresh_sidebar)
        self.sidebar_panel.scenario_clicked.connect(self._handle_scenario_clicked)
        self.sidebar_panel.favorite_toggled.connect(self._handle_favorite_toggled)
        return self.sidebar_panel

    # _build_main_panel creates the tab container and empty state region.
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

    # _build_empty_state creates the placeholder shown when no scenarios are selected.
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

    # _apply_styles applies the shared application stylesheet for all widgets.
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
        background: #111923;
        border-bottom: 1px solid #344152;
      }

      #titleLabel {
        color: #3fbcde;
        font-size: 15px;
        font-weight: 700;
      }

      #subtitleLabel {
        color: #aab4c0;
        font-size: 11px;
      }

      #folderLabel {
        color: #aab4c0;
        font-size: 11px;
        padding: 4px 8px;
      }

      QPushButton#toolbarButton {
        background: #1a2330;
        color: #d3dbe5;
        border: 1px solid #344152;
        padding: 5px 10px;
      }

      QPushButton#toolbarButton:hover {
        border: 1px solid #3fbcde;
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

      #sectionSubHeader {
        color: #7e8b99;
        font-size: 10px;
        font-weight: 700;
        padding-top: 4px;
      }

      #sectionEmptyLabel {
        color: #627082;
        font-size: 11px;
        padding: 2px 0 6px 0;
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

      QListWidget,
      QListWidget#scenarioSectionList {
        background: #0f1822;
        color: #f5f7fa;
        border: 1px solid #344152;
        outline: none;
        padding: 4px;
      }

      QListWidget::item,
      QListWidget#scenarioSectionList::item {
        padding: 8px 10px;
        margin: 1px 0;
      }

      QListWidget::item:selected,
      QListWidget#scenarioSectionList::item:selected {
        background: #22334a;
        color: #3fbcde;
      }

      #scenarioRow {
        background: #15202d;
        border: 1px solid #1f2b39;
      }

      #scenarioRow:hover {
        border: 1px solid #3fbcde;
      }

      #scenarioRow[selectedState="true"] {
        background: #22334a;
        border: 1px solid #3fbcde;
      }

      #scenarioRowName {
        color: #f5f7fa;
      }

      #scenarioRowCount {
        color: #aab4c0;
        min-width: 24px;
        padding-left: 10px;
      }

      QPushButton#favoriteToggleButton {
        background: transparent;
        min-width: 16px;
        max-width: 16px;
        min-height: 16px;
        max-height: 16px;
        padding: 0;
        font-size: 14px;
        font-weight: 700;
        border: none;
      }

      QPushButton#favoriteToggleButton[favoriteState="true"] {
        color: #f0d24a;
        border: none;
      }

      QPushButton#favoriteToggleButton[favoriteState="false"] {
        color: #7e8b99;
        border: none;
      }

      QPushButton#favoriteToggleButton:hover {
        color: #f0d24a;
        border: none;
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

    # _save_ui_state persists the latest UI state to the storage service.
    def _save_ui_state(self):
        self.storage["ui_state"] = self.state.to_persisted_dict()
        from corporate_serf_tracker.storage import save_data

        save_data(self.storage)

    # _attempt_default_load reopens the previous or default stats folder when possible.
    def _attempt_default_load(self):
        saved_folder_path = self.state.folder_path

        if saved_folder_path and os.path.exists(saved_folder_path):
            self._load_folder()
            return

        if os.path.exists(DEFAULT_STATS_PATH):
            self.state.set_folder_path(DEFAULT_STATS_PATH)
            self._load_folder()

    # _select_folder prompts the user for a new stats folder and reloads the app state.
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

    # _refresh reloads the currently selected stats folder or prompts for one.
    def _refresh(self):
        if not self.state.folder_path:
            self._select_folder()
            return

        self._load_folder()

    # _load_folder parses the active stats folder and refreshes the sidebar and tabs.
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
        self._save_ui_state()

        scenario_count = len(self.state.all_scenarios)
        self.folder_label.setText(f"{scenario_count} scenarios")
        self.statusBar().showMessage(f"Loaded {scenario_count} scenarios")

        self._refresh_sidebar()
        self._rebuild_tabs()

    # _refresh_sidebar repopulates the modular sidebar from the current AppState.
    def _refresh_sidebar(self):
        self.sidebar_panel.refresh(self.state)

    # _handle_scenario_clicked reuses the existing tab-selection rules for sidebar clicks.
    def _handle_scenario_clicked(self, scenario_name: str):
        selection_succeeded, is_now_selected = self.state.toggle_scenario(scenario_name)
        if not selection_succeeded:
            QMessageBox.information(
                self,
                "Selection Limit",
                f"Max {self.state.max_selected} scenarios. Remove one first.",
            )
            self._refresh_sidebar()
            return

        self._save_ui_state()

        if is_now_selected:
            scenario_tab = self._create_scenario_tab(scenario_name)
            tab_label = self._format_tab_name(scenario_name)
            new_tab_index = self.tab_widget.addTab(scenario_tab, tab_label)
            self.tab_widget.setCurrentIndex(new_tab_index)
            self.statusBar().showMessage(f"Selected {scenario_name}")
        else:
            self._remove_tab_by_name(scenario_name)
            self.statusBar().showMessage(f"Removed {scenario_name}")

        self._update_main_panel_visibility()
        self._refresh_sidebar()

    # _handle_favorite_toggled updates favorite state from the modular sidebar rows.
    def _handle_favorite_toggled(self, scenario_name: str, is_favorite: bool):
        if is_favorite:
            self.state.add_favorite(scenario_name)
            self.statusBar().showMessage(f"Pinned {scenario_name}")
        else:
            self.state.remove_favorite(scenario_name)
            self.statusBar().showMessage(f"Unpinned {scenario_name}")

        self._save_ui_state()
        self._refresh_sidebar()

    # _remove_tab_by_name closes the tab associated with a scenario name.
    def _remove_tab_by_name(self, scenario_name: str):
        for tab_index in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(tab_index)

            if getattr(tab_widget, "scenario_name", None) == scenario_name:
                widget_to_remove = self.tab_widget.widget(tab_index)
                self.tab_widget.removeTab(tab_index)

                if widget_to_remove is not None:
                    widget_to_remove.deleteLater()
                break

    # _handle_tab_close_requested removes a tab and updates the shared selection state.
    def _handle_tab_close_requested(self, tab_index: int):
        if tab_index < 0:
            return

        tab_widget = self.tab_widget.widget(tab_index)
        scenario_name = getattr(tab_widget, "scenario_name", None)

        if not scenario_name:
            return

        self.state.deselect_scenario(scenario_name)

        widget_to_remove = self.tab_widget.widget(tab_index)
        self.tab_widget.removeTab(tab_index)

        if widget_to_remove is not None:
            widget_to_remove.deleteLater()

        self._save_ui_state()
        self._update_main_panel_visibility()
        self._refresh_sidebar()
        self.statusBar().showMessage(f"Closed {scenario_name}")

    # _rebuild_tabs recreates tabs from persisted selection state after a folder reload.
    def _rebuild_tabs(self):
        self.tab_widget.clear()

        for scenario_name in self.state.selected_scenarios:
            scenario_tab = self._create_scenario_tab(scenario_name)
            tab_label = self._format_tab_name(scenario_name)
            self.tab_widget.addTab(scenario_tab, tab_label)

        if self.state.active_tab_name:
            for tab_index in range(self.tab_widget.count()):
                tab_widget = self.tab_widget.widget(tab_index)
                if (
                    getattr(tab_widget, "scenario_name", None)
                    == self.state.active_tab_name
                ):
                    self.tab_widget.setCurrentIndex(tab_index)
                    break

        self._update_main_panel_visibility()
        self._refresh_sidebar()

    # _create_scenario_tab builds one ScenarioTab from loaded plays and stored metadata.
    def _create_scenario_tab(self, scenario_name: str) -> ScenarioTab:
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
            parent=self.tab_widget,
        )
        return scenario_tab

    # _update_main_panel_visibility switches between the empty state and tab view.
    def _update_main_panel_visibility(self):
        has_selected_scenarios = len(self.state.selected_scenarios) > 0
        self.empty_state_container.setVisible(not has_selected_scenarios)
        self.tab_widget.setVisible(has_selected_scenarios)

    # _handle_tab_changed persists the currently focused scenario tab.
    def _handle_tab_changed(self, tab_index: int):
        if tab_index < 0:
            return

        if tab_index >= len(self.state.selected_scenarios):
            return

        self.state.active_tab_name = self.state.selected_scenarios[tab_index]
        self._save_ui_state()

    # _format_tab_name trims long scenario names for the tab bar.
    def _format_tab_name(self, scenario_name: str) -> str:
        max_length = 28
        if len(scenario_name) <= max_length:
            return f"  {scenario_name}  "

        return f"  {scenario_name[:max_length]}…  "

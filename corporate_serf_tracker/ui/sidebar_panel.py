from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from corporate_serf_tracker.services.app_state import AppState


# ScenarioRowWidget renders one scenario row and emits selection or favorite actions.
class ScenarioRowWidget(QFrame):
    # clicked notifies the parent list that the scenario row was activated.
    clicked = Signal(str)
    # favorite_toggled notifies the parent list that the pin state changed.
    favorite_toggled = Signal(str, bool)

    # __init__ builds a scenario row shared by favorites and all-scenarios sections.
    def __init__(
        self,
        scenario_name: str,
        play_count: int,
        is_selected: bool,
        is_favorite: bool,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        # scenario_name stores the scenario represented by this row.
        self.scenario_name = scenario_name
        # play_count stores the play total displayed beside the scenario name.
        self.play_count = play_count
        # favorite_button stores the star control rendered on the right side of the row.
        self.favorite_button = QPushButton(self)

        self.setObjectName("scenarioRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_layout()
        self.set_selected(is_selected)
        self.set_favorite(is_favorite)

    # _build_layout creates the shared name, count, and favorite control layout.
    def _build_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        self.setLayout(layout)
        self.setMinimumHeight(34)

        # name_label displays the full scenario name and can extend beyond the viewport.
        self.name_label = QLabel(self.scenario_name)
        self.name_label.setObjectName("scenarioRowName")
        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.name_label.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.Preferred,
        )

        # count_label displays the loaded play count for the scenario.
        self.count_label = QLabel(str(self.play_count))
        self.count_label.setObjectName("scenarioRowCount")
        self.count_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.count_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )

        self.favorite_button.setObjectName("favoriteToggleButton")
        self.favorite_button.setCursor(Qt.CursorShape.ArrowCursor)
        self.favorite_button.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.favorite_button.clicked.connect(self._handle_favorite_button_clicked)

        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.favorite_button, 0)
        layout.addStretch(0)
        layout.addWidget(self.count_label, 0)

    # _handle_favorite_button_clicked flips the pin state from the inline button.
    def _handle_favorite_button_clicked(self):
        next_favorite_state = not bool(self.favorite_button.property("favoriteState"))
        self.favorite_toggled.emit(self.scenario_name, next_favorite_state)

    # set_selected updates the visual state for scenarios with open tabs.
    def set_selected(self, is_selected: bool):
        self.setProperty("selectedState", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

    # set_favorite updates the star button label and style state.
    def set_favorite(self, is_favorite: bool):
        self.favorite_button.setProperty("favoriteState", is_favorite)
        self.favorite_button.setText("\u2605" if is_favorite else "\u2606")
        self.favorite_button.setToolTip(
            "Remove from favorites" if is_favorite else "Add to favorites"
        )
        self.favorite_button.style().unpolish(self.favorite_button)
        self.favorite_button.style().polish(self.favorite_button)

    # mousePressEvent turns row clicks into scenario activation signals.
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.scenario_name)

        super().mousePressEvent(event)

    # sizeHint gives QListWidgetItem a stable row height so labels are not vertically clipped.
    def sizeHint(self) -> QSize:
        name_width = self.fontMetrics().horizontalAdvance(self.scenario_name)
        count_width = self.count_label.fontMetrics().horizontalAdvance(
            self.count_label.text()
        )
        horizontal_padding = 72
        return QSize(name_width + count_width + horizontal_padding, 36)


# ScenarioListSection renders one labeled scenario list section in the sidebar.
class ScenarioListSection(QFrame):
    # scenario_clicked forwards row activation events to the owning sidebar panel.
    scenario_clicked = Signal(str)
    # favorite_toggled forwards row pin toggle events to the owning sidebar panel.
    favorite_toggled = Signal(str, bool)

    # __init__ builds a labeled list section reused for favorites and all scenarios.
    def __init__(
        self,
        title_text: str,
        empty_text: str,
        auto_fit_rows: bool,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        # empty_text stores the fallback message shown when the section has no visible rows.
        self.empty_text = empty_text
        # auto_fit_rows controls whether the list should shrink to the visible rows.
        self.auto_fit_rows = auto_fit_rows
        # row_widgets maps scenario names to their rendered row widgets for updates.
        self.row_widgets = {}

        self.setObjectName("scenarioSection")
        self._build_layout(title_text)

    # _build_layout creates the section header, empty state, and list container.
    def _build_layout(self, title_text: str):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.setLayout(layout)

        # section_label displays the section title above the list.
        self.section_label = QLabel(title_text)
        self.section_label.setObjectName("sectionSubHeader")

        # empty_label displays a compact message when the section is empty.
        self.empty_label = QLabel(self.empty_text)
        self.empty_label.setObjectName("sectionEmptyLabel")

        # list_widget contains the scenario row widgets for this section.
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("scenarioSectionList")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.list_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        if self.auto_fit_rows:
            self.list_widget.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )

        layout.addWidget(self.section_label)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.list_widget)

    # populate_rows replaces the rendered rows with the provided scenario names.
    def populate_rows(self, scenario_names: list, state: AppState):
        self.row_widgets = {}
        self.list_widget.clear()

        has_rows = len(scenario_names) > 0
        self.empty_label.setVisible(not has_rows)
        self.list_widget.setVisible(has_rows)

        for scenario_name in scenario_names:
            play_count = len(state.all_scenarios.get(scenario_name, []))
            row_widget = ScenarioRowWidget(
                scenario_name=scenario_name,
                play_count=play_count,
                is_selected=scenario_name in state.selected_scenarios,
                is_favorite=state.is_favorite(scenario_name),
                parent=self.list_widget,
            )
            row_widget.clicked.connect(self._handle_row_clicked)
            row_widget.favorite_toggled.connect(self._handle_favorite_toggled)

            list_item = QListWidgetItem()
            list_item.setSizeHint(row_widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, scenario_name)

            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, row_widget)
            self.row_widgets[scenario_name] = row_widget

        self._update_list_height()

    # _update_list_height keeps fitted sections compact and leaves scrolling to larger sections.
    def _update_list_height(self):
        if not self.auto_fit_rows:
            self.list_widget.setMinimumHeight(0)
            self.list_widget.setMaximumHeight(16777215)
            return

        if self.list_widget.count() == 0:
            self.list_widget.setFixedHeight(0)
            return

        row_height = self.list_widget.sizeHintForRow(0)
        frame_height = self.list_widget.frameWidth() * 2
        list_padding = 8
        visible_height = (row_height * self.list_widget.count()) + frame_height + list_padding
        self.list_widget.setFixedHeight(visible_height)

    # _handle_row_clicked forwards a row activation event to the parent sidebar.
    def _handle_row_clicked(self, scenario_name: str):
        self.scenario_clicked.emit(scenario_name)

    # _handle_favorite_toggled forwards a row pin event to the parent sidebar.
    def _handle_favorite_toggled(self, scenario_name: str, is_favorite: bool):
        self.favorite_toggled.emit(scenario_name, is_favorite)


# SidebarPanel owns the modular sidebar UI for search, favorites, and scenario lists.
class SidebarPanel(QFrame):
    # scenario_clicked notifies MainWindow to reuse the normal scenario selection flow.
    scenario_clicked = Signal(str)
    # favorite_toggled notifies MainWindow to update favorite state and persistence.
    favorite_toggled = Signal(str, bool)
    # refresh_requested asks MainWindow to rebuild sidebar contents for a new filter.
    refresh_requested = Signal()

    # __init__ builds the full sidebar control surface used by MainWindow.
    def __init__(self, search_placeholder_text: str, parent: QWidget = None):
        super().__init__(parent)
        # search_placeholder_text stores the default placeholder shown in the search box.
        self.search_placeholder_text = search_placeholder_text

        self.setObjectName("sidebar")
        self.setMinimumWidth(280)
        self.setMaximumWidth(380)
        self._build_layout()

    # _build_layout creates the sidebar header, counts, and both scenario sections.
    def _build_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.setLayout(layout)

        # header_label displays the top-level sidebar title.
        self.header_label = QLabel("SCENARIOS")
        self.header_label.setObjectName("sectionHeader")

        # search_input captures scenario filtering text for both sections.
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.search_placeholder_text)
        self.search_input.textChanged.connect(self._handle_search_text_changed)

        # selected_count_label displays the selected tab count summary.
        self.selected_count_label = QLabel("0 / 0 selected")
        self.selected_count_label.setObjectName("selectedCountLabel")
        self.selected_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # scenario_count_label displays the visible all-scenarios count summary.
        self.scenario_count_label = QLabel("0 scenarios")
        self.scenario_count_label.setObjectName("scenarioCountLabel")

        # favorites_section renders pinned scenarios above the full scenario list.
        self.favorites_section = ScenarioListSection(
            title_text="FAVORITES",
            empty_text="No favorites match the current filter.",
            auto_fit_rows=True,
            parent=self,
        )
        self.favorites_section.scenario_clicked.connect(self._handle_scenario_clicked)
        self.favorites_section.favorite_toggled.connect(self._handle_favorite_toggled)

        # all_scenarios_section renders the filtered scenario list below favorites.
        self.all_scenarios_section = ScenarioListSection(
            title_text="ALL SCENARIOS",
            empty_text="No scenarios match the current filter.",
            auto_fit_rows=False,
            parent=self,
        )
        self.all_scenarios_section.scenario_clicked.connect(self._handle_scenario_clicked)
        self.all_scenarios_section.favorite_toggled.connect(self._handle_favorite_toggled)

        # divider separates favorites from the full scenario list.
        self.divider = QFrame()
        self.divider.setObjectName("dividerLine")
        self.divider.setFrameShape(QFrame.Shape.HLine)

        layout.addWidget(self.header_label)
        layout.addWidget(self.search_input)
        layout.addWidget(self.selected_count_label)
        layout.addWidget(self.scenario_count_label)
        layout.addWidget(self.favorites_section)
        layout.addWidget(self.divider)
        layout.addWidget(self.all_scenarios_section, 1)

    # search_text returns the current sidebar filter string.
    def search_text(self) -> str:
        return self.search_input.text()

    # refresh rebuilds both scenario sections from AppState using the active search text.
    def refresh(self, state: AppState):
        visible_scenario_names = state.filtered_scenario_names(self.search_text())
        visible_scenario_name_set = set(visible_scenario_names)

        visible_favorite_names = []
        for scenario_name in state.favorite_names():
            if scenario_name in visible_scenario_name_set:
                visible_favorite_names.append(scenario_name)

        self.selected_count_label.setText(state.selected_count_label())
        self.scenario_count_label.setText(
            state.scenario_count_label(len(visible_scenario_names))
        )
        self.favorites_section.populate_rows(visible_favorite_names, state)
        self.all_scenarios_section.populate_rows(visible_scenario_names, state)

    # _handle_search_text_changed requests a sidebar refresh from MainWindow.
    def _handle_search_text_changed(self, _search_text: str):
        self.refresh_requested.emit()

    # _handle_scenario_clicked forwards row activation events to MainWindow.
    def _handle_scenario_clicked(self, scenario_name: str):
        self.scenario_clicked.emit(scenario_name)

    # _handle_favorite_toggled forwards row pin changes to MainWindow.
    def _handle_favorite_toggled(self, scenario_name: str, is_favorite: bool):
        self.favorite_toggled.emit(scenario_name, is_favorite)

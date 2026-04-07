from dataclasses import dataclass, field


# AppState stores UI state and scenario selection rules shared across the app.
@dataclass
class AppState:
    # all_scenarios maps scenario names to their loaded play history.
    all_scenarios: dict = field(default_factory=dict)
    # selected_scenarios tracks which scenarios currently have open tabs.
    selected_scenarios: list = field(default_factory=list)
    # favorite_scenarios tracks pinned scenarios shown at the top of the sidebar.
    favorite_scenarios: list = field(default_factory=list)
    # folder_path stores the active stats folder path for reloads.
    folder_path: str = ""
    # active_tab_name stores the currently focused scenario tab.
    active_tab_name: str = ""
    # max_selected limits how many scenario tabs can be open at once.
    max_selected: int = 5
    # show_all_cm stores whether the chart displays all sensitivities.
    show_all_cm: bool = False
    # last_8_only stores whether the chart is limited to recent plays.
    last_8_only: bool = False
    # chart_scale stores the persisted chart zoom factor.
    chart_scale: float = 1.0
    # chart_height stores the persisted chart height scaling.
    chart_height: float = 1.0
    # cm_range_min stores the persisted custom sensitivity range minimum.
    cm_range_min: str = ""
    # cm_range_max stores the persisted custom sensitivity range maximum.
    cm_range_max: str = ""
    # hidden_cms_by_scenario stores hidden sensitivity toggles per scenario.
    hidden_cms_by_scenario: dict = field(default_factory=dict)
    # chart_expanded stores whether the chart panel is expanded.
    chart_expanded: bool = True
    # table_expanded stores whether the table panel is expanded.
    table_expanded: bool = True
    # last_export_directory stores the most recent export destination.
    last_export_directory: str = ""

    # set_folder_path updates the current stats folder path.
    def set_folder_path(self, folder_path: str):
        self.folder_path = folder_path or ""

    # set_scenarios replaces loaded scenarios and removes invalid saved references.
    def set_scenarios(self, scenarios: dict):
        self.all_scenarios = scenarios or {}

        valid_selected_scenarios = []
        for scenario_name in self.selected_scenarios:
            if scenario_name in self.all_scenarios:
                valid_selected_scenarios.append(scenario_name)

        self.selected_scenarios = valid_selected_scenarios
        self.favorite_scenarios = self._validated_scenario_names(self.favorite_scenarios)

        if self.active_tab_name not in self.all_scenarios:
            self.active_tab_name = ""

    # _validated_scenario_names keeps only unique names that still exist in loaded data.
    def _validated_scenario_names(self, scenario_names: list) -> list:
        valid_scenario_names = []

        for scenario_name in scenario_names:
            if scenario_name not in self.all_scenarios:
                continue

            if scenario_name in valid_scenario_names:
                continue

            valid_scenario_names.append(scenario_name)

        return valid_scenario_names

    # scenario_names returns all loaded scenario names in sorted order.
    def scenario_names(self) -> list:
        return sorted(self.all_scenarios.keys())

    # favorite_names returns valid favorite scenario names in persisted order.
    def favorite_names(self) -> list:
        return self._validated_scenario_names(self.favorite_scenarios)

    # is_favorite reports whether a scenario is currently pinned.
    def is_favorite(self, scenario_name: str) -> bool:
        return scenario_name in self.favorite_scenarios

    # add_favorite pins a scenario when it exists in the loaded folder.
    def add_favorite(self, scenario_name: str):
        if scenario_name not in self.all_scenarios:
            return

        if scenario_name in self.favorite_scenarios:
            return

        self.favorite_scenarios.append(scenario_name)

    # remove_favorite unpins a scenario when present.
    def remove_favorite(self, scenario_name: str):
        if scenario_name not in self.favorite_scenarios:
            return

        self.favorite_scenarios.remove(scenario_name)

    # toggle_favorite flips the pinned state for a scenario and returns the new state.
    def toggle_favorite(self, scenario_name: str) -> bool:
        if self.is_favorite(scenario_name):
            self.remove_favorite(scenario_name)
            return False

        self.add_favorite(scenario_name)
        return self.is_favorite(scenario_name)

    # filtered_scenario_names returns visible scenario names for the active search text.
    def filtered_scenario_names(self, search_text: str) -> list:
        normalized_search_text = (search_text or "").strip().lower()
        all_scenario_names = self.scenario_names()

        if not normalized_search_text:
            return all_scenario_names

        matching_scenario_names = []
        for scenario_name in all_scenario_names:
            if normalized_search_text in scenario_name.lower():
                matching_scenario_names.append(scenario_name)

        return matching_scenario_names

    # select_scenario opens a scenario tab when within the selection limit.
    def select_scenario(self, scenario_name: str) -> bool:
        if scenario_name in self.selected_scenarios:
            return True

        if len(self.selected_scenarios) >= self.max_selected:
            return False

        self.selected_scenarios.append(scenario_name)
        return True

    # deselect_scenario closes a scenario tab and clears focus if needed.
    def deselect_scenario(self, scenario_name: str):
        if scenario_name in self.selected_scenarios:
            self.selected_scenarios.remove(scenario_name)

        if self.active_tab_name == scenario_name:
            self.active_tab_name = ""

    # toggle_scenario flips whether a scenario has an open tab.
    def toggle_scenario(self, scenario_name: str) -> tuple[bool, bool]:
        if scenario_name in self.selected_scenarios:
            self.deselect_scenario(scenario_name)
            return True, False

        selection_succeeded = self.select_scenario(scenario_name)
        return selection_succeeded, selection_succeeded

    # selected_count_label builds the sidebar label for the open-tab count.
    def selected_count_label(self) -> str:
        return f"{len(self.selected_scenarios)} / {self.max_selected} selected"

    # scenario_count_label builds the sidebar label for the visible search result count.
    def scenario_count_label(self, visible_count: int) -> str:
        return f"{visible_count} scenarios"

    # to_persisted_dict serializes the UI state stored in app_kv.ui_state.
    def to_persisted_dict(self) -> dict:
        return {
            "selected_scenarios": self.selected_scenarios,
            "favorite_scenarios": self.favorite_scenarios,
            "folder_path": self.folder_path,
            "active_tab_name": self.active_tab_name,
            "show_all_cm": self.show_all_cm,
            "last_8_only": self.last_8_only,
            "chart_scale": self.chart_scale,
            "chart_height": self.chart_height,
            "cm_range_min": self.cm_range_min,
            "cm_range_max": self.cm_range_max,
            "hidden_cms_by_scenario": self.hidden_cms_by_scenario,
            "chart_expanded": self.chart_expanded,
            "table_expanded": self.table_expanded,
            "last_export_directory": self.last_export_directory,
        }

    # apply_persisted_dict restores UI state loaded from app_kv.ui_state.
    def apply_persisted_dict(self, persisted_state: dict):
        self.selected_scenarios = persisted_state.get("selected_scenarios", [])
        self.favorite_scenarios = persisted_state.get("favorite_scenarios", [])
        self.folder_path = persisted_state.get("folder_path", "")
        self.active_tab_name = persisted_state.get("active_tab_name", "")
        self.show_all_cm = persisted_state.get("show_all_cm", False)
        self.last_8_only = persisted_state.get("last_8_only", False)
        self.chart_scale = persisted_state.get("chart_scale", 1.0)
        self.chart_height = persisted_state.get("chart_height", 1.0)
        self.cm_range_min = persisted_state.get("cm_range_min", "")
        self.cm_range_max = persisted_state.get("cm_range_max", "")
        self.hidden_cms_by_scenario = persisted_state.get(
            "hidden_cms_by_scenario",
            {},
        )
        self.chart_expanded = persisted_state.get("chart_expanded", True)
        self.table_expanded = persisted_state.get("table_expanded", True)
        self.last_export_directory = persisted_state.get("last_export_directory", "")

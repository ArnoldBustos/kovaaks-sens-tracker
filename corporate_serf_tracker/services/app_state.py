from dataclasses import dataclass, field


@dataclass
class AppState:
    all_scenarios: dict = field(default_factory=dict)
    selected_scenarios: list = field(default_factory=list)
    folder_path: str = ""
    active_tab_name: str = ""
    max_selected: int = 5
    show_all_cm: bool = False
    last_8_only: bool = False
    chart_scale: float = 1.0
    chart_height: float = 1.0
    cm_range_min: str = ""
    cm_range_max: str = ""
    hidden_cms_by_scenario: dict = field(default_factory=dict)

    def set_folder_path(self, folder_path: str):
        self.folder_path = folder_path or ""

    def set_scenarios(self, scenarios: dict):
        self.all_scenarios = scenarios or {}

        valid_selected_scenarios = []
        for scenario_name in self.selected_scenarios:
            if scenario_name in self.all_scenarios:
                valid_selected_scenarios.append(scenario_name)

        self.selected_scenarios = valid_selected_scenarios

        if self.active_tab_name not in self.all_scenarios:
            self.active_tab_name = ""

    def scenario_names(self) -> list:
        return sorted(self.all_scenarios.keys())

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

    def select_scenario(self, scenario_name: str) -> bool:
        if scenario_name in self.selected_scenarios:
            return True

        if len(self.selected_scenarios) >= self.max_selected:
            return False

        self.selected_scenarios.append(scenario_name)
        return True

    def deselect_scenario(self, scenario_name: str):
        if scenario_name in self.selected_scenarios:
            self.selected_scenarios.remove(scenario_name)

        if self.active_tab_name == scenario_name:
            self.active_tab_name = ""

    def toggle_scenario(self, scenario_name: str) -> tuple[bool, bool]:
        if scenario_name in self.selected_scenarios:
            self.deselect_scenario(scenario_name)
            return True, False

        selection_succeeded = self.select_scenario(scenario_name)
        return selection_succeeded, selection_succeeded

    def selected_count_label(self) -> str:
        return f"{len(self.selected_scenarios)} / {self.max_selected} selected"

    def scenario_count_label(self, visible_count: int) -> str:
        return f"{visible_count} scenarios"

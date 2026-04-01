from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from corporate_serf_tracker.analysis import estimate_best_cm, estimate_worst_cm
from corporate_serf_tracker.constants import (
    ACCENT,
    BG2,
    BG3,
    GOLD,
    TEXT2,
    WORST_BG,
    WORST_COL,
)


class ScrollPassthroughCanvas(FigureCanvasQTAgg):
    def wheelEvent(self, event: QWheelEvent):
        scroll_area = self._find_parent_scroll_area()

        if scroll_area is None:
            super().wheelEvent(event)
            return

        vertical_scrollbar = scroll_area.verticalScrollBar()

        if vertical_scrollbar is None:
            super().wheelEvent(event)
            return

        delta_y = event.angleDelta().y()

        if delta_y == 0:
            super().wheelEvent(event)
            return

        step_amount = 60

        if delta_y > 0:
            vertical_scrollbar.setValue(vertical_scrollbar.value() - step_amount)
        else:
            vertical_scrollbar.setValue(vertical_scrollbar.value() + step_amount)

        event.accept()

    def _find_parent_scroll_area(self):
        parent_widget = self.parentWidget()

        while parent_widget is not None:
            if isinstance(parent_widget, QScrollArea):
                return parent_widget
            parent_widget = parent_widget.parentWidget()

        return None


class ScoreChartWidget(QWidget):
    def __init__(self, by_cm_scores: dict, parent=None):
        super().__init__(parent)
        self.by_cm_scores = by_cm_scores

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(root_layout)

        self.figure = Figure(figsize=(7.6, 4.9), dpi=100)
        self.canvas = ScrollPassthroughCanvas(self.figure)
        self.canvas.setParent(self)

        root_layout.addWidget(self.canvas)
        self._build_chart()

    def _build_chart(self):
        visible_cms = sorted(self.by_cm_scores.keys())

        self.figure.clear()
        self.figure.patch.set_facecolor(BG2)

        axis = self.figure.add_subplot(111)
        axis.set_facecolor(BG2)

        if not visible_cms:
            axis.text(
                0.5,
                0.5,
                "No chartable data yet.",
                ha="center",
                va="center",
                color=TEXT2,
                fontsize=11,
                transform=axis.transAxes,
            )
            axis.set_xticks([])
            axis.set_yticks([])

            for spine in axis.spines.values():
                spine.set_color(BG3)

            self.figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.14)
            self.canvas.draw()
            return

        best_scores = []
        for cm_value in visible_cms:
            best_scores.append(max(self.by_cm_scores[cm_value]))

        cm_best_scores = {}
        for cm_value, score_value in zip(visible_cms, best_scores):
            cm_best_scores[cm_value] = score_value

        estimated_best_cm, estimated_best_method = estimate_best_cm(cm_best_scores)
        estimated_worst_cm, estimated_worst_method = estimate_worst_cm(cm_best_scores)

        estimated_best_key = None
        if estimated_best_cm is not None:
            estimated_best_key = min(
                visible_cms,
                key=lambda cm_value: abs(cm_value - estimated_best_cm),
            )

        estimated_worst_key = None
        if estimated_worst_cm is not None:
            estimated_worst_key = min(
                visible_cms,
                key=lambda cm_value: abs(cm_value - estimated_worst_cm),
            )

        x_positions = list(range(len(visible_cms)))

        bar_colors = []
        for cm_value in visible_cms:
            if cm_value == estimated_best_key:
                bar_colors.append(GOLD)
            elif cm_value == estimated_worst_key:
                bar_colors.append(WORST_COL)
            else:
                bar_colors.append(ACCENT)

        axis.bar(
            x_positions,
            best_scores,
            color=bar_colors,
            width=0.62,
            zorder=2,
            linewidth=0,
        )

        max_score = max(best_scores)
        min_score = min(best_scores)
        score_range = max_score - min_score

        if score_range <= 0:
            score_range = max(1.0, max_score * 0.1)

        lower_padding = score_range * 0.12
        upper_padding = score_range * 0.28

        y_min = min_score - lower_padding
        if y_min < 0:
            y_min = 0

        y_max = max_score + upper_padding

        axis.set_ylim(y_min, y_max)
        axis.margins(x=0.05)
        axis.grid(axis="y", color=BG3, linewidth=0.8, zorder=0)
        axis.set_axisbelow(True)

        if estimated_best_key is not None:
            estimated_best_index = visible_cms.index(estimated_best_key)

            axis.axvline(
                estimated_best_index,
                color=GOLD,
                linewidth=1.5,
                linestyle="--",
                zorder=3,
                alpha=0.9,
            )

            best_label_y = y_max - (score_range * 0.04)
            best_label_x = estimated_best_index + 0.22
            best_label_align = "left"

            if estimated_best_index >= len(visible_cms) - 2:
                best_label_x = estimated_best_index - 0.22
                best_label_align = "right"

            axis.text(
                best_label_x,
                best_label_y,
                f"est. best\n~{estimated_best_cm:.4g} cm",
                color=GOLD,
                fontsize=8,
                va="top",
                ha=best_label_align,
                fontfamily="Consolas",
                bbox={
                    "boxstyle": "round,pad=0.24",
                    "facecolor": BG2,
                    "edgecolor": GOLD,
                    "linewidth": 0.8,
                    "alpha": 0.96,
                },
                zorder=4,
            )

        if (
            estimated_worst_key is not None
            and estimated_worst_key != estimated_best_key
        ):
            estimated_worst_index = visible_cms.index(estimated_worst_key)

            axis.axvline(
                estimated_worst_index,
                color=WORST_COL,
                linewidth=1.4,
                linestyle=":",
                zorder=3,
                alpha=0.95,
            )

            worst_label_y = y_max - (score_range * 0.22)
            label_x = estimated_worst_index + 0.22
            label_align = "left"

            if estimated_worst_index >= len(visible_cms) - 2:
                label_x = estimated_worst_index - 0.22
                label_align = "right"

            if estimated_best_key is not None:
                estimated_best_index = visible_cms.index(estimated_best_key)
                if abs(estimated_worst_index - estimated_best_index) <= 1:
                    worst_label_y = y_max - (score_range * 0.38)

            axis.text(
                label_x,
                worst_label_y,
                f"worst\n~{estimated_worst_cm:.4g} cm",
                color=WORST_COL,
                fontsize=8,
                va="top",
                ha=label_align,
                fontfamily="Consolas",
                bbox={
                    "boxstyle": "round,pad=0.24",
                    "facecolor": WORST_BG,
                    "edgecolor": WORST_COL,
                    "linewidth": 0.8,
                    "alpha": 0.96,
                },
                zorder=4,
            )

        axis.set_xticks(x_positions)

        x_tick_labels = []
        for cm_value in visible_cms:
            x_tick_labels.append(f"{cm_value:.4g}")

        axis.set_xticklabels(
            x_tick_labels,
            color=TEXT2,
            fontsize=8,
            fontfamily="Consolas",
        )

        axis.set_ylabel("Best Score", color=TEXT2, fontsize=9)
        axis.set_xlabel("cm / 360", color=TEXT2, fontsize=9)

        axis.tick_params(axis="x", colors=TEXT2, length=3, labelsize=8, pad=6)
        axis.tick_params(axis="y", colors=TEXT2, length=3, labelsize=8)

        for spine in axis.spines.values():
            spine.set_color(BG3)

        legend_handles = []

        if estimated_best_cm is not None:
            legend_handles.append(
                mpatches.Patch(
                    color=GOLD,
                    label=f"Est. best: ~{estimated_best_cm:.4g} cm ({estimated_best_method})",
                )
            )

        if estimated_worst_cm is not None:
            legend_handles.append(
                mpatches.Patch(
                    color=WORST_COL,
                    label=f"Worst: ~{estimated_worst_cm:.4g} cm ({estimated_worst_method})",
                )
            )

        legend_handles.append(
            mpatches.Patch(
                color=ACCENT,
                label="Other tested cm",
            )
        )

        legend = axis.legend(
            handles=legend_handles,
            loc="upper left",
            facecolor=BG3,
            edgecolor=BG3,
            labelcolor=TEXT2,
            fontsize=7,
            framealpha=1.0,
            borderpad=0.5,
            handlelength=1.2,
            handletextpad=0.5,
            columnspacing=0.8,
        )

        if legend is not None:
            legend.set_zorder(5)

        self.figure.subplots_adjust(left=0.09, right=0.985, top=0.93, bottom=0.16)
        self.canvas.draw()

    def save_chart_image(self, output_path: str):
        self.figure.savefig(
            output_path,
            dpi=200,
            facecolor=self.figure.get_facecolor(),
            bbox_inches="tight",
        )

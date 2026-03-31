from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from corporate_serf_tracker.analysis import estimate_best_cm, estimate_worst_cm
from corporate_serf_tracker.constants import ACCENT, BG2, BG3, GOLD, TEXT2, WORST_COL

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
            vertical_scrollbar.setValue(
                vertical_scrollbar.value() - step_amount
            )
        else:
            vertical_scrollbar.setValue(
                vertical_scrollbar.value() + step_amount
            )

        event.accept()

    def _find_parent_scroll_area(self):
        parent_widget = self.parentWidget()

        while parent_widget is not None:
            if isinstance(parent_widget, QScrollArea):
                return parent_widget
            parent_widget = parent_widget.parentWidget()

        return None


class ScoreChartWidget(QWidget):
    def __init__(self, by_cm_scores: dict):
        super().__init__()
        self.by_cm_scores = by_cm_scores

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(root_layout)

        self.figure = Figure(figsize=(7.2, 4.6), dpi=100)
        self.canvas = ScrollPassthroughCanvas(self.figure)

        root_layout.addWidget(self.canvas)

        self._build_chart()

    def _build_chart(self):
        visible_cms = sorted(self.by_cm_scores.keys())

        self.figure.clear()

        axis = self.figure.add_subplot(111)
        self.figure.patch.set_facecolor(BG2)
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

        bars = axis.bar(
            x_positions,
            best_scores,
            color=bar_colors,
            width=0.78,
            zorder=2,
            linewidth=0,
        )

        max_score = max(best_scores)
        min_score = min(best_scores)
        label_offset = max_score * 0.016

        for bar_rect, score_value in zip(bars, best_scores):
            axis.text(
                bar_rect.get_x() + (bar_rect.get_width() / 2),
                bar_rect.get_height() + label_offset,
                str(int(score_value)),
                ha="center",
                va="bottom",
                color=TEXT2,
                fontsize=8,
                fontfamily="Consolas",
            )

        if estimated_best_key is not None:
            estimated_best_index = visible_cms.index(estimated_best_key)
            axis.axvline(
                estimated_best_index,
                color=GOLD,
                linewidth=1.5,
                linestyle="--",
                zorder=3,
                alpha=0.85,
            )
            axis.text(
                estimated_best_index + 0.22,
                max_score * 0.985,
                f"est. best\n~{estimated_best_cm:.4g} cm",
                color=GOLD,
                fontsize=8,
                va="top",
                ha="left",
                fontfamily="Consolas",
                bbox={
                    "boxstyle": "round,pad=0.22",
                    "facecolor": BG2,
                    "edgecolor": "none",
                    "alpha": 0.92,
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
                linewidth=1.5,
                linestyle=":",
                zorder=3,
                alpha=0.85,
            )

            label_x = estimated_worst_index + 0.38
            label_align = "left"

            if estimated_worst_index >= len(visible_cms) - 2:
                label_x = estimated_worst_index - 0.38
                label_align = "right"

            axis.text(
                label_x,
                max_score * 0.86,
                f"worst\n~{estimated_worst_cm:.4g} cm",
                color=WORST_COL,
                fontsize=8,
                va="top",
                ha=label_align,
                fontfamily="Consolas",
                bbox={
                    "boxstyle": "round,pad=0.22",
                    "facecolor": BG2,
                    "edgecolor": "none",
                    "alpha": 0.92,
                },
                zorder=4,
            )

        axis.set_xticks(x_positions)
        axis.set_xticklabels(
            [f"{cm_value:.4g}" for cm_value in visible_cms],
            color=TEXT2,
            fontsize=8,
            fontfamily="Consolas",
        )
        axis.set_ylabel("Best Score", color=TEXT2, fontsize=9)
        axis.set_xlabel("cm / 360", color=TEXT2, fontsize=9)
        axis.tick_params(colors=TEXT2, length=3, labelsize=8)
        axis.tick_params(axis="y", colors=TEXT2)

        for spine in axis.spines.values():
            spine.set_color(BG3)

        axis.set_ylim(bottom=max(0, min_score * 0.90), top=max_score * 1.20)
        axis.margins(x=0.08)
        axis.grid(axis="y", color=BG3, linewidth=0.8, zorder=0)
        axis.set_axisbelow(True)

        legend_handles = [
            mpatches.Patch(
                color=GOLD,
                label=(
                    f"Est. best (~{estimated_best_cm:.4g} cm {estimated_best_method})"
                    if estimated_best_cm is not None
                    else "Est. best"
                ),
            ),
            mpatches.Patch(
                color=WORST_COL,
                label=(
                    f"Worst (~{estimated_worst_cm:.4g} cm {estimated_worst_method})"
                    if estimated_worst_cm is not None
                    else "Worst"
                ),
            ),
            mpatches.Patch(
                color=ACCENT,
                label="Other tested cm",
            ),
        ]

        axis.legend(
            handles=legend_handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=3,
            facecolor=BG3,
            edgecolor=BG3,
            labelcolor=TEXT2,
            fontsize=8,
            framealpha=1.0,
            borderpad=0.6,
            handlelength=1.6,
            handletextpad=0.5,
            columnspacing=1.4,
        )

        self.figure.tight_layout(pad=1.2, rect=(0, 0.06, 1, 1))
        self.canvas.draw()

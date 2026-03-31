from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from corporate_serf_tracker.formatting import fmt_score


def export_scenario_pdf(
    output_path,
    scenario_name,
    summary_stats,
    by_cm_scores,
    filters,
    chart_image_path=None,
):
    document = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    base_styles = getSampleStyleSheet()

    title_style = base_styles["Title"]
    section_style = ParagraphStyle(
        name="SectionHeading",
        parent=base_styles["Heading2"],
        spaceBefore=6,
        spaceAfter=8,
        textColor=colors.HexColor("#1f2937"),
    )
    body_style = ParagraphStyle(
        name="BodyTextCustom",
        parent=base_styles["BodyText"],
        fontSize=10,
        leading=13,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        name="MetaText",
        parent=base_styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=2,
    )

    content = []

    content.append(Paragraph(scenario_name, title_style))
    content.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            meta_style,
        )
    )
    content.append(Spacer(1, 10))

    has_active_filters = (
        filters["last_8_only"]
        or bool((filters["cm_min"] or "").strip())
        or bool((filters["cm_max"] or "").strip())
    )

    if has_active_filters:
        filter_lines = []

        if filters["last_8_only"]:
            filter_lines.append("Last 8 Only: True")

        if (filters["cm_min"] or "").strip():
            filter_lines.append(f"Min CM: {filters['cm_min']}")

        if (filters["cm_max"] or "").strip():
            filter_lines.append(f"Max CM: {filters['cm_max']}")

        content.append(Paragraph("Filters", section_style))
        content.append(
            Paragraph(
                "<br/>".join(filter_lines),
                body_style,
            )
        )
        content.append(Spacer(1, 8))

    if chart_image_path:
        content.append(Paragraph("Chart", section_style))
        content.append(Spacer(1, 6))

        max_width = 6.5 * inch
        chart_image = Image(chart_image_path)
        original_width = chart_image.imageWidth
        original_height = chart_image.imageHeight

        scale_ratio = max_width / original_width
        chart_image.drawWidth = max_width
        chart_image.drawHeight = original_height * scale_ratio

        content.append(chart_image)
        content.append(Spacer(1, 10))

    content.append(Paragraph("Overview", section_style))

    overview_rows = [
        ["Best Score", fmt_score(summary_stats["best_score"])],
        ["Median Score", fmt_score(summary_stats["median_score"])],
        ["Best CM", summary_stats["cm_for_best_label"]],
        ["Estimated Best CM", summary_stats["estimated_best_label"]],
        ["Worst CM", summary_stats["worst_cm_label"]],
        ["Next CM to Test", summary_stats["next_cm_label"]],
        ["Total Plays", str(summary_stats["total_plays"])],
    ]

    overview_table = Table(
        overview_rows,
        colWidths=[1.9 * inch, 4.4 * inch],
    )
    overview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [
                        colors.HexColor("#f8fafc"),
                        colors.white,
                    ],
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    content.append(overview_table)
    content.append(Spacer(1, 12))

    content.append(Paragraph("Performance by CM", section_style))

    performance_rows = [["CM/360", "Best Score", "Median", "Plays"]]

    for cm_value in sorted(by_cm_scores.keys()):
        scores = sorted(by_cm_scores[cm_value])
        score_count = len(scores)
        midpoint = score_count // 2

        if score_count % 2:
            median_score = scores[midpoint]
        else:
            median_score = (scores[midpoint - 1] + scores[midpoint]) / 2

        performance_rows.append(
            [
                f"{cm_value:.4g}",
                fmt_score(max(scores)),
                fmt_score(median_score),
                str(score_count),
            ]
        )

    performance_table = Table(
        performance_rows,
        colWidths=[1.2 * inch, 1.6 * inch, 1.6 * inch, 1.0 * inch],
        repeatRows=1,
    )
    performance_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f9fafb"),
                    ],
                ),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    content.append(performance_table)

    document.build(content)

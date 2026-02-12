"""Evaluation report comparison."""

from punie.training.eval_prompts import EvalSuite
from punie.training.eval_results import EvalReport, EvalResult


def compare_reports(reports: list[EvalReport], suite: EvalSuite) -> str:
    """Generate HTML comparison table for multiple evaluation reports.

    Args:
        reports: List of EvalReport instances to compare
        suite: Evaluation suite with category information

    Returns:
        HTML string with side-by-side comparison
    """
    if not reports:
        return "<p>No reports to compare</p>"

    # Build category mapping from suite
    prompt_categories = {p.id: p.category for p in suite.prompts}

    # Get all categories
    all_categories = {p.category for p in suite.prompts}

    # Build comparison table
    html_parts = [
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Evaluation Comparison</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; ",
        "         margin: 40px; background: #f5f5f5; }",
        "  h1 { color: #333; }",
        "  table { width: 100%; background: white; border-collapse: collapse; ",
        "          box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0; }",
        "  th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }",
        "  th { background: #f8f9fa; font-weight: 600; }",
        "  tr:hover { background: #f8f9fa; }",
        "  .score { font-family: 'SF Mono', Monaco, monospace; font-weight: 600; }",
        "  .good { color: #28a745; }",
        "  .fair { color: #ffc107; }",
        "  .poor { color: #dc3545; }",
        "  .delta { font-size: 0.9em; margin-left: 8px; }",
        "  .positive { color: #28a745; }",
        "  .negative { color: #dc3545; }",
        "  .metadata { color: #6c757d; font-size: 0.9em; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>📊 Evaluation Comparison</h1>",
        f"<p class='metadata'>{len(reports)} reports compared</p>",
    ]

    # Overall scores table
    html_parts.extend([
        "<h2>Overall Scores</h2>",
        "<table>",
        "<thead>",
        "<tr>",
        "<th>Model</th>",
        "<th>Adapter</th>",
        "<th>Overall Score</th>",
        "<th>Success Rate</th>",
        "<th>Timestamp</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ])

    for i, report in enumerate(reports):
        adapter = report.adapter_path or "—"
        score_class = _score_class(report.overall_score)

        # Calculate delta from previous
        delta_html = ""
        if i > 0:
            prev_score = reports[i - 1].overall_score
            delta = report.overall_score - prev_score
            if delta != 0:
                delta_class = "positive" if delta > 0 else "negative"
                delta_sign = "+" if delta > 0 else ""
                delta_html = f"<span class='delta {delta_class}'>({delta_sign}{delta:.1%})</span>"

        html_parts.extend([
            "<tr>",
            f"<td>{report.model_name}</td>",
            f"<td>{adapter}</td>",
            f"<td class='score {score_class}'>{report.overall_score:.1%} {delta_html}</td>",
            f"<td class='score'>{report.success_rate:.1%}</td>",
            f"<td class='metadata'>{report.timestamp}</td>",
            "</tr>",
        ])

    html_parts.extend([
        "</tbody>",
        "</table>",
    ])

    # Category breakdown table
    if all_categories:
        html_parts.extend([
            "<h2>Score by Category</h2>",
            "<table>",
            "<thead>",
            "<tr>",
            "<th>Category</th>",
        ])

        for report in reports:
            adapter = report.adapter_path or "Base"
            # Shorten adapter path for display
            if len(adapter) > 20:
                adapter = "..." + adapter[-17:]
            html_parts.append(f"<th>{adapter}</th>")

        html_parts.extend([
            "</tr>",
            "</thead>",
            "<tbody>",
        ])

        for category in sorted(all_categories):
            html_parts.append("<tr>")
            html_parts.append(f"<td><strong>{category}</strong></td>")

            for report in reports:
                # Group results by category
                category_results: dict[str, list[EvalResult]] = {}
                for result in report.results:
                    cat = prompt_categories.get(result.prompt_id, "unknown")
                    if cat not in category_results:
                        category_results[cat] = []
                    category_results[cat].append(result)

                scores = report.score_by_category(category_results)
                score = scores.get(category, 0.0)
                score_class = _score_class(score)
                html_parts.append(f"<td class='score {score_class}'>{score:.1%}</td>")

            html_parts.append("</tr>")

        html_parts.extend([
            "</tbody>",
            "</table>",
        ])

    html_parts.extend([
        "</body>",
        "</html>",
    ])

    return "\n".join(html_parts)


def _score_class(score: float) -> str:
    """Return CSS class for score value."""
    if score >= 0.7:
        return "good"
    if score >= 0.4:
        return "fair"
    return "poor"

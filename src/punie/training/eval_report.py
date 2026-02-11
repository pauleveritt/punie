"""HTML report generation for evaluation results."""

from punie.training.eval_prompts import EvalSuite
from punie.training.eval_results import EvalReport


def generate_eval_html_report(report: EvalReport, suite: EvalSuite) -> str:
    """Generate standalone HTML report from evaluation results.

    Follows src/punie/perf/report.py pattern: standalone HTML with embedded CSS,
    summary section, category breakdown, and detailed results table.

    Args:
        report: Evaluation report with results
        suite: Evaluation suite (for category grouping)

    Returns:
        Complete HTML document as string with embedded CSS
    """
    timestamp_str = report.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    adapter_display = report.adapter_path or "Base model (no adapter)"

    # Group results by category
    category_results: dict[str, list] = {}
    for result in report.results:
        # Find the prompt to get its category
        prompt = next((p for p in suite.prompts if p.id == result.prompt_id), None)
        if prompt:
            category = prompt.category
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(result)

    # Calculate category scores
    category_scores = report.score_by_category(category_results)

    # Build category breakdown rows
    category_rows = ""
    for category, results in category_results.items():
        score = category_scores.get(category, 0.0)
        count = len(results)
        successful = sum(1 for r in results if r.success)
        category_rows += f"""
        <tr>
            <td><strong>{category.replace('_', ' ').title()}</strong></td>
            <td class="number">{score:.2%}</td>
            <td class="number">{count}</td>
            <td class="number">{successful}/{count}</td>
        </tr>
        """

    # Build result detail rows
    result_rows = ""
    for i, result in enumerate(report.results, 1):
        # Find prompt for this result
        prompt = next((p for p in suite.prompts if p.id == result.prompt_id), None)
        category_display = prompt.category.replace('_', ' ').title() if prompt else "Unknown"

        status_class = "success" if result.success else "failure"
        status_text = "✓" if result.success else "✗"

        # Truncate response for table display
        response_preview = result.response_text[:100]
        if len(result.response_text) > 100:
            response_preview += "..."

        tool_calls_display = ", ".join(result.tool_calls_made) if result.tool_calls_made else "—"

        result_rows += f"""
        <tr>
            <td>{i}</td>
            <td><code>{result.prompt_id}</code></td>
            <td>{category_display}</td>
            <td class="number score-{int(result.score * 100 // 10)}">{result.score:.2%}</td>
            <td class="number">{result.duration_ms:.0f}</td>
            <td class="status {status_class}">{status_text}</td>
            <td><code>{tool_calls_display}</code></td>
            <td class="response-preview">{response_preview}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Punie Evaluation Report - {report.suite_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 2rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 2rem;
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 0.5rem;
            font-size: 2rem;
        }}

        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9rem;
            margin-bottom: 2rem;
        }}

        .section {{
            margin-bottom: 2rem;
        }}

        h2 {{
            color: #34495e;
            font-size: 1.5rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .summary-card {{
            background: #ecf0f1;
            border-radius: 6px;
            padding: 1rem;
        }}

        .summary-card h3 {{
            font-size: 0.9rem;
            color: #7f8c8d;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #2c3e50;
        }}

        .summary-card .value.score {{
            color: #27ae60;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}

        th {{
            background: #34495e;
            color: white;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #ecf0f1;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .number {{
            text-align: right;
            font-family: 'Monaco', 'Menlo', monospace;
        }}

        .status {{
            text-align: center;
            font-weight: bold;
            font-size: 1.2rem;
        }}

        .status.success {{
            color: #27ae60;
        }}

        .status.failure {{
            color: #e74c3c;
        }}

        code {{
            background: #ecf0f1;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9rem;
        }}

        .response-preview {{
            font-size: 0.85rem;
            color: #555;
            max-width: 300px;
        }}

        .score-10, .score-9 {{ background: #d4edda; }}
        .score-8, .score-7 {{ background: #fff3cd; }}
        .score-6, .score-5 {{ background: #fff3cd; }}
        .score-4, .score-3 {{ background: #f8d7da; }}
        .score-2, .score-1, .score-0 {{ background: #f8d7da; }}

        .metadata {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 2rem;
        }}

        .metadata p {{
            margin: 0.25rem 0;
            color: #555;
        }}

        .metadata strong {{
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Evaluation Report: {report.suite_name}</h1>
        <div class="timestamp">Generated: {timestamp_str}</div>

        <div class="metadata">
            <p><strong>Model:</strong> <code>{report.model_name}</code></p>
            <p><strong>Adapter:</strong> <code>{adapter_display}</code></p>
            <p><strong>Suite:</strong> {report.suite_name}</p>
        </div>

        <div class="section">
            <h2>Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Overall Score</h3>
                    <div class="value score">{report.overall_score:.1%}</div>
                </div>
                <div class="summary-card">
                    <h3>Success Rate</h3>
                    <div class="value">{report.success_rate:.1%}</div>
                </div>
                <div class="summary-card">
                    <h3>Total Prompts</h3>
                    <div class="value">{len(report.results)}</div>
                </div>
                <div class="summary-card">
                    <h3>Successful</h3>
                    <div class="value">{sum(1 for r in report.results if r.success)}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Category Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th class="number">Average Score</th>
                        <th class="number">Prompts</th>
                        <th class="number">Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {category_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Detailed Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Prompt ID</th>
                        <th>Category</th>
                        <th class="number">Score</th>
                        <th class="number">Duration (ms)</th>
                        <th class="status">✓</th>
                        <th>Tools Called</th>
                        <th>Response Preview</th>
                    </tr>
                </thead>
                <tbody>
                    {result_rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

    return html

"""HTML report generation for tool performance data."""

from datetime import datetime, timezone

from punie.perf.collector import PromptTiming


def generate_html_report(timing: PromptTiming) -> str:
    """Generate standalone HTML report from timing data.

    Args:
        timing: Performance timing data to visualize

    Returns:
        Complete HTML document as string with embedded CSS
    """
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_tool_time = sum(t.duration_ms for t in timing.tool_timings)
    model_think_time = timing.duration_ms - total_tool_time

    # Calculate percentages for visualization
    tool_percentage = (
        (total_tool_time / timing.duration_ms * 100) if timing.duration_ms > 0 else 0
    )
    model_percentage = 100 - tool_percentage

    # Build tool rows
    tool_rows = ""
    for i, t in enumerate(timing.tool_timings, 1):
        status_class = "success" if t.success else "failure"
        status_text = "✓" if t.success else "✗"
        error_cell = f"<td>{t.error}</td>" if not t.success else "<td>—</td>"

        tool_rows += f"""
        <tr>
            <td>{i}</td>
            <td><code>{t.tool_name}</code></td>
            <td class="number">{t.duration_ms:.2f}</td>
            <td class="status {status_class}">{status_text}</td>
            {error_cell}
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Punie Performance Report</title>
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
            max-width: 1200px;
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
            padding: 1rem;
            border-radius: 4px;
            border-left: 4px solid #3498db;
        }}

        .summary-card label {{
            display: block;
            color: #7f8c8d;
            font-size: 0.85rem;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }}

        .summary-card .value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}

        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }}

        th {{
            background: #34495e;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .number {{
            text-align: right;
            font-family: "SF Mono", Monaco, "Courier New", monospace;
        }}

        .status {{
            text-align: center;
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
            font-family: "SF Mono", Monaco, "Courier New", monospace;
            font-size: 0.9rem;
        }}

        .timing-bar {{
            width: 100%;
            height: 60px;
            display: flex;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 1rem;
        }}

        .timing-segment {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9rem;
        }}

        .timing-tools {{
            background: #3498db;
        }}

        .timing-model {{
            background: #9b59b6;
        }}

        .legend {{
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
            font-size: 0.9rem;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
        }}

        .badge.local {{
            background: #3498db;
            color: white;
        }}

        .badge.ide {{
            background: #9b59b6;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Punie Performance Report</h1>
        <div class="timestamp">Generated: {timestamp}</div>

        <div class="section">
            <h2>Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <label>Model</label>
                    <div class="value">{timing.model_name}</div>
                </div>
                <div class="summary-card">
                    <label>Backend</label>
                    <div class="value">
                        <span class="badge {timing.backend}">{timing.backend}</span>
                    </div>
                </div>
                <div class="summary-card">
                    <label>Total Duration</label>
                    <div class="value">{timing.duration_ms:.2f} ms</div>
                </div>
                <div class="summary-card">
                    <label>Tool Calls</label>
                    <div class="value">{len(timing.tool_timings)}</div>
                </div>
                <div class="summary-card">
                    <label>Tool Time</label>
                    <div class="value">{total_tool_time:.2f} ms</div>
                </div>
                <div class="summary-card">
                    <label>Model Think Time</label>
                    <div class="value">{model_think_time:.2f} ms</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Timing Breakdown</h2>
            <div class="timing-bar">
                <div class="timing-segment timing-tools" style="width: {tool_percentage:.1f}%">
                    Tools: {tool_percentage:.1f}%
                </div>
                <div class="timing-segment timing-model" style="width: {model_percentage:.1f}%">
                    Model: {model_percentage:.1f}%
                </div>
            </div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color timing-tools"></div>
                    <span>Tool Execution Time</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color timing-model"></div>
                    <span>Model Think Time</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Tool Calls</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Tool Name</th>
                        <th>Duration (ms)</th>
                        <th>Status</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
                    {tool_rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""

    return html

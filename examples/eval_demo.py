"""Demo: Evaluation harness with test model.

This demonstrates the evaluation infrastructure working end-to-end
without requiring an actual model server (uses TestModel).

Run: uv run python examples/eval_demo.py
"""

import asyncio
from pathlib import Path

from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_results import EvalReport, EvalResult
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.server_config import ServerConfig


async def demo_with_test_model():
    """Run evaluation with TestModel (no server required)."""
    print("🧪 Demo: Evaluation Harness with Test Model")
    print("=" * 60)

    # Create a simple evaluation suite
    suite = EvalSuite(
        name="test-demo",
        prompts=(
            EvalPrompt(
                id="reasoning-01",
                category="reasoning",
                prompt_text="Explain what a function is in Python",
                expected_keywords=("function", "def", "return"),
            ),
            EvalPrompt(
                id="code-01",
                category="code_generation",
                prompt_text="Write a function to add two numbers",
                expected_keywords=("def", "add", "return"),
            ),
        ),
    )

    print(f"\n📋 Suite: {suite.name}")
    print(f"   Prompts: {len(suite.prompts)}")
    for p in suite.prompts:
        print(f"   - {p.id}: {p.category}")

    # Configure evaluation with test model
    config = EvalRunConfig(
        server_config=ServerConfig(model_path="test"),
        suite=suite,
        workspace=Path.cwd(),
        manage_server=False,  # No server for test model
    )

    print("\n⚙️  Configuration:")
    print(f"   Model: test (TestModel - no LLM calls)")
    print(f"   Server management: {config.manage_server}")
    print(f"   Workspace: {config.workspace}")

    # Since we can't actually use the test model with the current runner
    # (it needs special handling), let's create a mock report instead
    print("\n🔄 Running evaluation...")
    print("   (Note: This demo creates mock results - see next step for real evaluation)")

    # Create mock results for demonstration
    results = []
    for prompt in suite.prompts:
        # Simulate a response that matches some keywords
        if prompt.id == "reasoning-01":
            response = "A function in Python is defined with def and can return values."
            score = 1.0  # All keywords present
        else:
            response = "def add(a, b): return a + b"
            score = 1.0  # All keywords present

        results.append(
            EvalResult(
                prompt_id=prompt.id,
                response_text=response,
                tool_calls_made=(),
                duration_ms=50.0,
                score=score,
                success=True,
            )
        )

    # Create report
    from datetime import datetime

    report = EvalReport(
        model_name="test",
        adapter_path=None,
        suite_name=suite.name,
        timestamp=datetime.now(),
        results=tuple(results),
    )

    print("\n📊 Results Summary:")
    print(f"   Overall Score: {report.overall_score:.1%}")
    print(f"   Success Rate: {report.success_rate:.1%}")
    print(f"   Total Prompts: {len(report.results)}")

    # Generate HTML report
    html = generate_eval_html_report(report, suite)
    output_file = Path("eval_report_demo.html")
    output_file.write_text(html)

    print(f"\n✅ HTML report generated: {output_file}")
    print(f"   Open in browser: open {output_file}")

    return report


async def show_real_model_usage():
    """Show how to use with a real model (requires mlx-lm server)."""
    print("\n" + "=" * 60)
    print("📖 Next Step: Real Model Evaluation")
    print("=" * 60)

    print("""
To evaluate a real model, you'll need to:

1. Install mlx-lm (if not already):
   uv add mlx-lm

2. Create evaluation script (e.g., eval_real.py):
   ```python
   from pathlib import Path
   from punie.training.server_config import ServerConfig
   from punie.training.eval_runner import EvalRunConfig, run_evaluation
   from punie.training.eval_suites import create_baseline_suite
   from punie.training.eval_report import generate_eval_html_report

   async def main():
       # Create config with real model
       server_config = ServerConfig(
           model_path="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
           port=8080,
       )

       suite = create_baseline_suite()

       config = EvalRunConfig(
           server_config=server_config,
           suite=suite,
           workspace=Path.cwd(),
           manage_server=True,  # Auto-start/stop server
       )

       # Run evaluation
       report = await run_evaluation(config)

       # Generate report
       html = generate_eval_html_report(report, suite)
       Path("eval_report.html").write_text(html)

       print(f"Overall Score: {report.overall_score:.1%}")

   if __name__ == "__main__":
       import asyncio
       asyncio.run(main())
   ```

3. Run it:
   uv run python eval_real.py

The evaluation harness will:
- Start mlx_lm.server automatically
- Run all prompts in the baseline suite
- Extract tool calls and score responses
- Generate HTML report with visualizations
- Stop the server when done
""")


async def main():
    """Run the demo."""
    report = await demo_with_test_model()
    await show_real_model_usage()


if __name__ == "__main__":
    asyncio.run(main())

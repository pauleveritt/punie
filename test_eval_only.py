"""Simple evaluation test - just test server + evaluation."""

import asyncio
from pathlib import Path

from punie.training.eval_prompts import EvalPrompt, EvalSuite
from punie.training.eval_report import generate_eval_html_report
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.server_config import ServerConfig


async def main():
    print("🧪 Simple Evaluation Test")
    print("=" * 60)

    # Use tiny model
    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    print(f"Model: {model_path}")

    # Create simple 2-prompt suite
    suite = EvalSuite(
        name="quick-test",
        prompts=(
            EvalPrompt(
                id="test-01",
                category="reasoning",
                prompt_text="What is 2+2?",
                expected_keywords=("4", "four"),
            ),
            EvalPrompt(
                id="test-02",
                category="code_generation",
                prompt_text="Write a Python function to add two numbers",
                expected_keywords=("def", "add", "return"),
            ),
        ),
    )

    print(f"Suite: {suite.name} ({len(suite.prompts)} prompts)")

    server_config = ServerConfig(
        model_path=model_path,
        port=8080,
    )

    config = EvalRunConfig(
        server_config=server_config,
        suite=suite,
        workspace=Path.cwd(),
        manage_server=True,
    )

    print("\n🔄 Running evaluation...")
    print("(Server will start automatically, then run 2 prompts)")

    try:
        report = await run_evaluation(config)

        print(f"\n✅ Success!")
        print(f"   Overall Score: {report.overall_score:.1%}")
        print(f"   Success Rate: {report.success_rate:.1%}")

        # Show individual results
        print("\n📋 Results:")
        for result in report.results:
            status = "✓" if result.success else "✗"
            print(f"   {status} {result.prompt_id}: {result.score:.1%} score")
            print(f"      Response: {result.response_text[:80]}...")

        # Generate report
        html = generate_eval_html_report(report, suite)
        Path("eval_quick_test.html").write_text(html)
        print(f"\n📄 Report: eval_quick_test.html")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

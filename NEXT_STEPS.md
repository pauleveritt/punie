# Next Steps: Local Model Training

## Current Status ✅

**Completed:**
- ✅ Phase 12: Server Management (27 tests)
- ✅ Phase 13: Evaluation Harness (46 tests)
- ✅ Demo script showing evaluation workflow
- ✅ 368 tests passing, 78% coverage

**Ready to use:**
- Server lifecycle management (`ServerProcess`)
- Evaluation infrastructure (`run_evaluation()`)
- HTML report generation
- Baseline evaluation suite (7 prompts)

## Immediate Next Step: Validate Infrastructure

Before building more features, let's test with a real model:

### Option 1: Quick Test with Test Model (Already Done)
```bash
uv run python examples/eval_demo.py
open eval_report_demo.html
```
✅ This works! You've seen the HTML report.

### Option 2: Test with Real Local Model

**Prerequisites:**
1. Install mlx-lm:
   ```bash
   uv add mlx-lm
   ```

2. Download a small model for testing (NOT the 30B yet - start small):
   ```bash
   # Option A: Use LM Studio GUI (easiest)
   # - Install LM Studio
   # - Download a 3-7B model
   # - It runs on localhost:1234

   # Option B: Use mlx-lm directly
   # Download a small model for testing first
   huggingface-cli download mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --local-dir models/qwen-7b
   ```

3. Create `test_real_eval.py`:
   ```python
   import asyncio
   from pathlib import Path
   from punie.training.server_config import ServerConfig
   from punie.training.eval_runner import EvalRunConfig, run_evaluation
   from punie.training.eval_suites import create_baseline_suite
   from punie.training.eval_report import generate_eval_html_report

   async def main():
       # Use a small model for testing
       server_config = ServerConfig(
           model_path="models/qwen-7b",  # Or whatever model you downloaded
           port=8080,
       )

       suite = create_baseline_suite()  # 7 prompts

       config = EvalRunConfig(
           server_config=server_config,
           suite=suite,
           workspace=Path.cwd(),
           manage_server=True,  # Auto-start mlx_lm.server
       )

       print(f"🔄 Starting evaluation with {len(suite.prompts)} prompts...")
       report = await run_evaluation(config)

       # Generate HTML report
       html = generate_eval_html_report(report, suite)
       Path("eval_baseline.html").write_text(html)

       print(f"\n📊 Results:")
       print(f"   Overall Score: {report.overall_score:.1%}")
       print(f"   Success Rate: {report.success_rate:.1%}")
       print(f"   Report: eval_baseline.html")

   if __name__ == "__main__":
       asyncio.run(main())
   ```

4. Run it:
   ```bash
   uv run python test_real_eval.py
   ```

**What to look for:**
- Server starts automatically
- Prompts execute (may take a few minutes for 7 prompts)
- HTML report shows actual results
- Server stops automatically
- Check scores - they'll likely be low for base model (that's expected!)

### Option 3: Benchmark Training Speed (Phase 12.4)

Test if training is feasible on your hardware:

```python
import asyncio
from pathlib import Path
from punie.training.benchmark import create_dummy_dataset, run_training_benchmark

async def main():
    # Create tiny test dataset
    data_dir = Path("data/benchmark")
    create_dummy_dataset(data_dir, num_examples=5)

    # Benchmark with 7B model first (NOT 30B yet!)
    result = await run_training_benchmark(
        model_path="models/qwen-7b",
        num_iters=10,
        data_dir=data_dir,
    )

    print(f"Model: {result.model_path}")
    print(f"Seconds per iteration: {result.seconds_per_iter:.2f}s")
    print(f"Total time: {result.total_seconds:.2f}s")
    if result.peak_memory_gb:
        print(f"Peak memory: {result.peak_memory_gb:.2f} GB")

    # Decision criteria:
    if result.seconds_per_iter < 5:
        print("\n✅ Fast enough! (~5 sec/iter)")
    elif result.seconds_per_iter < 30:
        print("\n⚠️  Acceptable but slow (~10-30 sec/iter)")
    else:
        print("\n❌ Too slow for iteration (>30 sec/iter)")

asyncio.run(main())
```

## After Validation

Once real evaluation and benchmarking work:

1. **Document results** in `docs/research/training-journal.md`:
   - Baseline evaluation scores
   - Training speed benchmark
   - Memory usage

2. **Decide on model size**:
   - If 7B trains fast: Consider testing 30B
   - If 7B is too slow: Stick with 7B

3. **Continue with Phase 14**: Training Data Infrastructure
   - Dataset validation
   - Filtering functions
   - LoRA training runner
   - Progressive dataset refinement

## Troubleshooting

**Server won't start:**
- Check port 8080 isn't in use: `lsof -i :8080`
- Check model path exists
- Check mlx-lm is installed: `uv run python -c "import mlx_lm; print('OK')"`

**Evaluation fails:**
- Check server logs (stderr)
- Try simpler prompts first
- Verify model supports tool calling

**Memory issues:**
- Start with smaller model (3B or 7B)
- Use 4-bit quantization
- Close other applications

## Current Branch Status

```bash
git status
# On branch: local-model-training
# Commits: 3 (Phase 12 + Phase 13 + demo)
# Ready to merge to main once validated
```

## Questions?

- Evaluation too slow? → Use fewer prompts in suite
- Want different prompts? → Edit `create_baseline_suite()` in `eval_suites.py`
- Want to see scores per category? → Check HTML report category breakdown
- Need to debug? → Add `print()` statements in `eval_runner.py`

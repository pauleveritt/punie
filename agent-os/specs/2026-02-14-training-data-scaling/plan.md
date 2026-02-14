# Training Data Scaling Spec - Plan

## Goal

Scale from domain-specific training (244 examples) to diverse Python frameworks (794 examples), then add HTML support (824 examples), maintaining 100% discrimination accuracy while improving inference speed.

## Components

### 19.1: Clone 10 popular Python repositories

- Create `scripts/clone_popular_repos.py`
- Clone: fastapi, flask, pytest, typer, click, httpx, starlette, pydantic, attrs, structlog
- Result: 2,941 Python files in `data/repos/`

### 19.2: Generate 550 examples via AST parsing

- Create `scripts/generate_repo_examples.py`
- Parse Python files with `ast` module
- Extract: classes, functions, imports, decorators, docstrings
- Generate patterns:
  - **300 grep examples:** Search for classes, functions, patterns
  - **150 read examples:** Explore specific files
  - **100 direct answers:** Explain framework concepts
- Output: `data/repos_examples/training_examples.jsonl`

### 19.3: Add 30 HTML examples

- Create `scripts/generate_html_examples.py`
- Categories: semantic HTML, forms, tables, navigation, accessibility
- Patterns:
  - **9 grep examples:** Search for HTML patterns
  - **5 read examples:** Explore HTML files
  - **16 direct answers:** Semantic HTML concepts
- Output: `data/html_examples/training_examples.jsonl`

### 19.4: Train Phase 6 (794 examples)

- Create `scripts/merge_phase6_data.py`
- Merge Phase 5 (244) + repo examples (550) = 794 total
- Split: 714 train, 80 valid
- Train: 300 iterations, batch_size 2
- Result: Val loss 3.147 → 0.369 (88.3% improvement)

### 19.5: Train Phase 7 (824 examples)

- Create `scripts/merge_phase7_data.py`
- Merge Phase 6 (794) + HTML examples (30) = 824 total
- Split: 741 train, 83 valid
- Train: 300 iterations, batch_size 2
- Result: Val loss 2.783 → 0.373 (86.6% improvement)

### 19.6: Benchmark all phases

- Update `benchmark_phase5_vs_base.py` to support 5+ models
- Test: base, Phase 5, Phase 5 fused-8bit, Phase 6, Phase 7
- Compare: load time, generation speed, accuracy, adapter size
- Document: `benchmark_all_phases.log`

## Training Configuration

**Phase 6:**
- Model: Qwen2.5-Coder-7B-Instruct-4bit
- Examples: 794 (714 train, 80 valid)
- Batch size: 2
- Learning rate: 1e-4
- Iterations: 300
- Training time: ~45 min
- Peak memory: 18.493 GB

**Phase 7:**
- Model: Qwen2.5-Coder-7B-Instruct-4bit
- Examples: 824 (741 train, 83 valid)
- Batch size: 2
- Learning rate: 1e-4
- Iterations: 300
- Training time: ~45 min
- Peak memory: 18.447 GB

## Success Criteria

- ✅ Phase 6: 100% accuracy, faster than Phase 5 (11.97s vs 12.13s)
- ✅ Phase 6: 67% smaller adapter (0.13 GB vs 0.39 GB)
- ✅ Phase 7: 100% accuracy, fastest overall (11.96s avg)
- ✅ Phase 7: Fastest load time (0.68s)
- ✅ Multi-domain support with zero performance penalty

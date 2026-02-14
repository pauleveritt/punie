# Knowledge Distillation Spec - Plan

## Goal

Train Qwen2.5-Coder-7B-Instruct-4bit to autonomously use tools with proper discrimination between tool-calling and direct-answer queries, fixing memorization and infinite loop issues from Phase 0.

## Components

### 17.1: Establish baselines

- Benchmark Claude Code: 2.41s, 100% accuracy, autonomous tools
- Benchmark 30B model: ~27s, 100% accuracy, autonomous tools (crashes system)
- Benchmark 7B Phase 0: 21.06s, 100% accuracy, but memorized (no tools)
- Identify problem: Model memorized answers instead of learning to use tools

### 17.2: Fix tool-call format (Phase 1)

- Root cause: Training data used `"tool"` key, parser expected `"name"` key
- Fix converter to use correct format: `{"name": "run_command", "arguments": {...}}`
- Update 30 hand-authored examples
- Regenerate 69 converted examples
- Result: Model uses tools but loops infinitely (20+ calls)

### 17.3: Fix stop sequences (Phase 4)

- Discover key mismatch in `src/punie/agent/factory.py` line 241
- Change from `"stop"` to `"stop_sequences"` (PydanticAI expects this key)
- Update tests in `tests/test_agent_config.py`
- Result: Infinite loop fixed! Model completes in 2 turns

### 17.4: Add domain training data (Phase 4)

- Create `scripts/generate_domain_examples.py`
- Read real files from svcs-di and tdom-svcs repositories
- Generate 21 domain examples with actual code patterns
- Merge with existing POC (28) + public (150) = 199 examples
- Split: 179 train, 20 valid

### 17.5: Balance tool vs direct answers (Phase 5)

- Expand direct-answer examples from 5 to 50
- Mine from real documentation (concepts, comparisons, best practices)
- Final composition: 164 with tools (67.2%), 80 without tools (32.8%)
- Total: 244 examples (219 train, 25 valid)
- Categories:
  - Concept questions (15): "What is X?", "Explain Y"
  - Comparisons (10): "What's the difference between X and Y?"
  - Best practices (10): "When should I use X?"
  - Syntax/how-to (10): "What does this decorator do?"
  - Architecture (5): "How does the service locator pattern work?"

## Training Configuration

- Model: Qwen2.5-Coder-7B-Instruct-4bit
- Batch size: 2 (memory-optimized)
- Learning rate: 1e-4
- LoRA rank: 16 (num_layers)
- Iterations: 300
- Training time: ~30 minutes
- Peak memory: 18.493 GB

## Success Criteria

- ✅ Model uses tools instead of memorizing
- ✅ No infinite loops (completes in 1-2 turns)
- ✅ Stop sequences work correctly
- ✅ 100% discrimination accuracy (5/5 test queries)
- ✅ Training loss: 1.881 → 0.235 (87.5% improvement)
- ✅ Validation loss: 2.140 → 0.815 (62% improvement)

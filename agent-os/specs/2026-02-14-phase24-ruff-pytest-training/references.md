# Phase 24 References

## Key Files Modified

### Core Implementation
- **src/punie/agent/typed_tools.py**
  - Lines: Entire file extended
  - Purpose: Add RuffResult, TestResult models and parsers
  - Pattern: Follow TypeCheckResult from Phase 23

- **src/punie/agent/monty_runner.py**
  - Lines 23-33: ExternalFunctions dataclass
  - Lines 119-129: Doctest example (bug fix)
  - Lines ~143: Namespace registration
  - Purpose: Extend sandbox with new typed tools

- **src/punie/agent/toolset.py**
  - Lines 347+: Add sync_ruff_check, sync_pytest_run bridges
  - Lines 588-596: known_tools dict (bug fix)
  - Purpose: Connect external functions to terminal workflows

- **src/punie/agent/stubs.py**
  - Lines ~131+: Add ruff_check and pytest_run stubs
  - Purpose: Generate type hints for sandbox code

- **src/punie/agent/config.py**
  - Lines ~32: System prompt guidelines
  - Purpose: Update tool usage instructions

### Tests
- **tests/test_typed_tools.py**
  - Extend with ~14 new tests for Ruff/Pytest models
  - Pattern: Validation + parser tests

- **tests/test_monty_runner.py**
  - Add fake_ruff_check, fake_pytest_run
  - Add 5 new integration tests
  - Update external_functions fixture

- **tests/test_execute_code.py**
  - Update ExternalFunctions construction with new fakes

- **tests/test_stubs.py**
  - Add stub presence assertions

## Training Data Scripts (New)

### Data Generation
- **scripts/generate_ruff_training_data.py**
  - Output: `data/ruff_training/ruff_examples.jsonl`
  - ~50 examples in 4 categories

- **scripts/generate_pytest_training_data.py**
  - Output: `data/pytest_training/pytest_examples.jsonl`
  - ~50 examples in 4 categories

- **scripts/generate_phase24_domain_data.py**
  - Output: `data/phase24_domain/domain_examples.jsonl`
  - ~115 examples from tdom/svcs-di/tdom-svcs
  - Reads real files from repositories

- **scripts/generate_phase24_workflows.py**
  - Output: `data/phase24_workflows/workflow_examples.jsonl`
  - ~28 multi-step workflow examples

### Data Processing
- **scripts/merge_phase24_data.py**
  - Merges all sources into train/valid/test splits
  - Output: `data/phase24_merged/` (3 files)

### Training and Testing
- **scripts/train_phase24.sh**
  - Full pipeline: train → fuse → quantize
  - Output: `fused_model_qwen3_phase24_ruff_pytest_5bit/`

- **scripts/test_phase24_model.py**
  - 20-query test suite
  - Categories: single-tool, multi-step, domain knowledge

## Domain Repositories

### tdom
- **Location**: `~/projects/t-strings/tdom/`
- **Focus**: AST manipulation, HTML generation
- **Key files**:
  - `tdom/nodes.py` - Node classes
  - `tdom/processor.py` - Processing pipeline
  - `tdom/parser.py` - Parsing logic
  - `tdom/*_test.py` - Test files
  - `docs/usage/*.md` - Concept docs

### svcs-di
- **Location**: `~/projects/t-strings/svcs-di/`
- **Focus**: Dependency injection patterns
- **Key files**:
  - `src/svcs_di/*.py` - Core DI implementation
  - `docs/*.md` - DI concept docs

### tdom-svcs
- **Location**: `~/projects/t-strings/tdom-svcs/`
- **Focus**: Middleware and service integration
- **Key files**:
  - `src/tdom_svcs/*.py` - Middleware patterns
  - `docs/*.md` - Integration docs

## Related Phase Documentation

### Phase 22: Code Mode
- **Location**: `agent-os/specs/2026-02-14-phase22-code-mode/`
- **Key innovation**: Python code format instead of XML/JSON
- **Pattern**: `<tool_call>...Python code...</tool_call>`

### Phase 23: ty Integration
- **Location**: MEMORY.md Phase 23 section
- **Key innovation**: First typed tool (typecheck)
- **Pattern**: External function → Pydantic model
- **Training**: 757 examples, 84% val loss reduction

## Training Data Format Examples

### Simple Tool Call
```jsonl
{
  "messages": [
    {"role": "user", "content": "Lint src/punie/"},
    {"role": "assistant", "content": "<tool_call>\nresult = ruff_check('src/punie/')\nif result.success:\n    print('No violations')\nelse:\n    print(f'{result.violation_count} violations found')\n</tool_call>"}
  ]
}
```

### Multi-Step Workflow
```jsonl
{
  "messages": [
    {"role": "user", "content": "Check quality: lint, types, and tests"},
    {"role": "assistant", "content": "<tool_call>\nruff = ruff_check('src/')\nty = typecheck('src/')\ntests = pytest_run('tests/')\n\nprint(f'Ruff: {ruff.violation_count} violations')\nprint(f'Type: {ty.error_count} errors')\nprint(f'Tests: {tests.passed}/{tests.passed + tests.failed} passed')\n</tool_call>"}
  ]
}
```

### Direct Answer
```jsonl
{
  "messages": [
    {"role": "user", "content": "What is the F401 ruff code?"},
    {"role": "assistant", "content": "F401 is the ruff code for unused imports. It indicates that you've imported a module, class, or function but never used it in your code. This violation is auto-fixable with `ruff check --fix`."}
  ]
}
```

## Model Configuration

### Base Model
- **Name**: Qwen3-Coder-30B-A3B-Instruct
- **Size**: 30B parameters
- **Format**: 4-bit quantized (MLX)
- **Purpose**: Code generation with tool calling

### LoRA Training
- **Iterations**: 600
- **Batch size**: 1
- **Learning rate**: 1e-4
- **LoRA layers**: 8
- **Target modules**: Attention and FFN layers

### Quantization
- **Intermediate**: float16 (57 GB)
- **Final**: 5-bit (20-25 GB)
- **Reason**: Balances quality vs memory (established in Phase 23)

## Testing Strategy

### Unit Tests
- Pydantic model validation
- Parser functions (success, empty, malformed)
- Sandbox integration (fakes)

### Integration Tests
- External functions called correctly
- Structured results returned
- Multi-tool workflows

### Model Tests
- 20-query suite covering:
  - Single-tool discrimination (8)
  - Multi-step workflows (7)
  - Domain knowledge (5)
- Success criteria: 95% (19/20)

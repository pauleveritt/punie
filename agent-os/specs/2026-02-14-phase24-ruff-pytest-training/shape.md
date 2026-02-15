# Phase 24 Shape

## Scope

Phase 24 extends the typed tools architecture from Phase 23 by adding:
1. **Two new typed tools**: `ruff_check()` and `pytest_run()`
2. **Domain-specific training data**: Real code from tdom, svcs-di, tdom-svcs
3. **1000+ training examples**: Up from 757 in Phase 23
4. **Bug fixes**: Broken doctests and missing tool registration

## Key Decisions

### Why Typed Tools?
- Phase 23 established that returning structured Pydantic models > raw CLI text
- Model can use `result.error_count`, `result.errors[0].message` instead of parsing strings
- Type-safe, inspectable, composable

### Why These Two Tools?
- **ruff**: Most common linter in Python ecosystem, fast, comprehensive
- **pytest**: De facto testing standard, rich output format
- Together with `typecheck()` from Phase 23 → covers the quality triad (lint, types, tests)

### Why 1000+ Examples?
- Phase 25 will experiment with Qwen2.5-Coder-7B (smaller, faster model)
- 7B models need more training signal than 30B to match performance
- 757 → 1000+ is a 32% increase in training data

### Why Real Repository Content?
- Previous phases used synthetic examples
- Real code patterns → model learns actual project conventions
- tdom/svcs-di/tdom-svcs are representative Python codebases with:
  - Modern type annotations
  - Dataclasses and Protocols
  - Pytest function-based tests
  - Domain-specific patterns (AST manipulation, DI, middleware)

## Architecture

### Typed Tool Pattern (established in Phase 23)
```
User query → Model generates code → Sandbox executes
                                        ↓
                                   External function
                                        ↓
                                   Terminal workflow
                                        ↓
                                   Parse output
                                        ↓
                                   Return Pydantic model
```

### Training Data Format (Code Mode)
```python
# User message
"Lint src/punie/ and show fixable violations"

# Assistant response (model generates this)
result = ruff_check("src/punie/")
if result.success:
    print(f"No violations found")
else:
    fixable = [v for v in result.violations if v.fixable]
    print(f"Found {len(fixable)} fixable violations:")
    for v in fixable:
        print(f"  {v.file}:{v.line} {v.code} - {v.message}")
```

### Data Sources
1. **Phase 23**: 757 examples (typecheck + multi-turn + direct answers)
2. **Ruff**: 50 new (lint checks, fixes, combined with typecheck, concepts)
3. **Pytest**: 50 new (test runs, failures, full pipeline, concepts)
4. **Domain**: 115+ new (real code from tdom/svcs-di/tdom-svcs)
5. **Workflows**: 28+ new (multi-step sequences using all tools)

Total: ~1000 examples

### Model Pipeline
1. Train LoRA adapter (8 layers, 1e-4 LR, 600 iters)
2. Fuse to float16 (preserves full precision)
3. Quantize to 5-bit (20-25 GB, balances quality vs size)

## Out of Scope

- ❌ New tool types beyond ruff/pytest (save for future phases)
- ❌ Changing Code Mode format (established in Phase 22)
- ❌ Refactoring existing code (bugs only)
- ❌ Documentation updates (focus on training data)
- ❌ Performance optimization (next phase)

## Success Criteria

1. **All tests pass**: Including new typed tool tests and fixed doctests
2. **Training converges**: Val loss < 0.8 (matching Phase 23)
3. **Model discrimination**: 95%+ accuracy on 20-query test suite
4. **Tool selection**: Correctly chooses ruff_check, pytest_run, typecheck
5. **Domain knowledge**: Answers tdom/svcs-di/tdom-svcs concept questions

## Risks and Mitigations

### Risk: Parser Fragility
- Ruff and pytest output formats may vary across versions
- **Mitigation**: Test parsers with diverse output samples, graceful degradation

### Risk: Training Time
- 1000 examples → longer training than Phase 23
- **Mitigation**: Increased iterations (500 → 600) but same batch size

### Risk: Domain Data Quality
- Real repos may have inconsistent patterns
- **Mitigation**: Manual review of generated examples, filter low-quality

### Risk: Test Suite Coverage
- 20 queries may not catch edge cases
- **Mitigation**: Cover single-tool, multi-step, and domain knowledge categories

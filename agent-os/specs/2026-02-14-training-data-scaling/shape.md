# Training Data Scaling Spec - Shape

## Architecture

```
data/
├── repos/                         # Cloned repositories
│   ├── fastapi/
│   ├── flask/
│   ├── pytest/
│   ├── typer/
│   ├── click/
│   ├── httpx/
│   ├── starlette/
│   ├── pydantic/
│   ├── attrs/
│   └── structlog/
├── repos_examples/                # Generated from repos
│   └── training_examples.jsonl   # 550 repo examples
├── html_examples/                 # Generated HTML examples
│   └── training_examples.jsonl   # 30 HTML examples
├── phase6_format/                 # Phase 6 training data
│   ├── train.jsonl               # 714 examples (Python only)
│   └── valid.jsonl               # 80 examples
└── phase7_format/                 # Phase 7 training data
    ├── train.jsonl               # 741 examples (Python + HTML)
    └── valid.jsonl               # 83 examples

scripts/
├── clone_popular_repos.py        # Clone 10 Python repos
├── generate_repo_examples.py     # AST-based example generation
├── generate_html_examples.py     # HTML domain examples
├── merge_phase6_data.py          # Phase 5 + repos → Phase 6
└── merge_phase7_data.py          # Phase 6 + HTML → Phase 7

adapters_phase6/                  # Phase 6 LoRA weights (130MB)
adapters_phase7/                  # Phase 7 LoRA weights (130MB)
```

## Key Design Decisions

### AST-based example generation

- Parse Python files using `ast` module
- Extract classes, functions, imports, decorators
- Generate realistic grep/read/direct-answer examples
- 300 grep examples (search patterns)
- 150 read examples (file exploration)
- 100 direct answers (framework concepts)

### Multi-domain training

- **Phase 6:** Python only (794 examples)
  - 244 from Phase 5 (svcs-di, tdom-svcs)
  - 550 from 10 popular repos
- **Phase 7:** Python + HTML (824 examples)
  - 794 from Phase 6
  - 30 HTML examples (semantic HTML, forms, tables, accessibility)

### Progressive scaling

- Phase 5: 244 examples → Phase 6: 794 examples (3.3x)
- Phase 6: 794 examples → Phase 7: 824 examples (+30)
- Result: Better generalization with each phase

## Performance Results

| Phase | Examples | Load Time | Avg Gen Time | Accuracy | Adapter Size |
|-------|----------|-----------|--------------|----------|--------------|
| Phase 5 | 244 | 0.70s | 12.13s | 100% | 0.39 GB |
| Phase 6 | 794 | 1.25s | 11.97s | 100% | 0.13 GB |
| Phase 7 | 824 | **0.68s** | **11.96s** | 100% | 0.13 GB |

**Key findings:**
- More data → better generalization → faster inference
- Multi-domain (Python + HTML) → no performance penalty
- Phase 7 is fastest despite having most training data

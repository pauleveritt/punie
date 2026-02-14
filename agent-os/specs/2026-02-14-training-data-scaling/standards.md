# Training Data Scaling Spec - Standards

## Data Generation Standards

- **AST parsing:** Extract classes, functions, imports from Python files
- **Realistic patterns:** Generate grep/read examples that match actual usage
- **Diverse domains:** Cover 10+ popular Python frameworks
- **Multi-language:** Support Python, HTML (future: CSS, JS)
- **Concept coverage:** Include direct-answer examples for each framework

## Training Data Composition

- **70-80% with tools:** grep, read, write, run_command
- **20-30% without tools:** direct answers from base knowledge
- **Diverse patterns:** Mix search, exploration, concept questions
- **Progressive merging:** Build on previous phases, don't start from scratch

## Training Standards

- **Batch size:** 2 (optimal for 32GB M1 Max)
- **LoRA rank:** 16 (num_layers parameter)
- **Iterations:** 300 (consistent across phases)
- **Peak memory:** Stay under 19GB to avoid OOM
- **Loss tracking:** Monitor both train and validation loss
- **Checkpoints:** Save every 150 iterations

## Quality Standards

- **100% discrimination accuracy:** Tool vs direct-answer queries
- **No performance regression:** Each phase should be ≥ previous phase speed
- **Adapter efficiency:** Smaller adapters preferred (compression through generalization)
- **Multi-domain:** Adding new domains shouldn't hurt existing performance

## Project Standards

- Use Astral tools via skills (`astral:ruff`, `astral:ty`)
- Python 3.14 modern syntax
- No auto-commit — always ask before creating commits
- Document results in phase-specific status files

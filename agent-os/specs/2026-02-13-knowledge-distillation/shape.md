# Knowledge Distillation Spec - Shape

## Architecture

```
scripts/
├── generate_training_data.py      # Original POC examples (Phase 0)
├── convert_training_data.py       # Format converter (Phase 1)
├── generate_domain_examples.py    # Domain + direct-answer examples (Phase 4-5)
└── train_lora.sh                  # Training execution script

data/
├── hand_authored/                 # Original 30 examples (Phase 0)
├── domain_examples.jsonl          # Domain + direct answers (Phase 4-5)
└── mlx_format/                    # Final training data
    ├── train.jsonl                # Training split (219 examples)
    └── valid.jsonl                # Validation split (25 examples)

src/punie/agent/
└── factory.py                     # Fixed stop_sequences key (line 241)

adapters/                          # Phase 5 LoRA weights (44MB)
```

## Key Design Decisions

### Multi-phase approach

- **Phase 0:** Baseline with 69 examples (memorization problem)
- **Phase 1:** Fix tool-call format (`"tool"` → `"name"`)
- **Phase 4:** Add domain data + fix stop sequences
- **Phase 5:** Balance tool vs direct-answer examples

### Training data composition

- **Domain examples:** svcs-di, tdom-svcs patterns (21 examples)
- **POC examples:** Punie-specific tools (28 examples)
- **Public examples:** Generic tool patterns (150 examples)
- **Direct answers:** Concept/comparison/best-practice questions (50 examples)
- **Final split:** 219 train, 25 valid (244 total)

### Stop sequences critical fix

- Key name mismatch: factory.py used `"stop"` but PydanticAI expects `"stop_sequences"`
- Fixed at line 241: `model_settings_dict["stop_sequences"] = list(config.stop_sequences)`
- Result: Infinite loop fixed, model stops at `<|im_end|>` tokens

### Balanced discrimination training

- 67.2% with tools (grep, read, write, run_command)
- 32.8% without tools (direct answers from base knowledge)
- Teaches model when NOT to use tools

## Dependencies

- **mlx-lm>=0.22.0** — LoRA training and inference
- **Qwen2.5-Coder-7B-Instruct-4bit** — Base model
- **pydantic-ai-slim>=0.1.0** — Agent framework

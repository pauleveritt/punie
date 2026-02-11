# Learning Roadmap: Building a Python Coding Agent SLM

This is a deep, layered topic. I'll organize it from **foundational concepts up through agent-specific architecture**,
flagging what matters most for your specific constraints (M1/32GB, Python-focused, tool-calling native).

---

## Layer 0: Foundations You Need First

### Core Transformer Mechanics

- **Attention mechanisms** (self-attention, multi-head attention, KV-caching)
- **Tokenization** — especially critical for code (BPE, SentencePiece, and why code tokenizers like those in CodeLlama
  or StarCoder differ from prose tokenizers)
- **Positional encodings** (RoPE, ALiBi) — matters for long code context windows
- **Embeddings** — token embeddings, learned positional embeddings, and how they form the representation space your
  model thinks in

### Why This Matters for You

A tiny model has very limited representational capacity. Understanding *what* the embedding space is doing helps you
make architectural tradeoffs (embedding dimension, vocabulary size, number of layers vs. width).

---

## Layer 1: Small Language Model Architecture Decisions

This is where your project lives or dies given M1/32GB constraints.

### Model Sizing & Architecture

- **Scaling laws** (Chinchilla, but also the "over-training" regime from TinyLlama, Phi, etc.)
- **Mixture of Experts (MoE)** — lets you have a "larger" model with smaller active parameters per inference step. Very
  relevant for tool-calling where different "experts" could specialize.
- **Depth vs. Width tradeoffs** — deeper narrow models vs. shallow wide models for code
- **Distillation** — training your tiny model to mimic a larger teacher model (the Phi series' core strategy)
- **Pruning & Quantization** — GPTQ, GGUF/llama.cpp quantization, QLoRA; you'll likely need 4-bit quantization to fit
  meaningful models in 32GB

### Key References

- **Phi-1/Phi-1.5/Phi-2 papers** (Microsoft) — the gold standard for "tiny models that punch above their weight,"
  specifically Phi-1 which was Python-focused
- **TinyLlama** — 1.1B model trained on 3T tokens, shows you can over-train small models effectively
- **SmolLM/SmolLM2** (Hugging Face) — recent small models with good design documentation
- **CodeParrot, StarCoder, The Stack** — code-specific training data and models

---

## Layer 2: Code-Specific Representation

### Code Is Not Prose

- **Abstract Syntax Trees (ASTs)** — code has structure that flat token sequences lose. Some architectures inject AST
  awareness.
- **Code-aware tokenization** — handling indentation (critical for Python!), preserving semantic boundaries
- **Infilling / Fill-in-the-Middle (FIM)** — training objective where the model fills in code between prefix and suffix.
  Essential for coding agents.
- **Type-aware representations** — Python has type hints; leveraging them enriches the model's understanding

### Data Curation (Possibly the Most Important Thing)

Phi-1 proved that **data quality >> data quantity** for small models.

- **"Textbook quality" synthetic data** — using a large model to generate high-quality training examples
- **Code deduplication** (MinHash, exact dedup)
- **Quality filtering** — linting, type-checking, test-passing code vs. random GitHub scrapes
- **The Stack v2** and licensing considerations

---

## Layer 3: Tool Calling as a First-Class Architectural Concept

This is where your project gets genuinely interesting. Most models bolt tool-calling on as a fine-tuning afterthought.
You want to **build around it**.

### Fundamental Approaches to Tool Use

#### 3a: Structured Generation / Constrained Decoding

- **Grammar-constrained decoding** (llama.cpp grammars, Outlines, Guidance)
- **JSON Schema-guided generation** — forcing the model to output valid tool calls
- The model doesn't need to "learn" syntax if you constrain it — it just needs to learn *when* and *what*

#### 3b: Special Token Architecture

Design the vocabulary and token space around tool interactions:

```
<|tool_call|>execute_python<|args|>{"code": "print(1+1)"}<|end_call|>
<|tool_result|>2<|end_result|>
<|tool_call|>read_file<|args|>{"path": "main.py"}<|end_call|>
<|tool_result|>def main():...<|end_result|>
```

This is how Gorilla, Hermes, and the function-calling fine-tunes work, but you'd bake it into **pre-training**, not just
fine-tuning.

#### 3c: Tool-Augmented Pre-training (Toolformer Approach)

- **Toolformer** (Meta, 2023) — the model learns *during pre-training* when to insert API calls by self-supervising on
  whether the API result reduces perplexity
- This is the most radical approach: the model doesn't just learn to *format* tool calls, it learns that tools are part
  of how it *thinks*

#### 3d: Interleaved Execution Training

Train on traces where code execution results are interleaved:

```
# I need to find all prime numbers up to 100
<|execute|>
def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True

primes = [n for n in range(101) if is_prime(n)]
print(primes)
<|result|>
[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
<|/result|>
# There are 25 prime numbers up to 100.
```

The model learns that **execution is part of reasoning**, not a separate phase.

### Tool-Calling Design Space for Your Model

Think about what tools a Python coding agent actually needs:

| Tool                       | Purpose                            |
|----------------------------|------------------------------------|
| `execute_python`           | Run code, get stdout/stderr        |
| `read_file` / `write_file` | Filesystem access                  |
| `search_docs`              | Look up Python stdlib/library docs |
| `run_tests`                | Execute pytest, get results        |
| `lint` / `typecheck`       | Get static analysis feedback       |
| `search_codebase`          | Semantic or grep search            |
| `shell`                    | General command execution          |

A radical idea: **make the tool vocabulary part of the token vocabulary**. Tool names become single tokens. This reduces
the sequence length overhead of tool calling.

---

## Layer 4: Retrieval-Augmented Generation (RAG) & Context

### RAG Fundamentals

- **Embedding models** for semantic search (code-specific: CodeBERT, UniXcoder, code-search-net embeddings)
- **Vector databases** (FAISS, Qdrant, ChromaDB — all run on M1)
- **Chunking strategies for code** — function-level, class-level, file-level, dependency-aware chunking
- **Hybrid search** — combining BM25 (keyword) with semantic embeddings

### Context Engineering (The Emerging Discipline)

This is the layer *above* prompting:

- **Context window management** — what goes in, what gets evicted, priority ordering
- **System prompt design** for coding agents
- **Few-shot example selection** — dynamically choosing the most relevant examples
- **Summarization of long contexts** — condensing file contents, execution histories
- **Memory architectures:**
    - **Working memory** (current context window)
    - **Episodic memory** (past interactions, stored in a DB)
    - **Semantic memory** (learned facts about the codebase, embeddings)
    - **Procedural memory** (learned patterns/recipes)

### Relevant Papers & Concepts

- **MemGPT / Letta** — virtual context management, paging context in/out like an OS
- **Reflexion** — agent reflects on past failures stored in memory
- **RAG-Sequence vs. RAG-Token** — retrieve once vs. retrieve per generation step

---

## Layer 5: Agent Architectures & Reasoning

### Agent Loops

- **ReAct** (Reason + Act) — interleaving reasoning traces with actions
- **Plan-and-Execute** — make a plan, then execute steps
- **MCTS / Tree-of-Thought** — exploring multiple solution paths (expensive for small models, but interesting)
- **Recursive Language Models** (the link you shared) — models that can call themselves as subroutines, enabling
  recursive decomposition of problems

### Code-Specific Agent Patterns

- **SWE-Agent** — the leading architecture for GitHub issue resolution
- **Aider** — patterns for interactive code editing
- **OpenDevin/OpenHands** — open-source coding agent framework
- **Cursor / Copilot internal architectures** — speculative decoding, multi-model routing

### Self-Improvement & Feedback Loops

- **RLHF / RLAIF** for code — using execution results as reward signal (code either works or doesn't — you get free
  reward signals!)
- **Self-play** — model generates code, tests it, learns from results
- **Execution-based reinforcement** — the RLEF (Reinforcement Learning from Execution Feedback) concept
- **Constitutional AI patterns** adapted for code safety

---

## Layer 6: Training Pipeline (Practical)

Here's roughly the pipeline you'd implement:

```
1. DATA CURATION
   ├── Source: The Stack v2, synthetic from GPT-4/Claude
   ├── Filter: parseable, passes lint, has docstrings
   ├── Augment: add tool-call annotations (Toolformer-style)
   └── Format: interleaved execution traces

2. PRE-TRAINING
   ├── Tokenizer: custom, code-aware, tool-tokens built in
   ├── Architecture: transformer (maybe MoE), ~1-3B params
   ├── Objectives: next-token + FIM + tool-call prediction
   └── Infrastructure: M1 + MLX or PyTorch MPS

3. FINE-TUNING
   ├── Instruction tuning on coding tasks
   ├── Tool-calling specific fine-tuning
   ├── DPO/RLHF with execution feedback
   └── QLoRA to fit in memory

4. INFERENCE OPTIMIZATION
   ├── Quantization (4-bit GGUF)
   ├── KV-cache optimization
   ├── Speculative decoding (if you have a tiny draft model)
   └── Grammar-constrained decoding for tool calls

5. AGENT HARNESS
   ├── Context engineering / prompt management
   ├── Tool execution sandbox
   ├── RAG pipeline for codebase knowledge
   └── Memory management (MemGPT-style)
```

### M1-Specific Training Frameworks

- **MLX** (Apple's framework) — native M1 support, increasingly good
- **PyTorch with MPS backend** — works but less optimized than MLX
- **llama.cpp** — for inference, extremely well-optimized for Apple Silicon
- **mlx-lm** — fine-tuning in MLX ecosystem

Realistic scope at 32GB: you can **fine-tune** models up to ~7B (quantized) and **pre-train** models up to ~1-3B with
patience. Pre-training a 1B model from scratch on M1 is feasible but slow (weeks).

---

## Layer 7: Cutting-Edge Ideas Worth Exploring

### For Your Specific Project

1. **Executable embeddings** — what if code embeddings include execution trace information, not just syntax?

2. **Tool-tokens with learned routing** — each tool gets a special token, and a small router network learns which tool
   to invoke based on hidden state (like MoE routing but for tools)

3. **Recursive self-calling** (from your RLM link) — the model can emit a `<|self_call|>` token that triggers a
   sub-invocation with a sub-task, enabling compositional reasoning within limited context

4. **Speculative tool calling** — model predicts tool results to keep generating, then verifies against actual
   execution (like speculative decoding but for tools)

5. **Grounded pre-training** — every code example in training data includes execution results, so the model never
   learns "ungrounded" code generation

6. **State-space models for code** (Mamba-style) — potentially more efficient than transformers for long code sequences,
   and very efficient on Apple Silicon

7. **Retrieval-augmented training** (RETRO-style) — bake retrieval into the architecture itself, not just at inference
   time

---

## Recommended Study Order

```
Phase 1 (Foundations):          ~2-4 weeks
  ├── Transformer mechanics (Attention Is All You Need)
  ├── Andrej Karpathy's "Let's build GPT" video
  ├── Tokenization (HuggingFace NLP course, BPE paper)
  └── Train a tiny GPT-2 on Python code (nanoGPT)

Phase 2 (Code Models):         ~2-3 weeks
  ├── Phi-1 paper (critical for your project)
  ├── StarCoder / SantaCoder papers
  ├── Fill-in-the-Middle training
  └── Distillation & quantization basics

Phase 3 (Tool Use):            ~2-3 weeks
  ├── Toolformer paper
  ├── Gorilla paper (LLM tool calling)
  ├── Structured generation (Outlines library)
  └── Function-calling fine-tuning datasets (Glaive, Hermes)

Phase 4 (Agents):              ~2-3 weeks
  ├── ReAct paper
  ├── SWE-Agent paper
  ├── MemGPT paper
  └── Build a simple agent loop with tool calling

Phase 5 (Integration):         ~4+ weeks
  ├── Design your architecture
  ├── Curate your dataset
  ├── Train on M1 with MLX
  └── Build the agent harness
```

---

## Key Papers Shortlist

| Paper                                                       | Why It Matters                                   |
|-------------------------------------------------------------|--------------------------------------------------|
| **Phi-1** (Gunasekar et al., 2023)                          | Proves tiny models can code well with great data |
| **Toolformer** (Schick et al., 2023)                        | Tool use learned during pre-training             |
| **ReAct** (Yao et al., 2023)                                | Foundational agent reasoning pattern             |
| **SWE-Agent** (Yang et al., 2024)                           | State-of-art coding agent design                 |
| **MemGPT** (Packer et al., 2023)                            | Virtual context management                       |
| **Reflexion** (Shinn et al., 2023)                          | Self-reflection for agents                       |
| **RETRO** (Borgeaud et al., 2022)                           | Retrieval baked into architecture                |
| **RLMs** (Zhang, 2025)                                      | Recursive self-calling models                    |
| **Scaling Data-Constrained LMs** (Muennighoff et al., 2023) | How to over-train small models                   |
| **StarCoder2** (Lozhkov et al., 2024)                       | Modern code LM training recipe                   |

This is a genuinely ambitious project. The most impactful novel contribution you could make is in **Layer 3** — making
tool-calling architectural rather than an afterthought. The combination of Toolformer-style pre-training + special tool
tokens + constrained decoding is under-explored at the small model scale.
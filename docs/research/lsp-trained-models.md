# Open Source Research in LSP-Trained Coding Agents

This is a pretty specific intersection — RL-trained agents with code intelligence as a first-class primitive — and
honestly, **nothing squarely targets this** in the open source world. But there are projects that touch adjacent pieces
and could serve as foundations:

## Closest to the Vision

**SWE-Agent** (Princeton NLP)

- Defines a custom **Agent-Computer Interface (ACI)** — the key insight being that the action space design matters
  enormously for agent performance
- Currently uses shell/edit primitives, but the architecture is explicitly designed to be extended with new actions
- This is probably the most natural place where LSP actions could be added as research
- [github.com/princeton-nlp/SWE-agent](https://github.com/princeton-nlp/SWE-agent)

**OpenHands (formerly OpenDevin)**

- Open source coding agent platform with a pluggable action space
- Has an active research community exploring what tools/primitives improve agent performance
- Could support LSP integration as a new runtime capability
- [github.com/All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands)

**Aider**

- Not RL-trained, but interesting because it uses **tree-sitter** to build repository maps — essentially a lightweight
  version of code intelligence to give the model structural context
- Demonstrates that even crude structural awareness significantly improves performance
- [github.com/paul-gauthier/aider](https://github.com/paul-gauthier/aider)

## RL Training Infrastructure

**OpenRL / RL4LMs / TRL (Hugging Face)**

- General frameworks for RL training of language models
- You could build a custom environment where LSP diagnostics serve as reward signals
- None of them do this out of the box

**SWE-bench**

- The benchmark used to evaluate coding agents — defines tasks as GitHub issues with test suites
- Reward signal is test passage, not LSP diagnostics, but you could imagine an augmented version that includes
  type-checking and static analysis as intermediate rewards

## Compiler/Analyzer Feedback in Training

**RLCF (Reinforcement Learning from Compiler Feedback)**

- Some academic papers have explored using compiler errors as reward signals
- Not a single well-known open source project, but search for papers like "RLCF" or "compiler feedback reinforcement
  learning"

**CodeRL** (Salesforce Research)

- Used program execution feedback to improve code generation via RL
- The architecture of using structured program analysis as reward is very similar to what LSP training would look like
- [github.com/salesforce/CodeRL](https://github.com/salesforce/CodeRL)

## The Gap

What **doesn't exist** as an open source project:

```
Environment where:
  - Agent actions include LSP operations
  - LSP diagnostic state is part of observation
  - Reward function incorporates type-safety / reference resolution
  - RL training loop optimizes agent behavior over this action space
```

This is a genuinely open research project. The pieces exist separately:

| Component                       | Exists? | Where                                           |
|---------------------------------|---------|-------------------------------------------------|
| LSP servers for major languages | ✅       | rust-analyzer, typescript-language-server, etc. |
| RL training for LLMs            | ✅       | TRL, OpenRL                                     |
| Coding agent frameworks         | ✅       | SWE-Agent, OpenHands                            |
| Coding benchmarks               | ✅       | SWE-bench, HumanEval                            |
| Integration of all the above    | ❌       | **Nobody yet**                                  |

## If Someone Wanted to Start

The most tractable path would probably be:

1. **Fork SWE-Agent** (it's designed for action space research)
2. **Add LSP actions** to its interface (go-to-definition, find-references, diagnostics)
3. **Evaluate on SWE-bench** — does access to LSP actions improve solve rates even without RL training?
4. **Then** explore RL fine-tuning with LSP diagnostic feedback as reward signal

Step 3 alone would be a publishable result and would answer the threshold question: does structured code intelligence
help agents even as an external tool before you invest in training?

This is a space where a well-scoped open source project could genuinely advance the field. The pieces are all there —
they just haven't been assembled.
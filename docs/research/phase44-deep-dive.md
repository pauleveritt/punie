# Phase 44 Deep Dive Analysis

**Date:** 2026-02-18T22:17:12
**Model:** `fused_model_qwen3_phase44_format_fix_5bit`
**Overall eval score:** 16.7%
**Eval verdict:** ❌ FAIL

---

## Executive Summary

Phase 44 scored **16.7%**. Issues found:
- Methodology flags: 7 FP, 18 FN

---

## 1. Eval Results

| Category | Score |
|----------|-------|
| cst | 0.0% (0/3) |
| domain | 0.0% (0/9) |
| git | 33.3% (2/3) |
| lsp | 20.0% (2/5) |
| multi_tool | 0.0% (0/1) |
| text_tools | 33.3% (2/3) |
| validation | 50.0% (3/3) |
| **Overall** | **16.7%** |

### Per-Prompt Scores

| ID | Score | EC | Time | Notes |
|----|-------|-----|------|-------|
| text-01 | 0.00 | ✗ | 31.5s | ````python
# src/punie/agent/config.py
from typing import Opt` |
| text-02 | 0.50 | ✗ | 1.8s | `I'll help you write the text 'Phase 33 complete' to the outp` |
| text-03 | 0.50 | ✗ | 13.4s | `I'll run a command to see what Python files are in the src d` |
| valid-01 | 0.50 | ✗ | 13.4s | `I'll run type checking on the src/ directory to check for an` |
| valid-02 | 0.50 | ✗ | 1.6s | `I'll check the src/ directory for linting violations using r` |
| valid-03 | 0.50 | ✗ | 11.4s | `I'll help you run the test suite and report the results. Let` |
| lsp-01 | 0.50 | ✗ | 13.5s | `I need to find the definition of `AgentConfig` in the codeba` |
| lsp-02 | 0.00 | ✗ | 13.5s | `I'll search for all references to `execute_code` across the ` |
| lsp-03 | 0.00 | ✗ | 13.5s | `I'll help you find information about LoRAConfig. Let me sear` |
| lsp-04 | 0.00 | ✗ | 2.6s | `I need to examine the contents of the LoRA configuration fil` |
| lsp-05 | 0.50 | ✗ | 58.6s | `I'll search for any symbol named "TrainingResult" in the wor` |
| git-01 | 0.50 | ✗ | 0.8s | ````python
git_status()
```
```python
git_diff()
```` |
| git-02 | 0.00 | ✗ | 2.8s | `I'll help you show the git diff for uncommitted changes. Let` |
| git-03 | 0.50 | ✗ | 1.8s | `I'll help you get the 5 most recent git commits. I'll use th` |
| cst-01 | 0.00 | ✗ | 14.1s | `I need to find all class definitions in the websocket.py fil` |
| cst-02 | 0.00 | ✗ | 14.1s | `I need to find and rename `TrainingResult` to `FineTuneResul` |
| cst-03 | 0.00 | ✗ | 9.9s | `I need to add the import statement `from collections import ` |
| dom-01 | 0.00 | ✗ | 4.7s | `I'll check if `src/views/error_page.py` is a valid tdom comp` |
| dom-02 | 0.00 | ✗ | 14.1s | `I need to check the service registration in src/services/use` |
| dom-03 | 0.00 | ✗ | 14.1s | `I need to check if the circuit breaker middleware follows th` |
| dom-04 | 0.00 | ✗ | 14.1s | `I'll check for dependency graph violations in the report_ser` |
| dom-05 | 0.00 | ✗ | 14.2s | `I need to check the registration.py file to see if it uses t` |
| dom-06 | 0.00 | ✗ | 14.0s | `I'll validate the route patterns in src/routes/api.py to ens` |
| dom-07 | 0.00 | ✗ | 14.0s | `I need to verify the render tree composition in the checkout` |
| dom-08 | 0.00 | ✗ | 14.1s | `I need to check the imports in the `src/services/billing_ser` |
| dom-09 | 0.00 | ✗ | 14.1s | `I need to check if html() calls in src/views/account.py pass` |
| multi-01 | 0.00 | ✗ | 28.8s | `I'll help you find the definition of HomeView, read it, and ` |

---

## 2. Methodology Audit

**Verdict:** FLAGS_FOUND
**Score distribution:** {0.0: 18, 0.5: 9}

**Suspected false positives:** text-03, valid-01, valid-02, valid-03, lsp-01, lsp-05, git-03
**Suspected false negatives:** text-01, lsp-02, lsp-03, lsp-04, git-02, cst-01, cst-02, cst-03, dom-01, dom-02, dom-03, dom-04, dom-05, dom-06, dom-07, dom-08, dom-09, multi-01

### Per-Prompt Methodology Flags

| ID | Score | EC | Flags |
|----|-------|-----|-------|
| text-01 | 0.0 | ✗ | zero_score_with_content |
| text-02 | 0.5 | ✗ | — |
| text-03 | 0.5 | ✗ | possible_prose_false_positive |
| valid-01 | 0.5 | ✗ | possible_prose_false_positive |
| valid-02 | 0.5 | ✗ | possible_prose_false_positive |
| valid-03 | 0.5 | ✗ | possible_prose_false_positive |
| lsp-01 | 0.5 | ✗ | possible_prose_false_positive |
| lsp-02 | 0.0 | ✗ | zero_score_with_content |
| lsp-03 | 0.0 | ✗ | zero_score_with_content |
| lsp-04 | 0.0 | ✗ | zero_score_with_content |
| lsp-05 | 0.5 | ✗ | possible_prose_false_positive |
| git-01 | 0.5 | ✗ | — |
| git-02 | 0.0 | ✗ | zero_score_with_content |
| git-03 | 0.5 | ✗ | possible_prose_false_positive |
| cst-01 | 0.0 | ✗ | zero_score_with_content |
| cst-02 | 0.0 | ✗ | zero_score_with_content |
| cst-03 | 0.0 | ✗ | zero_score_with_content |
| dom-01 | 0.0 | ✗ | zero_score_with_content |
| dom-02 | 0.0 | ✗ | zero_score_with_content |
| dom-03 | 0.0 | ✗ | zero_score_with_content |
| dom-04 | 0.0 | ✗ | zero_score_with_content |
| dom-05 | 0.0 | ✗ | zero_score_with_content |
| dom-06 | 0.0 | ✗ | zero_score_with_content |
| dom-07 | 0.0 | ✗ | zero_score_with_content |
| dom-08 | 0.0 | ✗ | zero_score_with_content |
| dom-09 | 0.0 | ✗ | zero_score_with_content |
| multi-01 | 0.0 | ✗ | zero_score_with_content |

---

## 3. Consistency Check

**Verdict:** PASS

| Prompt | Run 1 | Run 2 | Run 3 | Consistent |
|--------|-------|-------|-------|------------|
| git-01 | 1.0 | 1.0 | 1.0 | ✓ |
| valid-01 | 1.0 | 1.0 | 1.0 | ✓ |
| cst-01 | 1.0 | 1.0 | 1.0 | ✓ |
| dom-01 | 1.0 | 1.0 | 1.0 | ✓ |
| multi-01 | 1.0 | 1.0 | 1.0 | ✓ |

---

## 4. Think-Mode Analysis

**Verdict:** NO_THINK

**Zero score but has content:** text-01, lsp-02, lsp-03, lsp-04, git-02, cst-01, cst-02, cst-03, dom-01, dom-02, dom-03, dom-04, dom-05, dom-06, dom-07, dom-08, dom-09, multi-01

**Think-mode probe** (prompt sent without `<think>` stop sequence):
- Starts with `<think>`: **False**
- Content length: 0 chars
- Preview: ``

---

## 5. Performance Benchmark

**Phase 44 model:** `fused_model_qwen3_phase44_format_fix_5bit`
**Peak GPU mem (training):** 21.302 GB (from training log)
**Model size on disk:** 21.0 GB

### Warm Query Timing (after model loaded)

| Prompt | p50 | p95 | min | max | errors |
|--------|-----|-----|-----|-----|--------|
| git-01 | 2.6s | 2.6s | 2.6s | 2.6s | 0 |
| valid-01 | 2.9s | 2.9s | 2.9s | 2.9s | 0 |
| cst-01 | 3.0s | 3.0s | 3.0s | 3.0s | 0 |
| dom-01 | 4.7s | 5.1s | 4.7s | 5.1s | 0 |
| multi-01 | 4.1s | 4.5s | 4.1s | 4.5s | 0 |

### Comparison: Phase 33b Production (`fused_model_qwen3_phase33b_5bit`)

| Prompt | p50 (44) | p50 (33b) | Delta |
|--------|----------|-----------|-------|
| git-01 | 2.6s | 2.4s | +0.2s |
| valid-01 | 2.9s | 2.8s | +0.2s |
| cst-01 | 3.0s | 2.9s | +0.1s |
| dom-01 | 4.7s | 2.9s | +1.8s |
| multi-01 | 4.1s | 2.5s | +1.6s |

---

## 6. Findings and Recommendations

Generated: 2026-02-18T22:17:12
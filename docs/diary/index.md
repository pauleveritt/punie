# Diary

Reverse-chronological notes from ongoing work. Each entry is summarized and dated.

## 2026-02-16 - [Phase 29: Toad WebSocket Client Implementation](2026-02-16-phase29-toad-websocket-client.md)
Built WebSocket client infrastructure for Toad frontend integration. Added 4 core functions (create_toad_session, send_prompt_stream, handle_tool_update, run_toad_client) with streaming support and tool execution visibility. 345 lines implementation + 457 lines tests (11 tests, all passing) + 573 lines documentation. Browser-compatible callback API. 620 total tests passing. Ready for Toad UI integration!

## 2026-02-16 - [Gate 0 Failure: Devstral Small 2 Unsuitable for Punie](2026-02-16-devstral-gate0-failure.md)
Evaluated Devstral Small 2 (24B) as Qwen3 replacement using gated approach. Gate 0 failed in 5 minutes: closing delimiter `[/TOOL_CALLS]` tokenizes as 7 pieces (not single token), would corrupt training data like Phase 25. Saved ~7 days of futile work. Decision: Continue using Qwen3-30B-A3B (Phase 27's 100% accurate model).

## 2026-02-16 - [Phase 28: Server/Client Separation Architecture](2026-02-16-phase28-server-client-separation.md)
Refactored Punie from monolithic dual-protocol to clean server/client separation. Server now runs HTTP/WebSocket only (no stdio), enabling background operation. Created 3 client modules (477 lines): stdio bridge for PyCharm, ask client for CLI, and connection utilities. All 609 tests passing, 3 new integration tests. Production ready: `punie serve &` now works!

## 2026-02-14 - [Phase 21: XML Format Fix Achieves 100% Tool-Calling Accuracy](2026-02-14-phase21-xml-format-fix.md)
Fixed critical tool-calling regression (40% → 100% accuracy) by converting training data from JSON to XML format to match mlx_lm.server expectations. Model now production-ready: 20GB, 6.6s tool queries, 1.8s direct answers. Speculative decoding infrastructure implemented but benchmarking deferred in favor of Phase 22 (Code Mode).

## 2026-02-14 - [Quantization Breakthrough: 5-bit Preserves LoRA Fine-tuning](2026-02-14-quantization-breakthrough.md)
Discovered that 5-bit quantization (32 levels) is the minimum threshold for preserving LoRA fine-tuning quality. Reduced Phase 8 model from 30GB (8-bit) to 20GB (5-bit) with 100% accuracy maintained. Scientific finding: LoRA signal preservation threshold is between 16 and 32 quantization levels.

## 2026-02-13 - [Phase 5: Tool vs. Direct Answer Discrimination](phase5_summary.md)
Expanded direct-answer training examples from 5 to 50, achieved 100% discrimination accuracy distinguishing tool-calling vs direct-answer queries, with benchmark showing +40pp quality improvement at cost of +53.7% slower generation.

## 2026-02-13 - [Phase 2 Final Summary - February 13, 2026](PHASE2_FINAL_SUMMARY.md)
Final Phase 2 summary covering fixes, POC dataset, training results, and hardware limitations.

## 2026-02-13 - [Phase 2 Completion Guide](PHASE2_COMPLETION_GUIDE.md)
Guide to complete Phase 2 after code fixes, including generator bug fix, converter updates, and format notes.

## 2026-02-13 - [Model Performance Tracker](MODEL_PERFORMANCE_TRACKER.md)
Tracker of model size, memory, speed, tool use, and accuracy across phases with key findings.

## 2026-02-13 - [Knowledge Distillation Experiment: 30B → 7B](KNOWLEDGE_DISTILLATION_SUMMARY.md)
Summary of the 30B-to-7B distillation experiment, results, limitations, and lessons learned.

## 2026-02-12 - [What I Did While You Were Away ✅](WHILE_YOU_WERE_AWAY.md)
Recap of completed work, experiment readiness, and next steps while you were away.

## 2026-02-12 - [Training Summary: Deep Testing Phase Complete](TRAINING_SUMMARY.md)
Deep testing summary showing base model outperforms fine-tuned adapters and key evaluation outcomes.

## 2026-02-12 - [Three-Step Implementation: Complete Summary](THREE_STEP_IMPLEMENTATION_SUMMARY.md)
Summary of the three-step implementation to fix tool signatures, validate results, and build the eval suite.

## 2026-02-12 - [Protocol Subclass Search: 1.5B Model vs Claude Code](PROTOCOL_SEARCH_COMPARISON.md)
Comparison of protocol search results between a 1.5B model and Claude Code, highlighting tool-use differences.

## 2026-02-12 - [Protocol Search Benchmark: Claude Code vs 30B](BENCHMARK_COMPARISON.md)
Benchmark comparison of protocol search between Claude Code and a 30B model, showing Claude is faster and lighter with equal accuracy.

## 2026-02-12 - [Overnight Knowledge Distillation - Status](OVERNIGHT_STATUS.md)
Overnight pipeline status with PIDs, timeline, monitoring commands, and morning checklist.

## 2026-02-12 - [Model Testing Results: Path to Production-Ready Agent](MODEL_TESTING_RESULTS.md)
Testing results for 1.5B and 30B models on autonomous tool use, with comparison matrix and findings.

## 2026-02-12 - [Knowledge Distillation: Data Generation In Progress 🚀](DATA_GENERATION_STATUS.md)
Status update on distillation training data generation, including progress, timeline, query categories, and output files.

## 2026-02-12 - [Knowledge Distillation Workflow: 30B → 7B](DISTILLATION_WORKFLOW.md)
End-to-end workflow for distilling 30B tool-use into 7B, covering phases, scripts, and monitoring steps.

## 2026-02-12 - [Knowledge Distillation Plan: 30B → 7B](KNOWLEDGE_DISTILLATION_PLAN.md)
Detailed plan for distilling 30B reasoning into 7B, including dataset requirements, phases, and strategy.

## 2026-02-12 - [Experiments Ready to Run! 🚀](EXPERIMENTS_READY.md)
Checklist and instructions for running prepared experiments, with RAM requirements and expected outputs.

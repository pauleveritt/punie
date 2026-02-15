"""Pipeline validation checks for detecting training failures early.

This module provides validation functions that catch common failure modes
at each stage of the training pipeline, preventing issues from going
undetected for multiple development phases.

Each check function returns a CheckResult with pass/fail status, messages,
and optional details. All checks are pure functions that can be tested
without MLX hardware.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from punie.training.dataset import TrainingDataset
from punie.training.dataset_validation import validate_dataset
from punie.training.hyperparam import parse_training_log
from punie.training.tool_call_parser import parse_tool_calls


@dataclass(frozen=True)
class CheckResult:
    """Result of a validation check.

    Attributes:
        check_name: Name of the check that was run
        passed: True if check passed, False if it failed
        message: Human-readable message describing the result
        warnings: Tuple of warning messages (non-fatal issues)
        details: Optional dictionary with additional check-specific details
    """

    check_name: str
    passed: bool
    message: str
    warnings: tuple[str, ...] = ()
    details: dict[str, object] | None = None


# Pre-training checks (validate data before training)


def check_format_consistency(
    data_directory: Path, expected_format: str = "messages"
) -> CheckResult:
    """Verify all training data uses consistent top-level format.

    Checks that every JSONL file uses the expected top-level key
    (either "messages" or "text"), catching format mismatches early.

    Args:
        data_directory: Directory containing training JSONL files
        expected_format: Expected top-level key ("messages" or "text")

    Returns:
        CheckResult indicating pass/fail with details about format issues

    Catches:
        - JSON vs XML format mismatches (Phases 8-20)
        - {messages} vs {text} format drift (Phase 6)
    """
    if not data_directory.exists():
        return CheckResult(
            check_name="check_format_consistency",
            passed=False,
            message=f"Data directory does not exist: {data_directory}",
        )

    issues = []
    total_files = 0
    total_lines = 0

    for jsonl_file in data_directory.glob("**/*.jsonl"):
        total_files += 1
        with open(jsonl_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    if expected_format not in data:
                        issues.append(
                            f"{jsonl_file.name}:{line_num} - "
                            f"Missing '{expected_format}' key, found: {list(data.keys())}"
                        )
                except json.JSONDecodeError as e:
                    issues.append(
                        f"{jsonl_file.name}:{line_num} - Invalid JSON: {e}"
                    )

    if not total_files:
        return CheckResult(
            check_name="check_format_consistency",
            passed=False,
            message=f"No JSONL files found in {data_directory}",
        )

    if issues:
        return CheckResult(
            check_name="check_format_consistency",
            passed=False,
            message=f"Found {len(issues)} format issues across {total_files} files",
            details={"issues": issues[:10], "total_issues": len(issues)},
        )

    return CheckResult(
        check_name="check_format_consistency",
        passed=True,
        message=f"All {total_lines} examples use '{expected_format}' format consistently",
        details={"files_checked": total_files, "lines_checked": total_lines},
    )


def check_training_data_distribution(
    data_directory: Path, max_tool_pct: float = 0.80, min_tool_pct: float = 0.10
) -> CheckResult:
    """Check tool-calling vs direct-answer distribution in training data.

    Verifies the dataset has a balanced mix of tool-calling and direct-answer
    examples, catching overly tool-heavy or tool-light datasets.

    Args:
        data_directory: Directory containing training JSONL files
        max_tool_pct: Maximum allowed percentage of tool-calling examples
        min_tool_pct: Minimum required percentage of tool-calling examples

    Returns:
        CheckResult indicating pass/fail with distribution details

    Catches:
        - 97.5% tool-heavy data (Phases 4-5)
        - Datasets lacking tool-calling examples
    """
    if not data_directory.exists():
        return CheckResult(
            check_name="check_training_data_distribution",
            passed=False,
            message=f"Data directory does not exist: {data_directory}",
        )

    tool_examples = 0
    direct_examples = 0

    for jsonl_file in data_directory.glob("**/*.jsonl"):
        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    # Check if this is a tool-calling example
                    # Look in assistant messages for tool call markers
                    is_tool_example = False

                    if "messages" in data:
                        for msg in data["messages"]:
                            if msg.get("role") == "assistant":
                                content = msg.get("content", "")
                                if (
                                    "<tool_call>" in content
                                    or "```json" in content
                                    or "<function=" in content
                                ):
                                    is_tool_example = True
                                    break

                    if is_tool_example:
                        tool_examples += 1
                    else:
                        direct_examples += 1

                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    total_examples = tool_examples + direct_examples
    if total_examples == 0:
        return CheckResult(
            check_name="check_training_data_distribution",
            passed=False,
            message=f"No valid examples found in {data_directory}",
        )

    tool_pct = tool_examples / total_examples

    warnings = []
    if tool_pct > max_tool_pct:
        return CheckResult(
            check_name="check_training_data_distribution",
            passed=False,
            message=f"Tool-calling examples at {tool_pct:.1%} exceeds maximum {max_tool_pct:.1%}",
            details={
                "tool_examples": tool_examples,
                "direct_examples": direct_examples,
                "tool_percentage": tool_pct,
            },
        )

    if tool_pct < min_tool_pct:
        warnings.append(
            f"Tool-calling examples at {tool_pct:.1%} below recommended minimum {min_tool_pct:.1%}"
        )

    return CheckResult(
        check_name="check_training_data_distribution",
        passed=True,
        message=f"Distribution acceptable: {tool_pct:.1%} tool-calling, {1-tool_pct:.1%} direct",
        warnings=tuple(warnings),
        details={
            "tool_examples": tool_examples,
            "direct_examples": direct_examples,
            "tool_percentage": tool_pct,
        },
    )


def check_training_data_content(
    data_directory: Path, max_empty_pct: float = 0.10
) -> CheckResult:
    """Check for empty or placeholder tool results in training data.

    Scans assistant messages in tool-calling examples to detect empty
    or placeholder tool results that would harm training quality.

    Args:
        data_directory: Directory containing training JSONL files
        max_empty_pct: Maximum allowed percentage of tool examples with empty results

    Returns:
        CheckResult indicating pass/fail with content quality details

    Catches:
        - Generator swallowing tool results (Phases 1-2)
        - Placeholder content like "[Tool execution completed]"
    """
    if not data_directory.exists():
        return CheckResult(
            check_name="check_training_data_content",
            passed=False,
            message=f"Data directory does not exist: {data_directory}",
        )

    tool_examples = 0
    empty_results = 0
    placeholder_patterns = [
        r"\[Tool execution completed\]",
        r"\[No output\]",
        r"<tool_result>\s*</tool_result>",
        r"<tool_result></tool_result>",
    ]

    for jsonl_file in data_directory.glob("**/*.jsonl"):
        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    if "messages" not in data:
                        continue

                    # Look for tool-calling examples with tool results
                    has_tool_call = False
                    has_empty_result = False

                    for msg in data["messages"]:
                        content = msg.get("content", "")

                        # Check if this message has a tool call
                        if (
                            msg.get("role") == "assistant"
                            and (
                                "<tool_call>" in content
                                or "```json" in content
                                or "<function=" in content
                            )
                        ):
                            has_tool_call = True

                        # Check if this is a tool result (usually from user role)
                        if msg.get("role") == "user" and "<tool_result>" in content:
                            # Check for empty or placeholder results
                            result_match = re.search(
                                r"<tool_result>(.*?)</tool_result>",
                                content,
                                re.DOTALL,
                            )
                            if result_match:
                                result_content = result_match.group(1).strip()
                                if not result_content or any(
                                    re.search(pattern, result_content)
                                    for pattern in placeholder_patterns
                                ):
                                    has_empty_result = True

                    if has_tool_call:
                        tool_examples += 1
                        if has_empty_result:
                            empty_results += 1

                except json.JSONDecodeError:
                    continue

    if tool_examples == 0:
        return CheckResult(
            check_name="check_training_data_content",
            passed=True,
            message="No tool-calling examples found (check not applicable)",
            warnings=("Consider adding tool-calling examples to dataset",),
        )

    empty_pct = empty_results / tool_examples

    if empty_pct > max_empty_pct:
        return CheckResult(
            check_name="check_training_data_content",
            passed=False,
            message=f"{empty_pct:.1%} of tool examples have empty results (max {max_empty_pct:.1%})",
            details={
                "tool_examples": tool_examples,
                "empty_results": empty_results,
                "empty_percentage": empty_pct,
            },
        )

    return CheckResult(
        check_name="check_training_data_content",
        passed=True,
        message=f"Tool results quality acceptable: {empty_pct:.1%} empty ({empty_results}/{tool_examples})",
        details={
            "tool_examples": tool_examples,
            "empty_results": empty_results,
            "empty_percentage": empty_pct,
        },
    )


def check_training_data_coverage(
    data_directory: Path, expected_patterns: tuple[str, ...]
) -> CheckResult:
    """Check that training data covers expected patterns.

    Verifies that training data contains examples of key patterns like
    field access (.error_count, .violations, .passed) that the model
    needs to learn.

    Args:
        data_directory: Directory containing training JSONL files
        expected_patterns: Tuple of patterns that should appear in data

    Returns:
        CheckResult indicating pass/fail with coverage details

    Catches:
        - 0% field access despite "working" typed tools (Phases 22-24)
        - Missing examples of important patterns
    """
    if not data_directory.exists():
        return CheckResult(
            check_name="check_training_data_coverage",
            passed=False,
            message=f"Data directory does not exist: {data_directory}",
        )

    pattern_counts: dict[str, int] = {pattern: 0 for pattern in expected_patterns}
    total_examples = 0

    for jsonl_file in data_directory.glob("**/*.jsonl"):
        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    total_examples += 1

                    # Check all message content for patterns
                    if "messages" in data:
                        for msg in data["messages"]:
                            content = msg.get("content", "")
                            for pattern in expected_patterns:
                                if pattern in content:
                                    pattern_counts[pattern] += 1

                except json.JSONDecodeError:
                    continue

    if total_examples == 0:
        return CheckResult(
            check_name="check_training_data_coverage",
            passed=False,
            message=f"No valid examples found in {data_directory}",
        )

    missing_patterns = [
        pattern for pattern, count in pattern_counts.items() if count == 0
    ]

    if missing_patterns:
        return CheckResult(
            check_name="check_training_data_coverage",
            passed=False,
            message=f"{len(missing_patterns)} expected patterns have zero coverage",
            details={
                "missing_patterns": missing_patterns,
                "pattern_counts": pattern_counts,
                "total_examples": total_examples,
            },
        )

    warnings = []
    low_coverage = [
        (pattern, count)
        for pattern, count in pattern_counts.items()
        if count < 3  # Warn if pattern appears fewer than 3 times
    ]
    if low_coverage:
        warnings.append(
            f"Low coverage for: {', '.join(f'{p}({c})' for p, c in low_coverage)}"
        )

    return CheckResult(
        check_name="check_training_data_coverage",
        passed=True,
        message=f"All {len(expected_patterns)} expected patterns found in dataset",
        warnings=tuple(warnings),
        details={
            "pattern_counts": pattern_counts,
            "total_examples": total_examples,
        },
    )


def check_system_prompt_consistency(
    data_directory: Path, expected_system_prompt: str | None = None
) -> CheckResult:
    """Check system prompt consistency across training data.

    Verifies that system prompts in training data match the expected
    runtime prompt, catching drift between training and production.

    Args:
        data_directory: Directory containing training JSONL files
        expected_system_prompt: Expected system prompt (if None, just checks consistency)

    Returns:
        CheckResult indicating pass/fail with consistency details

    Catches:
        - System prompt drift between training and runtime (Phase 6)
    """
    if not data_directory.exists():
        return CheckResult(
            check_name="check_system_prompt_consistency",
            passed=False,
            message=f"Data directory does not exist: {data_directory}",
        )

    system_prompts: dict[str, int] = {}
    examples_with_system = 0
    total_examples = 0

    for jsonl_file in data_directory.glob("**/*.jsonl"):
        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    total_examples += 1

                    if "messages" in data and data["messages"]:
                        first_msg = data["messages"][0]
                        if first_msg.get("role") == "system":
                            content = first_msg.get("content", "")
                            system_prompts[content] = system_prompts.get(content, 0) + 1
                            examples_with_system += 1

                except json.JSONDecodeError:
                    continue

    if total_examples == 0:
        return CheckResult(
            check_name="check_system_prompt_consistency",
            passed=False,
            message=f"No valid examples found in {data_directory}",
        )

    if not system_prompts:
        return CheckResult(
            check_name="check_system_prompt_consistency",
            passed=False,
            message="No system prompts found in training data",
            warnings=("Consider adding system prompts to examples",),
        )

    # Check if all examples use the same system prompt
    if len(system_prompts) > 1:
        sorted_prompts = sorted(system_prompts.items(), key=lambda x: x[1], reverse=True)
        return CheckResult(
            check_name="check_system_prompt_consistency",
            passed=False,
            message=f"Found {len(system_prompts)} different system prompts",
            details={
                "prompt_variants": len(system_prompts),
                "most_common": sorted_prompts[0][1],
                "examples_with_system": examples_with_system,
            },
        )

    # If expected prompt provided, check if it matches
    actual_prompt = list(system_prompts.keys())[0]
    if expected_system_prompt is not None:
        if actual_prompt != expected_system_prompt:
            return CheckResult(
                check_name="check_system_prompt_consistency",
                passed=False,
                message="System prompt in data doesn't match expected prompt",
                details={
                    "expected_length": len(expected_system_prompt),
                    "actual_length": len(actual_prompt),
                    "match": False,
                },
            )

    return CheckResult(
        check_name="check_system_prompt_consistency",
        passed=True,
        message=f"System prompt consistent across {examples_with_system} examples",
        details={"examples_with_system": examples_with_system, "total_examples": total_examples},
    )


def check_dataset_structural_validation(dataset: TrainingDataset) -> CheckResult:
    """Run structural validation on TrainingDataset.

    Wraps existing validate_dataset() from dataset_validation.py,
    which checks message structure, roles, and content.

    Args:
        dataset: TrainingDataset to validate

    Returns:
        CheckResult indicating pass/fail with validation errors

    Catches:
        - General structural issues (empty messages, invalid roles, etc.)
    """
    errors = validate_dataset(dataset)

    if errors:
        return CheckResult(
            check_name="check_dataset_structural_validation",
            passed=False,
            message=f"Found {len(errors)} structural validation errors",
            details={"errors": errors[:10], "total_errors": len(errors)},
        )

    total_examples = len(dataset.train) + len(dataset.valid) + len(dataset.test)
    return CheckResult(
        check_name="check_dataset_structural_validation",
        passed=True,
        message=f"All {total_examples} examples passed structural validation",
        details={
            "train_count": len(dataset.train),
            "valid_count": len(dataset.valid),
            "test_count": len(dataset.test),
        },
    )


# Post-training checks (validate adapter output)


def check_training_loss(
    training_output: str, max_final_loss: float = 2.0, min_loss_decrease: float = 0.1
) -> CheckResult:
    """Validate training loss curve.

    Uses parse_training_log() from hyperparam.py to extract loss values,
    checking that loss decreased and stayed within acceptable bounds.

    Args:
        training_output: Raw training command output
        max_final_loss: Maximum acceptable final loss value
        min_loss_decrease: Minimum required decrease from initial to final loss

    Returns:
        CheckResult indicating pass/fail with loss curve details

    Catches:
        - Loss not monitored (Phase 8)
        - Loss not decreasing
        - NaN/Inf in loss values
    """
    logs = parse_training_log(training_output)

    if not logs:
        return CheckResult(
            check_name="check_training_loss",
            passed=False,
            message="No training loss values found in output",
        )

    # Check for NaN/Inf
    for log in logs:
        if not (0 <= log.train_loss < float("inf")):
            return CheckResult(
                check_name="check_training_loss",
                passed=False,
                message=f"Invalid loss value at iteration {log.iteration}: {log.train_loss}",
                details={"iteration": log.iteration, "train_loss": log.train_loss},
            )

    initial_loss = logs[0].train_loss
    final_loss = logs[-1].train_loss
    loss_decrease = initial_loss - final_loss

    warnings = []

    # Check if loss decreased enough
    if loss_decrease < min_loss_decrease:
        return CheckResult(
            check_name="check_training_loss",
            passed=False,
            message=f"Loss decreased by only {loss_decrease:.3f} (minimum {min_loss_decrease})",
            details={
                "initial_loss": initial_loss,
                "final_loss": final_loss,
                "loss_decrease": loss_decrease,
                "iterations": len(logs),
            },
        )

    # Check final loss
    if final_loss > max_final_loss:
        warnings.append(
            f"Final loss {final_loss:.3f} above recommended maximum {max_final_loss}"
        )

    return CheckResult(
        check_name="check_training_loss",
        passed=True,
        message=f"Loss decreased from {initial_loss:.3f} to {final_loss:.3f} over {len(logs)} iterations",
        warnings=tuple(warnings),
        details={
            "initial_loss": initial_loss,
            "final_loss": final_loss,
            "loss_decrease": loss_decrease,
            "iterations": len(logs),
        },
    )


def check_adapter_files(adapter_path: Path) -> CheckResult:
    """Verify adapter directory has required files.

    Checks that training produced a complete adapter with weights
    and configuration files.

    Args:
        adapter_path: Path to adapter directory

    Returns:
        CheckResult indicating pass/fail with file presence details

    Catches:
        - Silent training failures producing incomplete output
    """
    if not adapter_path.exists():
        return CheckResult(
            check_name="check_adapter_files",
            passed=False,
            message=f"Adapter directory does not exist: {adapter_path}",
        )

    required_files = ["adapters.safetensors", "adapter_config.json"]
    missing_files = []

    for filename in required_files:
        if not (adapter_path / filename).exists():
            missing_files.append(filename)

    if missing_files:
        return CheckResult(
            check_name="check_adapter_files",
            passed=False,
            message=f"Missing required adapter files: {', '.join(missing_files)}",
            details={"missing_files": missing_files},
        )

    # Check adapter config is valid JSON
    config_path = adapter_path / "adapter_config.json"
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            if "lora_alpha" not in config or "r" not in config:
                return CheckResult(
                    check_name="check_adapter_files",
                    passed=False,
                    message="adapter_config.json missing required fields (lora_alpha, r)",
                    details={"config_keys": list(config.keys())},
                )
    except json.JSONDecodeError as e:
        return CheckResult(
            check_name="check_adapter_files",
            passed=False,
            message=f"adapter_config.json is not valid JSON: {e}",
        )

    return CheckResult(
        check_name="check_adapter_files",
        passed=True,
        message=f"Adapter directory has all required files: {', '.join(required_files)}",
    )


# Post-fusion checks (validate fused model)


def check_fused_model_config(
    fused_model_path: Path, expected_eos_token_ids: tuple[int, ...] | None = None
) -> CheckResult:
    """Verify fused model configuration.

    Checks that model fusion produced valid config files with correct
    special token IDs.

    Args:
        fused_model_path: Path to fused model directory
        expected_eos_token_ids: Expected EOS token IDs (if None, just checks existence)

    Returns:
        CheckResult indicating pass/fail with config validation details

    Catches:
        - eos_token_id mismatch (Phase 25)
        - Missing config files after fusion
    """
    if not fused_model_path.exists():
        return CheckResult(
            check_name="check_fused_model_config",
            passed=False,
            message=f"Fused model directory does not exist: {fused_model_path}",
        )

    required_files = ["config.json", "tokenizer_config.json"]
    missing_files = []

    for filename in required_files:
        if not (fused_model_path / filename).exists():
            missing_files.append(filename)

    if missing_files:
        return CheckResult(
            check_name="check_fused_model_config",
            passed=False,
            message=f"Missing required config files: {', '.join(missing_files)}",
            details={"missing_files": missing_files},
        )

    # Check config.json for eos_token_id
    config_path = fused_model_path / "config.json"
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            eos_token_id = config.get("eos_token_id")

            if eos_token_id is None:
                return CheckResult(
                    check_name="check_fused_model_config",
                    passed=False,
                    message="config.json missing eos_token_id field",
                )

            # If expected values provided, validate them
            if expected_eos_token_ids is not None:
                # Handle both single ID and list of IDs
                actual_ids = (
                    tuple(eos_token_id)
                    if isinstance(eos_token_id, list)
                    else (eos_token_id,)
                )
                if actual_ids != expected_eos_token_ids:
                    return CheckResult(
                        check_name="check_fused_model_config",
                        passed=False,
                        message=f"eos_token_id mismatch: expected {expected_eos_token_ids}, got {actual_ids}",
                        details={
                            "expected": expected_eos_token_ids,
                            "actual": actual_ids,
                        },
                    )

    except json.JSONDecodeError as e:
        return CheckResult(
            check_name="check_fused_model_config",
            passed=False,
            message=f"config.json is not valid JSON: {e}",
        )

    return CheckResult(
        check_name="check_fused_model_config",
        passed=True,
        message="Fused model config valid with correct eos_token_id",
        details={"eos_token_id": eos_token_id if "eos_token_id" in locals() else None},
    )


# Post-quantization checks (validate quantized model)


def check_quantized_model_config(
    quantized_model_path: Path, expected_bits: int = 5
) -> CheckResult:
    """Verify quantized model configuration.

    Checks that quantization config matches expected bit level and that
    special tokens were preserved through quantization.

    Args:
        quantized_model_path: Path to quantized model directory
        expected_bits: Expected quantization bit level

    Returns:
        CheckResult indicating pass/fail with quantization config details

    Catches:
        - 4-bit destroying LoRA signal (Phases 5-17)
        - eos_token_id not preserved through quantization
    """
    if not quantized_model_path.exists():
        return CheckResult(
            check_name="check_quantized_model_config",
            passed=False,
            message=f"Quantized model directory does not exist: {quantized_model_path}",
        )

    config_path = quantized_model_path / "config.json"
    if not config_path.exists():
        return CheckResult(
            check_name="check_quantized_model_config",
            passed=False,
            message="Missing config.json in quantized model",
        )

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

            # Check quantization bits
            quantization = config.get("quantization")
            if not quantization:
                return CheckResult(
                    check_name="check_quantized_model_config",
                    passed=False,
                    message="config.json missing quantization field",
                )

            bits = quantization.get("bits")
            if bits is None:
                return CheckResult(
                    check_name="check_quantized_model_config",
                    passed=False,
                    message="Quantization config missing 'bits' field",
                )

            warnings = []
            if bits < 5:
                warnings.append(
                    f"Quantization at {bits}-bit is below recommended 5-bit "
                    f"(known to destroy LoRA signal at 4-bit)"
                )

            # Check eos_token_id preserved
            eos_token_id = config.get("eos_token_id")
            if eos_token_id is None:
                warnings.append("eos_token_id missing from quantized model config")

            if bits != expected_bits:
                return CheckResult(
                    check_name="check_quantized_model_config",
                    passed=False,
                    message=f"Quantization at {bits}-bit doesn't match expected {expected_bits}-bit",
                    warnings=tuple(warnings),
                    details={"expected_bits": expected_bits, "actual_bits": bits},
                )

            return CheckResult(
                check_name="check_quantized_model_config",
                passed=True,
                message=f"Quantized model at {bits}-bit with correct configuration",
                warnings=tuple(warnings),
                details={"bits": bits, "eos_token_id": eos_token_id},
            )

    except json.JSONDecodeError as e:
        return CheckResult(
            check_name="check_quantized_model_config",
            passed=False,
            message=f"config.json is not valid JSON: {e}",
        )


def check_quantized_model_smoke_test(
    model_output: str, expected_patterns: tuple[str, ...]
) -> CheckResult:
    """Smoke test quantized model output for tool calling ability.

    Given output from a test prompt, verifies that tool call markers
    are present and raw control tokens are absent.

    Args:
        model_output: Raw output from quantized model test inference
        expected_patterns: Patterns that should appear (e.g., "<tool_call>", "```json")

    Returns:
        CheckResult indicating pass/fail with smoke test details

    Catches:
        - Quantization destroying tool calling ability (Phase 2)
        - Model outputting raw control tokens
    """
    if not model_output or not model_output.strip():
        return CheckResult(
            check_name="check_quantized_model_smoke_test",
            passed=False,
            message="Model output is empty",
        )

    # Check for expected patterns
    missing_patterns = []
    for pattern in expected_patterns:
        if pattern not in model_output:
            missing_patterns.append(pattern)

    # Check for bad patterns (raw control tokens)
    bad_patterns = ["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>"]
    found_bad = [pattern for pattern in bad_patterns if pattern in model_output]

    warnings = []
    if found_bad:
        warnings.append(f"Model outputting raw control tokens: {', '.join(found_bad)}")

    if missing_patterns:
        return CheckResult(
            check_name="check_quantized_model_smoke_test",
            passed=False,
            message=f"Missing expected patterns: {', '.join(missing_patterns)}",
            warnings=tuple(warnings),
            details={
                "missing_patterns": missing_patterns,
                "found_bad_patterns": found_bad,
            },
        )

    return CheckResult(
        check_name="check_quantized_model_smoke_test",
        passed=True,
        message=f"Model output contains all {len(expected_patterns)} expected patterns",
        warnings=tuple(warnings),
        details={"output_length": len(model_output)},
    )


# Runtime checks


def check_eval_parser_matches_training_format(
    sample_assistant_content: str,
) -> CheckResult:
    """Verify eval parser can extract tool calls from training format.

    Tests that the parser used in evaluation can handle the format used
    in training data, catching eval/production divergence.

    Args:
        sample_assistant_content: Sample assistant response from training data

    Returns:
        CheckResult indicating pass/fail with parser compatibility details

    Catches:
        - Eval masking production failures (Meta-pattern #1, Phases 8-20)
        - Parser format mismatches between training and evaluation
    """
    if not sample_assistant_content or not sample_assistant_content.strip():
        return CheckResult(
            check_name="check_eval_parser_matches_training_format",
            passed=False,
            message="Sample content is empty",
        )

    # Try to parse tool calls using production parser
    try:
        remaining_text, calls = parse_tool_calls(sample_assistant_content)

        # If sample contains tool call markers but parser found nothing, that's a failure
        has_markers = (
            "<tool_call>" in sample_assistant_content
            or "```json" in sample_assistant_content
            or "<function=" in sample_assistant_content
        )

        if has_markers and not calls:
            return CheckResult(
                check_name="check_eval_parser_matches_training_format",
                passed=False,
                message="Parser failed to extract tool calls from training format",
                details={
                    "has_markers": has_markers,
                    "calls_found": len(calls),
                    "sample_length": len(sample_assistant_content),
                },
            )

        return CheckResult(
            check_name="check_eval_parser_matches_training_format",
            passed=True,
            message=f"Parser successfully extracted {len(calls)} tool calls from sample",
            details={"calls_found": len(calls), "has_markers": has_markers},
        )

    except Exception as e:
        return CheckResult(
            check_name="check_eval_parser_matches_training_format",
            passed=False,
            message=f"Parser raised exception: {e}",
        )


# Convenience runners


def run_pre_training_checks(
    data_directory: Path,
    expected_format: str = "messages",
    max_tool_pct: float = 0.80,
    min_tool_pct: float = 0.10,
    expected_patterns: tuple[str, ...] | None = None,
    expected_system_prompt: str | None = None,
) -> tuple[CheckResult, ...]:
    """Run all pre-training validation checks.

    Args:
        data_directory: Directory containing training JSONL files
        expected_format: Expected top-level key ("messages" or "text")
        max_tool_pct: Maximum allowed percentage of tool-calling examples
        min_tool_pct: Minimum required percentage of tool-calling examples
        expected_patterns: Patterns that should appear in data (optional)
        expected_system_prompt: Expected system prompt (optional)

    Returns:
        Tuple of CheckResults from all pre-training checks
    """
    results = [
        check_format_consistency(data_directory, expected_format),
        check_training_data_distribution(data_directory, max_tool_pct, min_tool_pct),
        check_training_data_content(data_directory),
        check_system_prompt_consistency(data_directory, expected_system_prompt),
    ]

    if expected_patterns:
        results.append(check_training_data_coverage(data_directory, expected_patterns))

    return tuple(results)


def run_post_training_checks(
    training_output: str, adapter_path: Path, max_final_loss: float = 2.0
) -> tuple[CheckResult, ...]:
    """Run all post-training validation checks.

    Args:
        training_output: Raw training command output
        adapter_path: Path to trained adapter directory
        max_final_loss: Maximum acceptable final loss value

    Returns:
        Tuple of CheckResults from all post-training checks
    """
    return (
        check_training_loss(training_output, max_final_loss),
        check_adapter_files(adapter_path),
    )


def run_post_fusion_checks(
    fused_model_path: Path, expected_eos_token_ids: tuple[int, ...] | None = None
) -> tuple[CheckResult, ...]:
    """Run all post-fusion validation checks.

    Args:
        fused_model_path: Path to fused model directory
        expected_eos_token_ids: Expected EOS token IDs (optional)

    Returns:
        Tuple of CheckResults from all post-fusion checks
    """
    return (check_fused_model_config(fused_model_path, expected_eos_token_ids),)


def run_post_quantization_checks(
    quantized_model_path: Path,
    expected_bits: int = 5,
    model_output: str | None = None,
    expected_patterns: tuple[str, ...] | None = None,
) -> tuple[CheckResult, ...]:
    """Run all post-quantization validation checks.

    Args:
        quantized_model_path: Path to quantized model directory
        expected_bits: Expected quantization bit level
        model_output: Optional model output for smoke test
        expected_patterns: Optional patterns for smoke test

    Returns:
        Tuple of CheckResults from all post-quantization checks
    """
    results = [check_quantized_model_config(quantized_model_path, expected_bits)]

    if model_output and expected_patterns:
        results.append(check_quantized_model_smoke_test(model_output, expected_patterns))

    return tuple(results)


def summarize_checks(results: tuple[CheckResult, ...]) -> str:
    """Create human-readable summary of check results.

    Args:
        results: Tuple of CheckResults to summarize

    Returns:
        Formatted string summarizing all checks
    """
    if not results:
        return "No checks run"

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    lines = [
        f"Pipeline Validation: {passed}/{len(results)} checks passed",
        "",
    ]

    # List failed checks first
    if failed > 0:
        lines.append("❌ Failed Checks:")
        for result in results:
            if not result.passed:
                lines.append(f"  - {result.check_name}: {result.message}")
        lines.append("")

    # Then warnings
    warnings_found = [r for r in results if r.warnings]
    if warnings_found:
        lines.append("⚠️  Warnings:")
        for result in warnings_found:
            for warning in result.warnings:
                lines.append(f"  - {result.check_name}: {warning}")
        lines.append("")

    # Finally passed checks
    if passed > 0:
        lines.append("✅ Passed Checks:")
        for result in results:
            if result.passed:
                lines.append(f"  - {result.check_name}: {result.message}")

    return "\n".join(lines)

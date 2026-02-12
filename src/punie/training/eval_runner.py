"""Evaluation runner for testing models against prompt suites."""

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_pydantic_agent, create_server_model
from punie.local import LocalClient
from punie.training.eval_prompts import EvalSuite
from punie.training.eval_results import EvalReport, EvalResult
from punie.training.eval_scoring import score_prompt
from punie.training.server import ServerProcess
from punie.training.server_config import ServerConfig
from punie.training.tool_call_parser import parse_tool_calls


@dataclass(frozen=True)
class EvalRunConfig:
    """Configuration for an evaluation run."""

    server_config: ServerConfig  # Server configuration (model, port, etc.)
    suite: EvalSuite  # Evaluation suite to run
    workspace: Path  # Workspace for file operations
    manage_server: bool = True  # Whether to start/stop server automatically


async def run_evaluation(config: EvalRunConfig) -> EvalReport:
    """Run evaluation suite against a model.

    Orchestrates the full evaluation loop:
    1. Optionally start server via ServerProcess
    2. Create agent via create_server_model()
    3. Run each prompt, extract tool calls from messages, score
    4. Stop server
    5. Return frozen EvalReport

    Args:
        config: Evaluation run configuration

    Returns:
        EvalReport with all results

    Raises:
        RuntimeError: If server management fails
        Exception: If evaluation encounters errors
    """
    # Start server if requested
    server: ServerProcess | None = None
    if config.manage_server:
        server = ServerProcess(config=config.server_config)
        await server.start()

    try:
        # Create agent with server model
        model = create_server_model(config.server_config)
        agent_config = AgentConfig(temperature=0.0)  # Deterministic for evaluation
        agent = create_pydantic_agent(model=model, config=agent_config)

        # Create local client for file operations
        client = LocalClient(workspace=config.workspace)

        # Run each prompt and collect results
        results: list[EvalResult] = []
        for prompt in config.suite.prompts:
            start_time = time.perf_counter()

            # Track tool calls
            tracker = ToolCallTracker()

            # Create deps
            deps = ACPDeps(
                client_conn=client,
                session_id=f"eval-{prompt.id}",
                tracker=tracker,
            )

            try:
                # Run agent with prompt
                result = await agent.run(prompt.prompt_text, deps=deps)

                # Extract tool calls from both structured parts AND raw text
                tool_calls_list = []
                # Check structured parts first (for cloud models that return proper tool_calls)
                if result.all_messages():
                    for msg in result.all_messages():
                        if hasattr(msg, "parts"):
                            for part in msg.parts:
                                if hasattr(part, "tool_name"):
                                    tool_calls_list.append(part.tool_name)
                # If no structured tool calls found, parse from raw text (for mlx_lm.server)
                if not tool_calls_list:
                    _, parsed_calls = parse_tool_calls(result.output)
                    tool_calls_list = [call["name"] for call in parsed_calls if "name" in call]
                tool_calls_made: tuple[str, ...] = tuple(tool_calls_list)

                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Score the result
                score = score_prompt(
                    prompt=prompt,
                    response=result.output,
                    tool_calls=tool_calls_made,
                )

                # Record successful result
                results.append(
                    EvalResult(
                        prompt_id=prompt.id,
                        response_text=result.output,
                        tool_calls_made=tool_calls_made,
                        duration_ms=duration_ms,
                        score=score,
                        success=True,
                    )
                )

            except Exception as e:
                # Record failed result
                duration_ms = (time.perf_counter() - start_time) * 1000
                results.append(
                    EvalResult(
                        prompt_id=prompt.id,
                        response_text=f"Error: {e}",
                        tool_calls_made=(),
                        duration_ms=duration_ms,
                        score=0.0,
                        success=False,
                    )
                )

        # Build and return report
        return EvalReport(
            model_name=config.server_config.model_path,
            adapter_path=config.server_config.adapter_path,
            suite_name=config.suite.name,
            timestamp=datetime.now(),
            results=tuple(results),
        )

    finally:
        # Stop server if we started it
        if server:
            await server.stop()

"""Inference parameter tuning infrastructure.

Unlike hyperparameter tuning (which changes training), inference tuning
changes how the model generates responses at serving time.
"""

from dataclasses import dataclass

from punie.training.eval_results import EvalReport
from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.server_config import ServerConfig


@dataclass(frozen=True)
class InferenceGrid:
    """Grid of inference parameters to search.

    These parameters affect how the model generates text during inference,
    not during training.
    """

    temperatures: tuple[float, ...] = (0.0, 0.1, 0.3, 0.7)
    top_ps: tuple[float, ...] = (0.9, 0.95, 1.0)

    @property
    def total_combinations(self) -> int:
        """Total number of parameter combinations."""
        return len(self.temperatures) * len(self.top_ps)


@dataclass(frozen=True)
class InferenceResult:
    """Result from a single inference parameter configuration.

    Contains the server config used and the evaluation report.
    """

    server_config: ServerConfig
    eval_report: EvalReport
    temperature: float
    top_p: float


async def run_inference_search(
    grid: InferenceGrid,
    base_eval_config: EvalRunConfig,
) -> tuple[InferenceResult, ...]:
    """Run grid search over inference parameters.

    For each combination in the grid:
    1. Start server with those parameters
    2. Evaluate using base_eval_config's suite
    3. Record the results

    Args:
        grid: Inference parameter grid to search
        base_eval_config: Base evaluation configuration (server_config will be modified)

    Returns:
        Tuple of InferenceResult sorted by score (best first)
    """
    results = []
    combination_num = 0

    for temp in grid.temperatures:
        for top_p in grid.top_ps:
            combination_num += 1

            # Create server config with inference parameters
            server_config = ServerConfig(
                model_path=base_eval_config.server_config.model_path,
                port=base_eval_config.server_config.port,
                host=base_eval_config.server_config.host,
                adapter_path=base_eval_config.server_config.adapter_path,
                temp=temp,
                top_p=top_p,
            )

            # Create eval config with new server config
            eval_config = EvalRunConfig(
                server_config=server_config,
                suite=base_eval_config.suite,
                workspace=base_eval_config.workspace,
                manage_server=base_eval_config.manage_server,
            )

            print(f"\n[{combination_num}/{grid.total_combinations}] Testing inference params:")
            print(f"  Temp: {temp}, Top-p: {top_p}")

            try:
                eval_report = await run_evaluation(eval_config)
                print(f"  Score: {eval_report.overall_score:.1%}")

                results.append(
                    InferenceResult(
                        server_config=server_config,
                        eval_report=eval_report,
                        temperature=temp,
                        top_p=top_p,
                    )
                )

            except Exception as e:
                print(f"  ❌ Failed: {e}")
                continue

    # Sort by score (best first)
    sorted_results = sorted(results, key=lambda r: r.eval_report.overall_score, reverse=True)
    return tuple(sorted_results)

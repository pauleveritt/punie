"""Performance data collection for tool timing."""

import time
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ToolTiming:
    """Frozen snapshot of a single tool call's timing."""

    tool_name: str
    started_at: float  # monotonic time
    ended_at: float
    duration_ms: float
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class PromptTiming:
    """Frozen snapshot of entire prompt execution timing."""

    started_at: float
    ended_at: float
    duration_ms: float
    model_name: str
    backend: Literal["local", "ide"]
    tool_timings: tuple[ToolTiming, ...]


class PerformanceCollector:
    """Mutable collector for recording tool and prompt timing during execution."""

    def __init__(self) -> None:
        self._tool_starts: dict[str, float] = {}
        self._tool_timings: list[ToolTiming] = []
        self._prompt_start: float | None = None
        self._prompt_end: float | None = None
        self._prompt_info: tuple[str, Literal["local", "ide"]] | None = (
            None  # (model_name, backend)
        )

    def start_tool(self, name: str) -> None:
        """Record the start time of a tool call."""
        self._tool_starts[name] = time.monotonic()

    def end_tool(
        self, name: str, success: bool = True, error: str | None = None
    ) -> None:
        """Record the end time of a tool call and calculate duration."""
        end_time = time.monotonic()
        start_time = self._tool_starts.pop(name, end_time)
        duration_ms = (end_time - start_time) * 1000

        timing = ToolTiming(
            tool_name=name,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )
        self._tool_timings.append(timing)

    def start_prompt(self, model_name: str, backend: Literal["local", "ide"]) -> None:
        """Record the start time of prompt execution."""
        self._prompt_start = time.monotonic()
        self._prompt_info = (model_name, backend)

    def end_prompt(self) -> None:
        """Record the end time of prompt execution."""
        self._prompt_end = time.monotonic()

    def report(self) -> PromptTiming:
        """Generate frozen snapshot of all timing data."""
        if (
            self._prompt_start is None
            or self._prompt_end is None
            or self._prompt_info is None
        ):
            msg = "Cannot generate report: prompt timing not started or not ended"
            raise ValueError(msg)

        model_name, backend = self._prompt_info
        duration_ms = (self._prompt_end - self._prompt_start) * 1000

        return PromptTiming(
            started_at=self._prompt_start,
            ended_at=self._prompt_end,
            duration_ms=duration_ms,
            model_name=model_name,
            backend=backend,
            tool_timings=tuple(self._tool_timings),
        )

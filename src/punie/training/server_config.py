"""Configuration for mlx_lm.server instances."""

from dataclasses import dataclass

# Default stop sequences for Qwen models to prevent garbage token generation
QWEN_STOP_SEQUENCES = ("<|im_end|>", "<|endoftext|>")


@dataclass(frozen=True)
class ServerConfig:
    """Configuration for launching mlx_lm.server.

    All code launches mlx-lm as a subprocess — no import-time dependency.
    Tests work without mlx-lm installed.
    """

    model_path: str  # e.g., "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
    port: int = 8080
    host: str = "127.0.0.1"
    adapter_path: str | None = None  # LoRA adapter directory (None = base model)
    temp: float | None = None  # Default sampling temperature (--temp)
    top_p: float | None = None  # Nucleus sampling parameter (--top-p)
    max_tokens: int | None = None  # Maximum generation length (--max-tokens)
    chat_template_args: str | None = None  # Chat template args JSON (--chat-template-args)
    stop_sequences: tuple[str, ...] | None = None  # Stop tokens (per-request, not CLI flag)
    draft_model: str | None = None  # Draft model for speculative decoding (--draft-model)
    num_draft_tokens: int | None = None  # Tokens per draft step (--num-draft-tokens)

    @property
    def base_url(self) -> str:
        """Return the OpenAI-compatible API base URL."""
        return f"http://{self.host}:{self.port}/v1"

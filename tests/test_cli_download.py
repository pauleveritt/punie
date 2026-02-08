"""Tests for punie download-model CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from punie.cli import app

runner = CliRunner()


def test_download_model_list_flag():
    """Test that --list shows recommended models."""
    result = runner.invoke(app, ["download-model", "--list"])

    assert result.exit_code == 0
    assert "Available models" in result.output
    assert "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit" in result.output
    assert "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit" in result.output
    assert "mlx-community/Qwen2.5-Coder-14B-Instruct-4bit" in result.output
    assert "~4GB" in result.output
    assert "~2GB" in result.output
    assert "~8GB" in result.output


def test_download_model_help():
    """Test that help message shows command usage."""
    result = runner.invoke(app, ["download-model", "--help"])

    assert result.exit_code == 0
    assert "download-model" in result.output
    assert "HuggingFace model name" in result.output
    assert "--models-dir" in result.output


def test_download_model_missing_mlx_lm():
    """Test error when mlx-lm not installed (ImportError during download)."""
    # Patch the actual import location in the download_model function
    with patch("punie.cli.Path.mkdir"):
        with patch.object(
            Path,
            "expanduser",
            return_value=Path("/fake/.punie/models"),
        ):
            # Trigger ImportError when trying to import snapshot_download in download_model
            with patch.dict("sys.modules", {"huggingface_hub": None}):
                result = runner.invoke(app, ["download-model"])

    assert result.exit_code == 1
    assert "Local model support requires mlx-lm" in result.output
    assert "uv pip install 'punie[local]'" in result.output


def test_download_model_default_name(tmp_path: Path):
    """Test download with default model name."""
    # Mock snapshot_download within the CLI module's namespace
    mock_snapshot = Mock()

    with patch.dict(
        "sys.modules", {"huggingface_hub": Mock(snapshot_download=mock_snapshot)}
    ):
        with patch.object(
            Path,
            "expanduser",
            return_value=tmp_path,
        ):
            # Re-import to pick up mocked module
            import importlib
            import punie.cli

            importlib.reload(punie.cli)

            result = runner.invoke(app, ["download-model"])

    assert result.exit_code == 0
    assert "Downloading mlx-community/Qwen2.5-Coder-7B-Instruct-4bit" in result.output
    assert "Model downloaded successfully" in result.output


def test_download_model_custom_name(tmp_path: Path):
    """Test download with custom model name."""
    custom_model = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
    mock_snapshot = Mock()

    with patch.dict(
        "sys.modules", {"huggingface_hub": Mock(snapshot_download=mock_snapshot)}
    ):
        with patch.object(
            Path,
            "expanduser",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["download-model", custom_model])

    assert result.exit_code == 0
    assert f"Downloading {custom_model}" in result.output


def test_download_model_custom_dir(tmp_path: Path):
    """Test download with custom models directory."""
    custom_dir = tmp_path / "custom-models"
    mock_snapshot = Mock()

    with patch.dict(
        "sys.modules", {"huggingface_hub": Mock(snapshot_download=mock_snapshot)}
    ):
        result = runner.invoke(app, ["download-model", "--models-dir", str(custom_dir)])

    assert result.exit_code == 0


def test_download_model_network_error(tmp_path: Path):
    """Test error handling for network failures."""
    mock_snapshot = Mock(side_effect=Exception("Network error: connection failed"))

    with patch.dict(
        "sys.modules", {"huggingface_hub": Mock(snapshot_download=mock_snapshot)}
    ):
        with patch.object(
            Path,
            "expanduser",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["download-model"])

    assert result.exit_code == 1
    assert "Error downloading model" in result.output
    assert "Network error" in result.output


def test_download_model_disk_space_error(tmp_path: Path):
    """Test error handling for disk space issues."""
    mock_snapshot = Mock(side_effect=OSError("No space left on device"))

    with patch.dict(
        "sys.modules", {"huggingface_hub": Mock(snapshot_download=mock_snapshot)}
    ):
        with patch.object(
            Path,
            "expanduser",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["download-model"])

    assert result.exit_code == 1
    assert "Error downloading model" in result.output


def test_mlx_model_not_downloaded_error():
    """Test MLXModel raises clear error when model not downloaded."""
    from punie.models.mlx import MLXModel

    # Create a mock module with a load function that raises FileNotFoundError
    mock_mlx_lm = Mock()
    mock_load = Mock(side_effect=FileNotFoundError("Model not found"))
    mock_mlx_lm.utils = Mock(load=mock_load)

    with patch.dict(
        "sys.modules", {"mlx_lm": mock_mlx_lm, "mlx_lm.utils": mock_mlx_lm.utils}
    ):
        with pytest.raises(RuntimeError) as exc_info:
            MLXModel.from_pretrained("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")

        error_msg = str(exc_info.value)
        assert "not downloaded" in error_msg
        assert "punie download-model" in error_msg
        assert "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit" in error_msg


def test_cli_main_model_not_downloaded_shows_error():
    """Test CLI main command shows clear error for missing model."""
    with patch("punie.cli.asyncio.run") as mock_run:
        mock_run.side_effect = RuntimeError(
            "Model 'mlx-community/Qwen2.5-Coder-7B-Instruct-4bit' is not downloaded.\n"
            "Download it with: punie download-model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        )

        result = runner.invoke(app, ["--model", "local"])

        assert result.exit_code == 1
        assert "not downloaded" in result.output


def test_cli_serve_model_not_downloaded_shows_error():
    """Test CLI serve command shows clear error for missing model."""
    with patch("punie.cli.asyncio.run") as mock_run:
        mock_run.side_effect = RuntimeError(
            "Model 'mlx-community/Qwen2.5-Coder-7B-Instruct-4bit' is not downloaded.\n"
            "Download it with: punie download-model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        )

        result = runner.invoke(app, ["serve", "--model", "local"])

        assert result.exit_code == 1
        assert "not downloaded" in result.output

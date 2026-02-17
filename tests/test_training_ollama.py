"""Tests for ollama process lifecycle."""

import pytest

from punie.training.ollama import OllamaProcess


def test_ollama_process_base_url():
    """OllamaProcess constructs correct base URL."""
    process = OllamaProcess(model="devstral", port=11434, host="127.0.0.1")

    assert process.base_url == "http://127.0.0.1:11434"


def test_ollama_process_custom_port():
    """OllamaProcess uses custom port."""
    process = OllamaProcess(model="qwen3:30b-a3b", port=8888)

    assert process.base_url == "http://127.0.0.1:8888"


def test_ollama_process_custom_host():
    """OllamaProcess uses custom host."""
    process = OllamaProcess(model="devstral", host="0.0.0.0", port=11434)

    assert process.base_url == "http://0.0.0.0:11434"


def test_ollama_process_is_running_initially_false():
    """OllamaProcess.is_running is False when not started."""
    process = OllamaProcess(model="devstral")

    assert process.is_running is False


def test_ollama_process_default_port():
    """OllamaProcess defaults to port 11434."""
    process = OllamaProcess(model="devstral")

    assert process.port == 11434


def test_ollama_process_default_host():
    """OllamaProcess defaults to host 127.0.0.1."""
    process = OllamaProcess(model="devstral")

    assert process.host == "127.0.0.1"


@pytest.mark.asyncio
async def test_ollama_health_check_failure():
    """OllamaProcess.health_check returns False when server not running."""
    process = OllamaProcess(model="devstral", port=65534)  # Unlikely to be in use

    result = await process.health_check()

    assert result is False


def test_ollama_process_model_stored():
    """OllamaProcess stores model name."""
    process = OllamaProcess(model="qwen3:30b-a3b")

    assert process.model == "qwen3:30b-a3b"

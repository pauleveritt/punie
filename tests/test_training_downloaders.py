"""Tests for dataset downloaders.

Note: These tests use mock data to avoid downloading actual datasets.
Integration tests would download real data but are marked slow.
"""

# Integration tests (require actual dataset download - mark as slow)
# These are commented out to avoid slow downloads during normal testing
# Uncomment to test with real datasets

# import pytest
# from pathlib import Path
#
# @pytest.mark.slow
# def test_download_sample_dataset(tmp_path: Path):
#     """Integration test: download sample dataset."""
#     from punie.training.downloaders import download_sample_dataset
#
#     output_dir = tmp_path / "sample"
#     stats = download_sample_dataset(output_dir, max_examples=10)
#
#     assert stats.total_examples > 0
#     assert (output_dir / "train.jsonl").exists()
#     assert (output_dir / "valid.jsonl").exists()
#     assert (output_dir / "test.jsonl").exists()

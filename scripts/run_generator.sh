#!/bin/bash
# Wrapper to run training data generator with proper output handling

set -e

echo "Starting training data generation..."
echo "This will take ~70 minutes for 100 examples"
echo ""

# Set environment variables for OpenAI-compatible API
export OPENAI_API_KEY='dummy'
export OPENAI_BASE_URL='http://127.0.0.1:8080/v1'

# Run with unbuffered output
uv run python -u scripts/generate_training_data.py

echo ""
echo "Generation complete! Check data/training_examples_1k.jsonl"

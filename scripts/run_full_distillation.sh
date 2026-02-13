#!/bin/bash
# Complete knowledge distillation pipeline: Data → Training → Evaluation
#
# Runs all three phases overnight:
# 1. Complete data generation (~45 min)
# 2. LoRA fine-tuning (~6-8 hours)
# 3. Evaluation (automated with 7B server)
#
# Total time: ~7-9 hours
#
# Usage:
#   ./run_full_distillation.sh          # Interactive mode
#   ./run_full_distillation.sh --yes    # Unattended overnight mode

set -e  # Exit on error

# Parse arguments
UNATTENDED=false
if [ "$1" = "--yes" ] || [ "$1" = "-y" ]; then
    UNATTENDED=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "========================================================================"
echo "FULL KNOWLEDGE DISTILLATION PIPELINE"
echo "========================================================================"
echo ""
echo "This will run overnight (~7-9 hours total):"
echo "  Phase 1: Complete training data generation (~45 min)"
echo "  Phase 2: LoRA fine-tuning (~6-8 hours)"
echo "  Phase 3: Evaluation with automated 7B server"
echo ""
if [ "$UNATTENDED" = true ]; then
    echo "MODE: Unattended (--yes flag)"
else
    echo "MODE: Interactive"
fi
echo "========================================================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check 30B server is running
if ! curl -s http://127.0.0.1:8080/v1/models > /dev/null 2>&1; then
    echo "❌ Error: 30B server not running on port 8080"
    echo "   Start it first with: mlx_lm.server --model <model> --port 8080"
    exit 1
fi
echo "✅ 30B server running on port 8080"

# Check current data progress
if [ -f "data/training_examples_1k.jsonl" ]; then
    CURRENT_COUNT=$(wc -l < "data/training_examples_1k.jsonl")
    echo "✅ Current training data: $CURRENT_COUNT examples"
else
    CURRENT_COUNT=0
    echo "⚠️  No existing training data"
fi

echo ""
if [ "$UNATTENDED" = false ]; then
    read -p "Ready to start overnight distillation? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

# Create log directory
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "========================================================================"
echo "PHASE 1: Training Data Generation"
echo "========================================================================"
echo ""
echo "Target: 100 examples"
echo "Estimated time: 30-45 minutes"
echo ""

# Run data generation
LOG_FILE="$LOG_DIR/data_generation_$TIMESTAMP.log"
echo "Running data generation..."
echo "Log: $LOG_FILE"
echo ""

if uv run python scripts/generate_training_data.py > "$LOG_FILE" 2>&1; then
    FINAL_COUNT=$(wc -l < "data/training_examples_1k.jsonl" 2>/dev/null || echo "0")
    echo ""
    echo "✅ Data generation complete: $FINAL_COUNT examples"

    if [ "$FINAL_COUNT" -lt 80 ]; then
        echo ""
        echo "⚠️  Warning: Only $FINAL_COUNT examples (target: 100+)"
        if [ "$UNATTENDED" = false ]; then
            read -p "Continue with training anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Stopping pipeline. Check log: $LOG_FILE"
                exit 1
            fi
        else
            echo "Continuing anyway (unattended mode)"
        fi
    fi
else
    echo ""
    echo "❌ Data generation failed. Check log: $LOG_FILE"
    exit 1
fi

echo ""
echo "========================================================================"
echo "PHASE 2: LoRA Fine-Tuning"
echo "========================================================================"
echo ""

LOG_FILE="$LOG_DIR/training_$TIMESTAMP.log"
echo "Starting training (~6-8 hours)..."
echo "Log: $LOG_FILE"
echo ""

# Training configuration
MODEL="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
TRAINING_DATA="data/training_examples_1k.jsonl"
OUTPUT_DIR="models/qwen25-7b-distilled"
BATCH_SIZE=2
LEARNING_RATE=1e-4
EPOCHS=3

EXAMPLE_COUNT=$(wc -l < "$TRAINING_DATA")
TOTAL_ITERATIONS=$((EXAMPLE_COUNT * EPOCHS / BATCH_SIZE))

echo "Configuration:"
echo "  Model: $MODEL"
echo "  Examples: $EXAMPLE_COUNT"
echo "  Batch size: $BATCH_SIZE"
echo "  Epochs: $EPOCHS"
echo "  Iterations: $TOTAL_ITERATIONS"
echo "  Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

if uv run python -m mlx_lm.lora \
    --model "$MODEL" \
    --train \
    --data "$TRAINING_DATA" \
    --iters "$TOTAL_ITERATIONS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --num-layers 16 \
    --adapter-path "$OUTPUT_DIR/adapters" \
    --save-every 100 \
    --val-batches 5 \
    --test > "$LOG_FILE" 2>&1; then

    echo ""
    echo "✅ Training complete!"
    echo "   Adapters saved to: $OUTPUT_DIR/adapters"
else
    echo ""
    echo "❌ Training failed. Check log: $LOG_FILE"
    exit 1
fi

echo ""
echo "========================================================================"
echo "PHASE 3: Evaluation"
echo "========================================================================"
echo ""

# Start 7B server with LoRA adapter
echo "Starting 7B server with LoRA adapter on port 8081..."
SERVER_LOG="$LOG_DIR/server_7b_$TIMESTAMP.log"

uv run python -m mlx_lm.server \
    --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
    --adapter-path models/qwen25-7b-distilled/adapters \
    --port 8081 > "$SERVER_LOG" 2>&1 &

SERVER_PID=$!
echo "Server started (PID: $SERVER_PID)"
echo "Server log: $SERVER_LOG"

# Wait for server to be ready
echo "Waiting for server to be ready (30s)..."
sleep 30

# Check if server is responding
if curl -s http://127.0.0.1:8081/v1/models > /dev/null 2>&1; then
    echo "✅ 7B server ready!"
    echo ""
    echo "Running evaluation..."

    EVAL_LOG="$LOG_DIR/evaluation_$TIMESTAMP.log"
    if uv run python scripts/evaluate_distilled_model.py > "$EVAL_LOG" 2>&1; then
        echo ""
        echo "✅ Evaluation complete!"
        echo "   Results: evaluation_results.json"
        echo "   Log: $EVAL_LOG"

        # Show summary from log
        echo ""
        echo "=== EVALUATION SUMMARY ==="
        grep -A 20 "VERDICT" "$EVAL_LOG" || echo "Check full log for results"
    else
        echo ""
        echo "❌ Evaluation failed. Check log: $EVAL_LOG"
    fi

    # Clean up: kill the 7B server
    echo ""
    echo "Stopping 7B server..."
    kill $SERVER_PID 2>/dev/null || true
    echo "7B server stopped"
else
    echo "❌ 7B server failed to start. Check log: $SERVER_LOG"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "========================================================================"
echo "KNOWLEDGE DISTILLATION PIPELINE COMPLETE! 🎉"
echo "========================================================================"
echo ""
echo "All logs saved to: $LOG_DIR/"
echo "Results: evaluation_results.json"
echo ""

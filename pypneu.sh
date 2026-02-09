#!/bin/bash

# Usage: ./pypneu.sh path/to/file.pneu
FILE=$1

if [ -z "$FILE" ]; then
    echo "❌ Error: Please provide a .pneu file."
    echo "Usage: ./pypneu.sh examples/my_net.pneu"
    exit 1
fi

# Ensure Python looks into the src directory for the pypneu package
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Ensure necessary directories exist
mkdir -p outputs

FILENAME=$(basename -- "$FILE")
BASENAME="${FILENAME%.*}"

echo "🚀 Starting Pypneu Toolchain for $FILENAME..."
echo "Timestamp: $(date)"

# 1. Run Batch Simulation (Statistical Analysis & State Tracing)
echo "------------------------------------------"
echo "🧪 Running Batch Simulation (100 runs)..."
# We now generate both the Audit CSV and the JSON State-Transition Trace
python -m pypneu.cli "$FILE" batch -n 100 --steps 50 \
    --csv "outputs/${BASENAME}_audit.csv" \
    --json "outputs/${BASENAME}_traces.json"

if [ $? -ne 0 ]; then
    echo "❌ Batch simulation failed. Check your simulator.py or cli.py logic."
    exit 1
fi

# 2. Export Static High-Res Image (Initial State)
echo "------------------------------------------"
echo "🎨 Exporting Static Visualization..."
python -m pypneu.cli "$FILE" export --format png -o "outputs/${BASENAME}_static.png"

# 3. Generate Animation GIF (Visualizing the Token Game)
echo "------------------------------------------"
echo "🎬 Rendering Animation..."
python -m pypneu.cli "$FILE" animate --steps 15 -o "outputs/${BASENAME}_anim.gif"

# 4. Generate Text Trace for Debugging
echo "------------------------------------------"
echo "📝 Logging Single Stochastic Trace (CLI output)..."
python -m pypneu.cli "$FILE" simulate --steps 20 > "outputs/${BASENAME}_trace_log.txt"

echo "------------------------------------------"
echo "✅ Workflow complete!"
echo "📄 State JSON: outputs/${BASENAME}_traces.json"
echo "📈 Audit CSV: outputs/${BASENAME}_audit.csv"
echo "🎨 Static PNG: outputs/${BASENAME}_static.png"
echo "🎬 Animation: outputs/${BASENAME}_anim.gif"
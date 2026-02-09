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
mkdir -p logs output reports

FILENAME=$(basename -- "$FILE")
BASENAME="${FILENAME%.*}"

echo "🚀 Starting Pypneu Toolchain for $FILENAME..."

# 1. Run Batch Simulation (Statistical Analysis)
echo "------------------------------------------"
echo "🧪 Running Batch Simulation (100 runs)..."
python -m pypneu.cli "$FILE" batch -n 100 --steps 50 \
    --csv "logs/${BASENAME}_audit.csv" \
    --json "reports/${BASENAME}_summary.json"

if [ $? -ne 0 ]; then
    echo "❌ Batch simulation failed. Check your imports or run 'pip install -e .'"
    exit 1
fi

# 2. Export Static High-Res Image (Initial State)
echo "------------------------------------------"
echo "🎨 Exporting Static Visualization..."
python -m pypneu.cli "$FILE" export --format png -o "output/${BASENAME}_static.png"

# 3. Generate Animation GIF (Visualizing the Token Game)
echo "------------------------------------------"
echo "🎬 Rendering Animation..."
python -m pypneu.cli "$FILE" animate --steps 15 -o "output/${BASENAME}_anim.gif"

# 4. Generate Text Trace for Debugging
echo "------------------------------------------"
echo "📝 Logging Single Stochastic Trace..."
python -m pypneu.cli "$FILE" simulate --steps 20 > "logs/${BASENAME}_trace.txt"

echo "------------------------------------------"
echo "✅ Workflow complete!"
echo "📊 Summary: reports/${BASENAME}_summary.json"
echo "🎨 Static PNG: output/${BASENAME}_static.png"
echo "🎬 Animation: output/${BASENAME}_anim.gif"
echo "📈 Audit CSV: logs/${BASENAME}_audit.csv"
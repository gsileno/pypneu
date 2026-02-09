import argparse
import sys
import os
import json
import imageio
import numpy as np
from PIL import Image
from io import BytesIO

import pypneu
from pypneu.executor import StochasticPetriNetExecution
from pypneu.simulator import BatchSimulator
from pypneu.exporter import to_json, to_pnml, to_dot
from pypneu.viewer import PetriNetViewer


def generate_gif(net_data, steps, output_path):
    """Fires transitions and compiles frames into a GIF using PetriNetViewer."""
    # net_data is the dict returned by pypneu.compile_file
    executor = StochasticPetriNetExecution(**net_data)
    frames = []

    print(f"🎬 Generating animation ({steps} steps)...")

    for i in range(steps + 1):
        # Use PetriNetViewer to generate the image frame
        viewer = PetriNetViewer(executor.pn)
        png_data = viewer.to_pydot_graph().create_png()

        img = Image.open(BytesIO(png_data))
        frames.append(np.array(img))

        if i < steps:
            if not executor.step():
                print(f"⏹️ Simulation ended early at step {i} (Deadlock).")
                break

    imageio.mimsave(output_path, frames, fps=2, loop=0)
    print(f"✅ Animation saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(prog="pypneu", description="Pypneu: Petri Net Toolchain")
    parser.add_argument("file", help="Path to the .pneu source file")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

    # --- Batch Command ---
    batch_p = subparsers.add_parser("batch", help="Run stochastic analysis")
    batch_p.add_argument("-n", "--runs", type=int, default=100, help="Number of runs")
    batch_p.add_argument("--steps", type=int, default=50, help="Max steps per run")
    batch_p.add_argument("--csv", default="event_log.csv", help="CSV output path")
    batch_p.add_argument("--json", help="Summary JSON report path")

    # --- Simulate Command ---
    sim_p = subparsers.add_parser("simulate", help="Run a single stochastic trace")
    sim_p.add_argument("--steps", type=int, default=20, help="Max steps")

    # --- Export Command ---
    exp_p = subparsers.add_parser("export", help="Export net to various formats")
    exp_p.add_argument("--format", choices=["json", "pnml", "dot", "png"], required=True)
    exp_p.add_argument("-o", "--output", required=True, help="Output filename")

    # --- Animate Command ---
    anim_p = subparsers.add_parser("animate", help="Generate a GIF animation")
    anim_p.add_argument("--steps", type=int, default=15, help="Steps to animate")
    anim_p.add_argument("-o", "--output", default="simulation.gif", help="Output filename")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ Error: File '{args.file}' not found.")
        sys.exit(1)

    try:
        net_data = pypneu.compile_file(args.file)
        # compile_file returns a dict: {'places': [...], 'transitions': [...], 'arcs': [...]}
    except Exception as e:
        print(f"❌ Compilation Error: {e}")
        sys.exit(1)

    if args.command == "batch":
        simulator = BatchSimulator(StochasticPetriNetExecution, net_data)
        results = simulator.run_batch(n_runs=args.runs, iterations_per_run=args.steps)

        print("\n--- Final Marking Distribution ---")
        summary = []
        for marking, count in sorted(results["marking_distribution"].items(), key=lambda x: x[1], reverse=True):
            perc = (count / args.runs) * 100
            print(f" {perc:5.1f}% | {marking}")
            summary.append({"marking": marking, "count": count, "percentage": round(perc, 2)})

        simulator.export_csv(results["event_logs"], args.csv)
        if args.json:
            with open(args.json, 'w') as f:
                json.dump({"total_runs": args.runs, "distribution": summary}, f, indent=4)

    elif args.command == "simulate":
        executor = StochasticPetriNetExecution(**net_data)
        executor.run_simulation(iterations=args.steps)

    elif args.command == "export":
        # We need a PetriNetStructure for the exporters
        from pypneu.structures import PetriNetStructure
        pn_struct = PetriNetStructure(**net_data)

        if args.format == "json":
            with open(args.output, "w") as f:
                f.write(to_json(pn_struct))
        elif args.format == "pnml":
            to_pnml(pn_struct, args.output)
        elif args.format == "dot":
            with open(args.output, "w") as f:
                f.write(to_dot(pn_struct))
        elif args.format == "png":
            viewer = PetriNetViewer(pn_struct)
            viewer.save_png(args.output)
        print(f"✅ Exported to {args.output}")

    elif args.command == "animate":
        generate_gif(net_data, args.steps, args.output)


if __name__ == "__main__":
    main()
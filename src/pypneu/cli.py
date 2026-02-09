import argparse
import sys
import os
import json
import imageio
import logging
import numpy as np
from PIL import Image
from io import BytesIO

import pypneu

from pypneu import (
    StochasticPetriNetExecution,
    BatchSimulator,
    PetriNetViewer,
    PetriNetStructure,
    ArcType
)
from pypneu.exporter import to_json, to_pnml, to_dot

# Configure logging to show up in the console when running the CLI
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("pypneu.cli")

def generate_gif(net_data, steps, output_path):
    """Fires transitions and compiles frames with logic highlighting and a step counter."""
    executor = StochasticPetriNetExecution(**net_data)
    frames = []

    print(f"🎬 Generating animation ({steps} steps)...")
    logger.info(f"Animation started for {output_path}")

    for i in range(steps + 1):
        enabled = [t.nid for t in executor.pn.transitions if t.is_enabled()]
        inhibited = [
            t.nid for t in executor.pn.transitions
            if not t.is_enabled() and any(a.source.marking for a in t.inputs if a.type == ArcType.INHIBITOR)
        ]

        viewer = PetriNetViewer(
            executor.pn,
            highlight_green=enabled,
            highlight_red=inhibited
        )

        graph = viewer.to_pydot_graph()
        graph.set_label(f"Step: {i} | Tokens: {sum(1 for p in executor.pn.places if p.marking)}")
        graph.set_labelloc("t")
        graph.set_fontsize(14)
        graph.set_fontname("Arial Bold")

        png_data = graph.create_png()
        img = Image.open(BytesIO(png_data)).convert("RGB")
        frames.append(np.array(img))

        if i < steps:
            if not executor.step():
                print(f"⏹️  Simulation reached deadlock at step {i}.")
                logger.info(f"Deadlock reached at step {i}")
                graph.set_label(f"Step: {i} - DEADLOCK REACHED")
                graph.set_fontcolor("red")
                last_png = graph.create_png()
                frames[-1] = np.array(Image.open(BytesIO(last_png)).convert("RGB"))
                for _ in range(5): frames.append(frames[-1])
                break

    imageio.mimsave(output_path, frames, duration=600, loop=0)
    print(f"✅ Animation saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(prog="pypneu", description="Pypneu: Petri Net Toolchain")
    parser.add_argument("file", help="Path to the .pneu source file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

    # --- Batch Command ---
    batch_p = subparsers.add_parser("batch", help="Run stochastic analysis")
    batch_p.add_argument("-n", "--runs", type=int, default=100, help="Number of runs")
    batch_p.add_argument("--steps", type=int, default=50, help="Max steps per run")
    batch_p.add_argument("--csv", default="output/audit.csv", help="CSV audit log path")
    batch_p.add_argument("--json", default="output/traces.json", help="JSON state-trace path")

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
    anim_p.add_argument("-o", "--output", default="output/simulation.gif", help="Output filename")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("pypneu").setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    if not os.path.exists(args.file):
        logger.error(f"File '{args.file}' not found.")
        sys.exit(1)

    try:
        net_data = pypneu.compile_file(args.file)
        logger.info(f"Compiled {args.file} successfully.")
    except Exception as e:
        logger.error(f"Compilation Error: {e}")
        sys.exit(1)

    if args.command == "batch":
        # Create directories if they don't exist
        for path in [args.csv, args.json]:
            dir_name = os.path.dirname(path)
            if dir_name and not os.path.exists(dir_name):
                logger.info(f"Creating directory: {dir_name}")
                os.makedirs(dir_name, exist_ok=True)

        simulator = BatchSimulator(StochasticPetriNetExecution, net_data)
        results = simulator.run_batch(n_runs=args.runs, iterations_per_run=args.steps)

        # 1. Export CSV
        if results.get("event_logs"):
            simulator.export_csv(results["event_logs"], args.csv)
        else:
            logger.warning("No event logs generated. CSV will not be exported.")

        # 2. Export JSON (The key fix: ensuring json_data exists and is passed)
        json_payload = results.get("json_data")
        if json_payload and json_payload.get("paths"):
            logger.info(f"Exporting {len(json_payload['paths'])} paths to JSON.")
            simulator.export_json(json_payload, args.json)
        else:
            logger.error("JSON trace data is empty or missing from results!")

        # 3. Print Summary
        print("\n--- Final Marking Distribution ---")
        for marking, count in results["marking_distribution"].most_common(5):
            perc = (count / args.runs) * 100
            print(f" {perc:5.1f}% | {marking}")

    elif args.command == "simulate":
        executor = StochasticPetriNetExecution(**net_data)
        logger.info("Starting single simulation run.")
        executor.run_simulation(iterations=args.steps)

    elif args.command == "export":
        pn_struct = PetriNetStructure(**net_data)
        logger.info(f"Exporting net to {args.format} format.")
        if args.format == "json":
            with open(args.output, "w") as f: f.write(to_json(pn_struct))
        elif args.format == "pnml":
            to_pnml(pn_struct, args.output)
        elif args.format == "dot":
            with open(args.output, "w") as f: f.write(to_dot(pn_struct))
        elif args.format == "png":
            PetriNetViewer(pn_struct).save_png(args.output)
        print(f"✅ Exported to {args.output}")

    elif args.command == "animate":
        generate_gif(net_data, args.steps, args.output)

if __name__ == "__main__":
    main()
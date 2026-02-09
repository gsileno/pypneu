import csv
import sys
import copy
import logging
from collections import Counter
from typing import List, Dict, Any

# Set up logger for the simulator
logger = logging.getLogger("pypneu.simulator")


class BatchSimulator:
    def __init__(self, execution_class, net_params: Dict[str, Any]):
        self.execution_class = execution_class
        self.net_params = net_params

    def run_batch(self, n_runs: int, iterations_per_run: int = 100):
        """Executes multiple stochastic runs and aggregates ALL event logs."""
        final_markings = []
        event_logs = []

        logger.info(f"Starting batch of {n_runs} runs.")
        print(f"🚀 Starting Batch Simulation: {n_runs} runs...")

        for run_id in range(n_runs):
            logger.debug(f"--- Starting Run ID: {run_id} ---")

            # Deepcopy ensures a fresh state for every run
            try:
                current_places = copy.deepcopy(self.net_params.get('places', []))
                current_transitions = copy.deepcopy(self.net_params.get('transitions', []))
                current_arcs = copy.deepcopy(self.net_params.get('arcs', []))

                executor = self.execution_class(
                    places=current_places,
                    transitions=current_transitions,
                    arcs=current_arcs
                )
            except Exception as e:
                logger.error(f"Failed to initialize executor for run {run_id}: {e}")
                break

            run_event_count = 0
            for step_idx in range(1, iterations_per_run + 1):
                fired_group = executor.step()

                if fired_group:
                    main_t = fired_group[0]
                    label = main_t.label or main_t.nid

                    logger.debug(f"Run {run_id} | Step {step_idx} | Fired: {label}")

                    event_logs.append({
                        "run_id": run_id,
                        "step": step_idx,
                        "event_type": label
                    })
                    run_event_count += 1
                else:
                    logger.debug(f"Run {run_id} | Step {step_idx} | Deadlock reached (no enabled transitions).")
                    break

            logger.debug(f"Run {run_id} completed with {run_event_count} events.")
            final_markings.append(executor.pn.marking_to_string())

            # Progress Bar
            progress = (run_id + 1) / n_runs
            bar_len = 30
            filled = int(bar_len * progress)
            bar = "█" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\rProgress: |{bar}| {int(progress * 100)}% ({run_id + 1}/{n_runs})")
            sys.stdout.flush()

        print("\n✅ Batch simulation finished.")
        logger.info(f"Batch complete. Total events collected: {len(event_logs)}")

        return {
            "marking_distribution": Counter(final_markings),
            "event_logs": event_logs
        }

    def export_csv(self, event_logs: List[Dict], filename: str = "event_log.csv"):
        """Exports the flattened event logs to a CSV."""
        if not event_logs:
            logger.warning("Export requested but event_logs list is empty.")
            print("⚠️ No events were captured to export.")
            return None

        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                fieldnames = ["run_id", "step", "event_type"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(event_logs)

            logger.info(f"Successfully exported {len(event_logs)} events to {filename}")
            print(f"📈 Audit CSV exported: {len(event_logs)} total events to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to write CSV to {filename}: {e}")
            print(f"❌ CSV Export Error: {e}")
            return None
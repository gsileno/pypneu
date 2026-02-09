import csv
import sys
import copy
import json
import logging
import os
from collections import Counter
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("pypneu.simulator")


class BatchSimulator:
    def __init__(self, execution_class, net_params: Dict[str, Any]):
        self.execution_class = execution_class
        self.net_params = net_params

    def _get_current_state_key(self, executor) -> Tuple[str, ...]:
        """Returns a sorted tuple of active place labels (places with tokens)."""
        # CRITICAL: We explicitly check p.marking and capture the label or NID
        active = []
        for p in executor.pn.places:
            if p.marking:
                name = p.label if p.label else str(p.nid)
                active.append(name)

        state_key = tuple(sorted(active))
        logger.debug(f"State Fingerprint: {state_key}")
        return state_key

    def run_batch(self, n_runs: int, iterations_per_run: int = 100):
        """Executes runs and aggregates paths by count to save space."""
        final_markings = []
        event_logs = []
        path_counter = Counter()
        state_registry: Dict[Tuple[str, ...], str] = {}

        print(f"🚀 Starting Batch Simulation: {n_runs} runs...")

        for run_id in range(n_runs):
            # We deepcopy the whole params dict to maintain internal pointer integrity
            params = copy.deepcopy(self.net_params)
            executor = self.execution_class(
                places=params.get('places', []),
                transitions=params.get('transitions', []),
                arcs=params.get('arcs', [])
            )

            current_path = []

            # 1. Capture Initial State
            initial_key = self._get_current_state_key(executor)
            if initial_key not in state_registry:
                state_registry[initial_key] = f"s{len(state_registry)}"

            current_path.append(state_registry[initial_key])

            for step_idx in range(1, iterations_per_run + 1):
                # 2. Fire Transition
                fired_group = executor.step()

                if fired_group:
                    # Capture Transition Label
                    main_t = fired_group[0]
                    t_label = main_t.label or main_t.nid
                    current_path.append(t_label)

                    # 3. Capture Resulting State
                    new_state_key = self._get_current_state_key(executor)
                    if new_state_key not in state_registry:
                        state_registry[new_state_key] = f"s{len(state_registry)}"

                    state_id = state_registry[new_state_key]
                    current_path.append(state_id)

                    logger.debug(f"Run {run_id} Step {step_idx}: {t_label} -> {state_id}")

                    event_logs.append({
                        "run_id": run_id,
                        "step": step_idx,
                        "event_type": t_label
                    })
                else:
                    break

            path_counter[tuple(current_path)] += 1
            final_markings.append(executor.pn.marking_to_string())

            # Progress Bar
            progress = (run_id + 1) / n_runs
            bar_len = 30
            filled_len = int(bar_len * progress)
            bar = '█' * filled_len + '-' * (bar_len - filled_len)
            sys.stdout.write(f"\rProgress: |{bar}| {int(progress * 100)}% ({run_id + 1}/{n_runs})")
            sys.stdout.flush()

        print("\n✅ Batch simulation finished.")

        unique_paths = [list(p) for p in path_counter.keys()]
        counts = list(path_counter.values())
        formatted_states = {v: list(k) for k, v in state_registry.items()}

        return {
            "marking_distribution": Counter(final_markings),
            "event_logs": event_logs,
            "json_data": {
                "paths": unique_paths,
                "counts": counts,
                "states": formatted_states
            }
        }

    def export_csv(self, event_logs: List[Dict], filename: str = "event_log.csv"):
        if not event_logs: return None
        try:
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["run_id", "step", "event_type"])
                writer.writeheader()
                writer.writerows(event_logs)
                f.flush()
                os.fsync(f.fileno())
            return filename
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            return None

    def export_json(self, json_data: Dict, filename: str = "traces.json"):
        if not json_data or not json_data.get("paths"): return None
        try:
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            return filename
        except Exception as e:
            logger.error(f"Failed to write JSON: {e}")
            return None
import csv
import time
from typing import List, Tuple, Any

# Assuming these are the refactored classes from previous steps
from pypneu.structures import Place, Transition, Arc, Binding
from pypneu.analysis import PetriNetAnalysis
from pypneu.eventcalculus import PetriNetEventCalculus


class PetriNetFactory:
    """Utility class to generate standard Petri Net patterns."""

    @staticmethod
    def build_serial(n: int) -> Tuple[List[Place], List[Transition], List[Arc]]:
        """Generates a linear sequence of P -> T -> P."""
        places = [Place(label="p0", marking=True)]
        transitions = []
        arcs = []

        for i in range(1, n + 1):
            p_next = Place(label=f"p{i}")
            t = Transition(label=f"t{i}")

            arcs.append(places[-1].connect_to(t))
            arcs.append(t.connect_to(p_next))

            places.append(p_next)
            transitions.append(t)

        return places, transitions, arcs

    @staticmethod
    def build_fork_recursive(depth: int, root_place: Place = None) -> Tuple[List[Place], List[Transition], List[Arc]]:
        """Generates a binary tree of forks."""
        if root_place is None:
            root_place = Place(label="root", marking=True)

        places = [root_place]
        transitions = []
        arcs = []

        if depth <= 0:
            return places, transitions, arcs

        # Create two branches
        t1, t2 = Transition(label=f"fork_t{depth}_L"), Transition(label=f"fork_t{depth}_R")
        p_l, p_r = Place(label=f"p{depth}_L"), Place(label=f"p{depth}_R")

        # Connect
        arcs.extend([
            root_place.connect_to(t1),
            root_place.connect_to(t2),
            t1.connect_to(p_l),
            t2.connect_to(p_r)
        ])
        transitions.extend([t1, t2])

        # Recurse
        for p_branch in [p_l, p_r]:
            sub_p, sub_t, sub_a = PetriNetFactory.build_fork_recursive(depth - 1, p_branch)
            # Avoid duplicating the branch root place
            places.extend(sub_p[1:])
            transitions.extend(sub_t)
            arcs.extend(sub_a)

        return places, transitions, arcs


def run_benchmarks(output_file: str = "evaluation.csv"):
    """Executes the benchmark suite and saves results to CSV."""

    headers = ["Trial", "N", "Topology", "Engine", "Models", "Timing"]

    with open(output_file, "w", newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(headers)

        # Configurable ranges
        TRIALS = range(1, 11)
        FORK_RANGE = range(1, 9)
        SERIAL_RANGE = range(1, 52, 5)

        for trial in TRIALS:
            print(f"Starting Trial {trial}...")

            # --- Fork Topology Benchmarks ---
            for n in FORK_RANGE:
                # Test LPPN (Analysis)
                p, t, a = PetriNetFactory.build_fork_recursive(n)
                net = PetriNetAnalysis(PetriNetExecutor(p, t, a))  # Assumes executor injection
                models, timing, _ = net.run_analysis()
                writer.writerow([trial, n, "Fork", "LPPN", models, f"{timing:.6f}"])

                # Test Event Calculus
                p, t, a = PetriNetFactory.build_fork_recursive(n)
                net_ec = PetriNetEventCalculus(p, t, a)
                models_ec, timing_ec = net_ec.solve(n)
                writer.writerow([trial, n, "Fork", "EC", models_ec, f"{timing_ec:.6f}"])

            # --- Serial Topology Benchmarks ---
            for n in SERIAL_RANGE:
                # Test LPPN
                p, t, a = PetriNetFactory.build_serial(n)
                net = PetriNetAnalysis(PetriNetExecutor(p, t, a))
                models, timing, _ = net.run_analysis()
                writer.writerow([trial, n, "Serial", "LPPN", models, f"{timing:.6f}"])

                # Test Event Calculus
                p, t, a = PetriNetFactory.build_serial(n)
                net_ec = PetriNetEventCalculus(p, t, a)
                models_ec, timing_ec = net_ec.solve(n - 1)
                writer.writerow([trial, n, "Serial", "EC", models_ec, f"{timing_ec:.6f}"])

    print(f"Benchmarks completed. Data saved to {output_file}")


if __name__ == "__main__":
    run_benchmarks()
"""
pypneu - Event Calculus engine for Petri Nets.
Translates PN structures into temporal ASP programs for pathfinding and reasoning.
"""

import logging
from timeit import default_timer as timer
from clingo import Control, parse_program
from .structures import PetriNetStructure, Place, Transition, ArcType

logger = logging.getLogger("pypneu.ec")


class PetriNetEventCalculus(PetriNetStructure):
    def __init__(self, places=(), transitions=(), arcs=(), p_bindings=(), t_bindings=()):
        super().__init__(places, transitions, arcs, p_bindings, t_bindings)
        self.n_models = 0

    @staticmethod
    def get_axioms() -> str:
        """Returns the core Event Calculus and Operational rules."""
        return """
        % --- Core Event Calculus ---
        holdsAt(F, P, T2) :- initially(F, P), not clipped(0, F, P, T2), fluent(F), place(P), time(T2).
        holdsAt(F, P, T2) :- firesAt(Tr, T1), T1 < T2, initiates(Tr, F, P, T1), 
                             not clipped(T1, F, P, T2), place(P), transition(Tr), time(T1;T2).
        clipped(T1, F, P, T2) :- firesAt(Tr, T), T1 <= T, T < T2, terminates(Tr, F, P, T), 
                                 place(P), transition(Tr), time(T1;T2;T).

        % --- Operational Rules (Single token flow) ---
        {prefiresAt(Tr, T)} :- enabled(Tr, T), transition(Tr), time(T).
        someTransitionPrefiresAt(T) :- prefiresAt(Tr, T).

        :- not someTransitionPrefiresAt(0).
        :- T > 0, not someTransitionPrefiresAt(T-1), time(T).
        :- prefiresAt(Tr1, T), prefiresAt(Tr2, T), Tr1 != Tr2.

        firesAt(Tr, T) :- prefiresAt(Tr, T).
        fluent(filled).
        """

    def build_program(self, max_time: int) -> str:
        """Assembles the full ASP program for the current net."""
        lines = [self.get_axioms(), f"time(0..{max_time})."]

        # Build Places
        for p in self.places:
            lines.append(f"place({p.nid}).")
            if p.marking:
                lines.append(f"initially(filled, {p.nid}).")

            # Constraint: A place can't be drained by two different transitions simultaneously
            drainers = [a.target.nid for a in p.outputs if a.type == ArcType.ENABLER]
            if len(drainers) > 1:
                drain_list = "; ".join(f"terminates({t}, filled, {p.nid}, T)" for t in drainers)
                lines.append(f":- 2 {{ {drain_list} }}.")

        # Build Transitions
        for t in self.transitions:
            lines.append(f"transition({t.nid}).")

            # Enabled logic
            normal = [a.source.nid for a in t.inputs if a.type == ArcType.ENABLER]
            inhibitors = [a.source.nid for a in t.inputs if a.type == ArcType.INHIBITOR]

            if normal:
                body = ", ".join([f"holdsAt(filled, {p}, T)" for p in normal] +
                                 [f"not holdsAt(filled, {p}, T)" for p in inhibitors])
                lines.append(f"enabled({t.nid}, T) :- {body}, time(T).")

                # Consumption and Production
                for p in normal:
                    lines.append(f"terminates({t.nid}, filled, {p}, T) :- firesAt({t.nid}, T).")

            for out_arc in t.outputs:
                if out_arc.type == ArcType.ENABLER:
                    lines.append(f"initiates({t.nid}, filled, {out_arc.target.nid}, T) :- firesAt({t.nid}, T).")

        return "\n".join(lines)

    def _on_model(self, model):
        self.n_models += 1

    def solve(self, max_time: int) -> tuple:
        """Solves the EC program and returns (count, execution_time)."""
        self.n_models = 0
        program_code = self.build_program(max_time)

        # Setup Clingo
        ctl = Control(arguments=["--models=0"])
        with ctl.builder() as b:
            parse_program(program_code, b.add)

        ctl.ground([("base", [])])

        start = timer()
        ctl.solve(on_model=self._on_model)
        duration = timer() - start

        logger.info(f"EC Solver: {self.n_models} models found in {duration:.4f}s")
        return self.n_models, duration
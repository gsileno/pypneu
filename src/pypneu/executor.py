"""
pypneu - Execution engine for Logic Programming Petri Nets (LPPNs).
Handles token flow, logical inference via Clingo, and story-driven simulation.
"""

import logging
from typing import List, Optional, Iterable
from clingo import Control, Function, parse_program

# Assuming structures.py contains the previously refactored Node, Place, Transition classes
from .structures import PetriNetStructure, Place, Transition

logger = logging.getLogger("pypneu.executor")

class PetriNetExecution:
    """
    Handles the execution cycle of an LPPN:
    1. Place Inference: Apply logic to find co-occurrent conditions.
    2. Transition Selection: Choose an enabled transition (or follow a story).
    3. Transition Inference: Propagate logical dependencies between transitions.
    4. Firing: Consume and produce tokens.
    """

    def __init__(self,
                 places: Iterable[Place] = (),
                 transitions: Iterable[Transition] = (),
                 arcs: Iterable = (),
                 p_bindings: Iterable = (),
                 t_bindings: Iterable = (),
                 story: List[str] = None):

        self.pn = PetriNetStructure(places, transitions, arcs, p_bindings, t_bindings)
        self.story = list(story) if story else []
        self.remaining_story = self.story.copy()

        # Clingo Controllers
        self.p_solver: Optional[Control] = None
        self.t_solver: Optional[Control] = None

        # Temp state for callbacks
        self._firing_group: List[Transition] = []

    def init_control(self):
        """Initializes and grounds the ASP solvers for places and transitions."""
        # Setup Place Solver
        self.p_solver = Control(["--models=0"])
        with self.p_solver.builder() as b:
            parse_program(self.pn.p_code(), b.add)
        self.p_solver.ground([("base", [])])

        # Setup Transition Solver
        self.t_solver = Control(["--models=0"])
        with self.t_solver.builder() as b:
            parse_program(self.pn.t_code(), b.add)
        self.t_solver.ground([("base", [])])

    def run_simulation(self, iterations: int) -> int:
        """Runs the simulation for a fixed number of steps."""
        self.init_control()

        steps_completed = 0
        for i in range(iterations):
            logger.info(f"Attempting execution step {i}")
            if not self.step():
                logger.info(f"Simulation stopped at step {i}: No transitions enabled.")
                break
            steps_completed += 1

        print(f"Final Marking: {self.pn.marking_to_string()}")
        print(f"Simulation finished: {steps_completed} steps completed.")
        return steps_completed

    def step(self) -> bool:
        """Executes a single LPPN cycle."""
        self._firing_group = []

        # 1. Place Inference
        self._resolve_place_logic()

        # 2. Selection
        target = self._select_transition()
        if not target:
            return False

        # 3. Transition Inference & 4. Firing
        self._resolve_transition_logic(target)
        self._fire_group(self._firing_group)

        return True

    def _resolve_place_logic(self):
        """Syncs current markings to Clingo and runs inference."""
        for p in self.pn.places:
            # Toggle external atoms based on current marking
            self.p_solver.assign_external(Function(p.nid), p.marking)

        self.p_solver.solve(on_model=self._place_callback)

    def _place_callback(self, model):
        """Updates internal markings based on logic results."""
        for atom in model.symbols(shown=True):
            nid = str(atom)
            if nid in self.pn.id2place:
                self.pn.id2place[nid].marking = True

    def _select_transition(self) -> Optional[Transition]:
        """Selects transition based on the story or availability."""
        # Story-driven selection (Greedy)
        if self.remaining_story:
            next_label = self.remaining_story[0]
            for t in self.pn.transitions:
                if t.label == next_label and (t.is_source or t.is_enabled()):
                    self.remaining_story.pop(0)
                    return t

        # Default: First enabled transition
        return next((t for t in self.pn.transitions if t.is_enabled()), None)

    def _resolve_transition_logic(self, trigger: Transition):
        """Propagates logic from the triggered transition to its dependents."""
        for t in self.pn.transitions:
            self.t_solver.assign_external(Function(t.nid), t == trigger)

        self.t_solver.solve(on_model=self._transition_callback)

    def _transition_callback(self, model):
        """Collects all transitions that must fire together."""
        for atom in model.symbols(shown=True):
            nid = str(atom)
            if nid in self.pn.id2transition:
                self._firing_group.append(self.pn.id2transition[nid])

    def _fire_group(self, transitions: List[Transition]):
        """Executes the actual token movement for a group of transitions."""
        for t in transitions:
            logger.info(f"Firing transition: {t.nid} ({t.label})")
            t.consume_input_tokens()
            t.produce_output_tokens()
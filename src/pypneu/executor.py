import logging
from typing import List, Optional, Iterable, Set
from .structures import PetriNetStructure, Place, Transition

logger = logging.getLogger("pypneu.executor")

class PetriNetExecution:
    def __init__(self,
                 places: Iterable[Place] = (),
                 transitions: Iterable[Transition] = (),
                 arcs: Iterable = (),
                 story: List[str] = None):

        self.pn = PetriNetStructure(places, transitions, arcs)
        self.story = list(story) if story else []
        self.remaining_story = self.story.copy()

    def run_simulation(self, iterations: int) -> int:
        steps_completed = 0
        for i in range(iterations):
            logger.info(f"Attempting execution step {i}")
            if not self.step():
                logger.info(f"Simulation stopped at step {i}: No transitions enabled.")
                break
            steps_completed += 1

        print(f"\nFinal Marking: {self.pn.marking_to_string()}")
        return steps_completed

    def step(self) -> bool:
        firing_group = self._select_transition_group()
        if not firing_group:
            return False

        self._fire_group(firing_group)
        return True

    def _is_group_ready(self, group: List[Transition]) -> bool:
        """
        Validates if a group (Bus) can fire.
        Sources are blocked if they have already fired once.
        """
        if not group:
            return False

        for t in group:
            # Check basic Petri Net enabling or source status
            if not (t.is_enabled() or t.is_source):
                return False

            # Constraint: Transitions with no input (Sources) fire max once
            if t.is_source and t.fired_count >= 1:
                logger.debug(f"Source transition '{t.label}' blocked: already fired.")
                return False
        return True

    def _select_transition_group(self) -> List[Transition]:
        # 1. Story Priority
        if self.remaining_story:
            target_label = self.remaining_story[0]
            group = [t for t in self.pn.transitions if t.label == target_label]

            if self._is_group_ready(group):
                self.remaining_story.pop(0)
                logger.info(f"Story match: Firing bus group '{target_label}'")
                return group
            return [] # Story blocked

        # 2. Automatic Selection (if no story or story finished)
        processed_labels: Set[str] = set()
        for t in self.pn.transitions:
            if t.label and t.label not in processed_labels:
                group = [x for x in self.pn.transitions if x.label == t.label]
                if self._is_group_ready(group):
                    return group
                processed_labels.add(t.label)
            elif not t.label:
                if self._is_group_ready([t]):
                    return [t]

        return []

    def _fire_group(self, transitions: List[Transition]):
        """Atomic Firing: Consume all inputs before producing any outputs."""
        for t in transitions:
            t.consume_input_tokens()

        for t in transitions:
            t.produce_output_tokens()
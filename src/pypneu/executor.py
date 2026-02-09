import logging
from typing import List, Optional, Iterable, Set, Dict
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
        firing_group = self._get_next_firing_group()
        if not firing_group:
            return False

        self._fire_group(firing_group)
        return True

    def _is_group_ready(self, group: List[Transition]) -> bool:
        """Validates if a group (Bus) can fire."""
        if not group:
            return False

        for t in group:
            if not (t.is_enabled() or t.is_source):
                return False

            if t.is_source and t.fired_count >= 1:
                logger.debug(f"Source transition '{t.label}' blocked: already fired.")
                return False
        return True

    def _get_next_firing_group(self) -> List[Transition]:
        """Orchestrates selection logic: Story first, then Automatic/Stochastic."""
        # 1. Story Priority
        if self.remaining_story:
            target_label = self.remaining_story[0]
            group = [t for t in self.pn.transitions if t.label == target_label]

            if self._is_group_ready(group):
                self.remaining_story.pop(0)
                logger.info(f"Story match: Firing bus group '{target_label}'")
                return group
            return []  # Story is blocked

        # 2. Collect ALL currently enabled groups
        enabled_map: Dict[str, List[Transition]] = {}
        processed_labels: Set[str] = set()

        for t in self.pn.transitions:
            # Use label as key, or a unique string for unlabeled transitions
            key = t.label if t.label else f"unlabeled_{id(t)}"

            if key not in processed_labels:
                group = [x for x in self.pn.transitions if x.label == t.label]
                if self._is_group_ready(group):
                    enabled_map[key] = group
                processed_labels.add(key)

        # 3. Delegate selection to the hook (overridden in Stochastic subclass)
        return self.select_transition_group(enabled_map)

    def select_transition_group(self, enabled_map: Dict[str, List[Transition]]) -> List[Transition]:
        """
        Hook for selection strategy.
        Default behavior is deterministic: returns the first group found.
        """
        if not enabled_map:
            return []

        # Consistent deterministic choice (first key in dict)
        first_key = next(iter(enabled_map))
        return enabled_map[first_key]

    def _fire_group(self, transitions: List[Transition]):
        """Atomic Firing: Consume all inputs before producing any outputs."""
        for t in transitions:
            t.consume_input_tokens()

        for t in transitions:
            t.produce_output_tokens()

import random
class StochasticPetriNetExecution(PetriNetExecution):

    def select_transition_group(self, enabled_map):
        if not enabled_map:
            return []
        labels = list(enabled_map.keys())
        chosen_label = random.choice(labels)
        return enabled_map[chosen_label]
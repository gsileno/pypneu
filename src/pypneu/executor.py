import logging
import random
from typing import List, Optional, Iterable, Set, Dict
from .structures import PetriNetStructure, Place, Transition

# Set up logger
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
        logger.info(f"Starting simulation for {iterations} iterations.")
        for i in range(iterations):
            if not self.step():
                logger.info(f"Simulation stopped at step {i}: No transitions enabled.")
                break
            steps_completed += 1

        logger.debug(f"Final Marking: {self.pn.marking_to_string()}")
        return steps_completed

    def step(self) -> Optional[List[Transition]]:
        firing_group = self._get_next_firing_group()
        if not firing_group:
            return None

        # Log the group chosen to fire
        group_labels = [t.label or t.nid for t in firing_group]
        logger.debug(f"Step Execution: Selected group {group_labels}")

        self._fire_group(firing_group)
        return firing_group

    def _is_group_ready(self, group: List[Transition]) -> bool:
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
        if self.remaining_story:
            target_label = self.remaining_story[0]
            group = [t for t in self.pn.transitions if t.label == target_label]

            if self._is_group_ready(group):
                logger.debug(f"Story match found: Firing '{target_label}'")
                self.remaining_story.pop(0)
                return group
            logger.debug(f"Story block: '{target_label}' is not enabled.")
            return []

        enabled_map: Dict[str, List[Transition]] = {}
        processed_labels: Set[str] = set()

        for t in self.pn.transitions:
            key = t.label if t.label else f"unlabeled_{id(t)}"

            if key not in processed_labels:
                group = [x for x in self.pn.transitions if x.label == t.label]
                if self._is_group_ready(group):
                    enabled_map[key] = group
                processed_labels.add(key)

        return self.select_transition_group(enabled_map)

    def select_transition_group(self, enabled_map: Dict[str, List[Transition]]) -> List[Transition]:
        if not enabled_map:
            return []
        first_key = next(iter(enabled_map))
        return enabled_map[first_key]

    def _fire_group(self, transitions: List[Transition]):
        """Atomic Firing: Consume all inputs before producing any outputs."""

        # Phase 1: Consumption
        for t in transitions:
            label = t.label or t.nid
            # Log current marking of inputs before consumption
            inputs = [f"{a.source.label or a.source.nid}:{a.source.marking}" for a in t.inputs]
            logger.debug(f"Transition [{label}] consuming from: {', '.join(inputs)}")

            t.consume_input_tokens()

        # Phase 2: Production
        for t in transitions:
            label = t.label or t.nid
            t.produce_output_tokens()

            # Log new marking of outputs after production
            outputs = [f"{a.target.label or a.target.nid}:{a.target.marking}" for a in t.outputs]
            logger.debug(f"Transition [{label}] produced to: {', '.join(outputs)}")


class StochasticPetriNetExecution(PetriNetExecution):
    def select_transition_group(self, enabled_map: Dict[str, List[Transition]]) -> List[Transition]:
        if not enabled_map:
            return []
        labels = list(enabled_map.keys())
        chosen_label = random.choice(labels)
        logger.debug(f"Stochastic Choice: Picked '{chosen_label}' from {labels}")
        return enabled_map[chosen_label]
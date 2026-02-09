import logging
from collections import deque
from dataclasses import dataclass, field
from timeit import default_timer as timer
from typing import List, Dict, Optional, FrozenSet, Tuple, Set

# Configure Logger
logger = logging.getLogger("pypneu.analyzer")


@dataclass(eq=False)
class State:
    """Represents a unique marking in the Petri Net state space."""
    marking: Dict[str, bool]
    sid: str
    # Map of Transition Group (labels) -> Resulting State
    access_function: Dict[str, Optional['State']] = field(default_factory=dict)

    def find_next_unexplored_label(self) -> Optional[str]:
        """Returns the first transition label that hasn't been explored from this state."""
        for label, target_state in self.access_function.items():
            if target_state is None:
                return label
        return None

    def __str__(self) -> str:
        marking_str = ", ".join(f"{k}: {'●' if v else '○'}" for k, v in self.marking.items())
        return f"{self.sid} | {marking_str}"


@dataclass
class Path:
    """Data structure for recording an execution sequence."""
    path_id: str
    steps: List[State] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)

    def clone(self, new_id: str, up_to_index: Optional[int] = None) -> 'Path':
        """Creates a shallow copy for backtracking."""
        n = up_to_index if up_to_index is not None else len(self.steps)
        return Path(
            path_id=new_id,
            steps=self.steps[:n + 1],
            labels=self.labels[:n]
        )


class PetriNetAnalysis:
    """Explores the state space to detect deadlocks and reachability without ASP."""

    def __init__(self, executor):
        self.executor = executor
        self.pn = executor.pn

        # Repositories
        self.path_base: List[Path] = []
        self.state_base: List[State] = []

        # Current Context
        self.current_path: Optional[Path] = None
        self.current_state: Optional[State] = None

    def _get_new_path_id(self) -> str:
        return f"path{len(self.path_base)}"

    def _get_current_marking_map(self) -> Dict[str, bool]:
        return {p.nid: p.marking for p in self.pn.places}

    def _set_marking(self, marking_map: Dict[str, bool]):
        """Restores the PN to a specific marking."""
        for p in self.pn.places:
            p.marking = marking_map.get(p.nid, False)

    def _record_state(self) -> State:
        """Saves current marking as a state if it doesn't exist."""
        marking = self._get_current_marking_map()

        # Search for existing state with this marking
        state = next((s for s in self.state_base if s.marking == marking), None)
        if not state:
            state = State(marking=marking, sid=f"s{len(self.state_base)}")
            self.state_base.append(state)
            # Find all fireable buses from this marking
            self._populate_available_labels(state)

        return state

    def _populate_available_labels(self, state: State):
        """Identifies which transition labels are currently fireable."""
        available_labels = {}
        processed_labels = set()

        for t in self.pn.transitions:
            if t.label not in processed_labels:
                # Use executor's internal logic to see if this bus is ready
                group = [x for x in self.pn.transitions if x.label == t.label]
                if self.executor._is_group_ready(group):
                    available_labels[t.label] = None
                processed_labels.add(t.label)

        state.access_function = available_labels

    def run_analysis(self, max_states: int = 500) -> Tuple[int, float, int]:
        """DFS exploration of all possible markings."""
        start_time = timer()
        self.state_base.clear()
        self.path_base.clear()

        # Initial State
        initial_state = self._record_state()
        self.current_path = Path(self._get_new_path_id(), steps=[initial_state])
        self.current_state = initial_state
        self.path_base.append(self.current_path)

        iterations = 0
        while iterations < max_states:
            iterations += 1
            if not self._step():
                break

        duration = timer() - start_time
        logger.info(f"Analysis complete: {len(self.state_base)} states explored.")
        return len(self.state_base), duration, iterations

    def _step(self) -> bool:
        """The core DFS logic: Try a label, if stuck, backtrack."""

        # 1. Look for an unexplored transition from current state
        label_to_fire = self.current_state.find_next_unexplored_label()

        if label_to_fire:
            # Prepare for firing
            group = [t for t in self.pn.transitions if t.label == label_to_fire]

            # Fire and record results
            self.executor._fire_group(group)
            new_state = self._record_state()

            # Link the transition in the state graph
            self.current_state.access_function[label_to_fire] = new_state

            # Update path
            self.current_path.steps.append(new_state)
            self.current_path.labels.append(label_to_fire)

            # Move to new state (unless it's a cycle)
            self.current_state = new_state
            return True

        # 2. Backtrack if no labels left to explore from current state
        for i in range(len(self.current_path.steps) - 2, -1, -1):
            backtrack_state = self.current_path.steps[i]
            if backtrack_state.find_next_unexplored_label():
                # Fork a new path for bookkeeping
                self.current_path = self.current_path.clone(self._get_new_path_id(), i)
                self.path_base.append(self.current_path)

                # Rewind the physical net to this state's marking
                self.current_state = backtrack_state
                self._set_marking(backtrack_state.marking)
                return True

        return False

    def get_deadlocks(self) -> List[State]:
        return [s for s in self.state_base if not s.access_function]

    def print_summary(self):
        print("\n" + "=" * 40)
        print(f"{'PETRI NET REACHABILITY SUMMARY':^40}")
        print("=" * 40)
        print(f"Unique Markings (States): {len(self.state_base)}")
        print(f"Exploration Paths:       {len(self.path_base)}")

        deadlocks = self.get_deadlocks()
        if deadlocks:
            print(f"Deadlocks Detected:      {len(deadlocks)}")
            for d in deadlocks:
                print(f"  > {d.sid}: {d.marking}")
        else:
            print("Liveness: No deadlocks found in explored space.")
        print("=" * 40 + "\n")
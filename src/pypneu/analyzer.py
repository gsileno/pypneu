import logging
from collections import deque
from dataclasses import dataclass, field
from timeit import default_timer as timer
from typing import List, Dict, Optional, FrozenSet, Tuple

# Configure Logger
logger = logging.getLogger("pypneu.analyzer")

@dataclass
class State:
    """Represents a unique marking in the Petri Net state space."""
    marking: Dict[str, bool]
    sid: str
    # Map of Transition Group -> Resulting State
    access_function: Dict[FrozenSet, Optional['State']] = field(default_factory=dict)

    def find_next_unexplored_group(self) -> Optional[FrozenSet]:
        """Returns the first transition group that hasn't been explored."""
        for group, target_state in self.access_function.items():
            if target_state is None:
                return group
        return None

    def __str__(self) -> str:
        marking_str = ", ".join(f"{k}: {v}" for k, v in self.marking.items())
        return f"{self.sid} # {marking_str}"


@dataclass
class Path:
    """Data structure for recording an execution sequence."""
    path_id: str
    steps: List[State] = field(default_factory=list)
    transitions: List[FrozenSet] = field(default_factory=list)

    def clone(self, new_id: str, up_to_index: Optional[int] = None) -> 'Path':
        """Creates a shallow copy for backtracking."""
        n = up_to_index if up_to_index is not None else len(self.steps)
        return Path(
            path_id=new_id,
            steps=self.steps[:n + 1],
            transitions=self.transitions[:n]
        )

    def __str__(self) -> str:
        trans_list = [str([t.nid for t in group]) for group in self.transitions]
        return f"{self.path_id}# " + " -- ".join(trans_list)


class PetriNetAnalysis:
    """Explores the state space and detects deadlocks/reachability."""

    def __init__(self, executor):
        self.executor = executor
        self.pn = executor.pn

        # Repositories
        self.path_base: deque[Path] = deque()
        self.state_base: deque[State] = deque()

        # Iteration Context
        self.current_path: Optional[Path] = None
        self.current_state: Optional[State] = None
        self.previous_path: Optional[Path] = None
        self.previous_state: Optional[State] = None
        self.fired_group: FrozenSet = frozenset()
        self.discovered_groups: List[FrozenSet] = []

    def _get_new_path_id(self) -> str:
        return f"path{len(self.path_base)}"

    def _get_current_marking_map(self) -> Dict[str, bool]:
        return {p.nid: p.marking for p in self.pn.places}

    def _on_place_model(self, model):
        """Clingo callback to update markings from place-bindings."""
        for atom in model.symbols(shown=True):
            if str(atom) in self.pn.id2place:
                self.pn.id2place[str(atom)].marking = True

        self.current_path = self.previous_path.clone(self._get_new_path_id())
        self.current_state = self._record_state_transition(self.previous_state, self.fired_group)

        if self.current_path not in self.path_base:
            self.path_base.append(self.current_path)

    def _on_transition_model(self, model):
        """Clingo callback to identify fired transition groups."""
        group = frozenset(self.pn.id2transition[str(atom)] for atom in model.symbols(shown=True))
        self.discovered_groups.append(group)

    def _record_state_transition(self, antecedent: Optional[State], fired_group: FrozenSet) -> State:
        marking = self._get_current_marking_map()

        # Search for existing state
        state = next((s for s in self.state_base if s.marking == marking), None)
        if not state:
            state = State(marking=marking, sid=f"s{len(self.state_base)}")
            self._populate_access_function(state)
            self.state_base.append(state)

        self.current_path.steps.append(state)
        if antecedent and fired_group:
            antecedent.access_function[fired_group] = state
            self.current_path.transitions.append(fired_group)

        return state

    def _populate_access_function(self, state: State):
        potential_groups = set()
        for t in self.pn.transitions:
            if t.is_enabled() or (not self.current_path.steps and t.is_source):
                self.discovered_groups = []
                self.executor.set_t_program(t)
                self.executor.t_prog.solve(on_model=self._on_transition_model)
                potential_groups.update(self.discovered_groups)

        state.access_function = {group: None for group in potential_groups}

    def run_analysis(self, max_iterations: int = 100) -> Tuple[int, float, int]:
        """Deep Search exploration of all possible markings."""
        self.executor.init_control()
        self.path_base.clear()
        self.state_base.clear()

        self.previous_path = Path(self._get_new_path_id())
        self.previous_state = None
        self.fired_group = frozenset()

        start_time = timer()
        iterations = 0

        for i in range(max_iterations):
            iterations = i + 1
            if not self._step():
                break

        duration = timer() - start_time
        logger.info(f"Analysis complete: {len(self.state_base)} states in {duration:.4f}s")
        return len(self.path_base), duration, iterations

    def _step(self) -> bool:
        # 1. Update Inferences
        for p in self.pn.places:
            self.executor.p_prog.assign_external(Function(p.nid, (), True), p.marking)
        self.executor.p_prog.solve(on_model=self._on_place_model)

        # 2. Cycle Detection
        is_cycle = self.current_state in self.current_path.steps[:-1]

        next_group = None
        if not is_cycle:
            self.previous_state = self.current_state
            self.previous_path = self.current_path
            next_group = self.current_state.find_next_unexplored_group()

        # 3. Backtrack (DFS)
        if next_group is None:
            for i in range(len(self.current_path.steps) - 2, -1, -1):
                step = self.current_path.steps[i]
                next_group = step.find_next_unexplored_group()
                if next_group:
                    self.current_state = step
                    self.current_path = self.current_path.clone(self._get_new_path_id(), i)
                    # Reset marking to backtracked state
                    for p in self.pn.places:
                        p.marking = step.marking[p.nid]
                    self.previous_path = self.current_path
                    self.previous_state = self.current_state
                    break

        if next_group:
            self.executor.fire(next_group)
            self.fired_group = next_group
            return True

        return False

    # --- Reporting Tools ---

    def get_deadlocks(self) -> List[State]:
        """Identifies states with no possible future transitions."""
        return [s for s in self.state_base if not s.access_function]

    def print_summary(self):
        """Prints a human-readable reachability summary."""
        print("\n" + "="*30)
        print("ANALYSIS SUMMARY")
        print("="*30)
        print(f"Unique States: {len(self.state_base)}")
        print(f"Unique Paths:  {len(self.path_base)}")

        deadlocks = self.get_deadlocks()
        if deadlocks:
            print(f"Deadlocks:     {len(deadlocks)} detected")
            for d in deadlocks:
                print(f"  - {d.sid}: {d.marking}")
        else:
            print("Deadlocks:     None (Net is live or cyclic)")
        print("="*30 + "\n")
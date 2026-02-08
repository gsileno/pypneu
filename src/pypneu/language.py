"""
pypneu.language - Core language primitives for LPPN syntax.
Defines predicates, rules, and programs used by the parser and simulators.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass(frozen=True)
class Predicate:
    """Base atom representation with support for classical negation."""
    atom: str
    neg: bool = False

    def dual(self) -> 'Predicate':
        """Returns the negated version of this predicate."""
        return Predicate(self.atom, not self.neg)

    def __str__(self) -> str:
        prefix = "~" if self.neg else ""
        return f"{prefix}{self.atom}"


@dataclass(frozen=True)
class ConditionPredicate(Predicate):
    """Represents a state-based condition (Place in Petri Net)."""
    pass


@dataclass(frozen=True)
class EventPredicate(Predicate):
    """Represents a firing event (Transition in Petri Net)."""

    def __str__(self) -> str:
        return f"#{self.atom}"


@dataclass
class TransformationalRule:
    """Represents a static logic rule (Head :- Body)."""
    head: Optional[Predicate] = None
    body: List[Predicate] = field(default_factory=list)

    def __post_init__(self):
        if self.head is None and not self.body:
            raise ValueError("TransformationalRule cannot be empty.")

    def is_fact(self) -> bool:
        return self.head is not None and not self.body

    def is_constraint(self) -> bool:
        return self.head is None and len(self.body) > 0

    def to_asp(self) -> str:
        """Converts rule to Answer Set Programming syntax."""
        head_str = str(self.head) if self.head else ""
        if not self.body:
            return f"{head_str}."

        body_str = ", ".join(str(p) for p in self.body)
        if not self.head:
            return f":- {body_str}."
        return f"{head_str} :- {body_str}."


@dataclass
class ActiveRule:
    """
    Event-Condition-Action (ECA) rule.
    Maps to the functional behavior of Petri Net transitions.
    """
    event: EventPredicate
    actions: List[Union[EventPredicate, ConditionPredicate]]
    conditions: List[ConditionPredicate] = field(default_factory=list)

    def __post_init__(self):
        if not self.event or not self.actions:
            raise ValueError("Active rules require both an initiating event and a consequence.")


class ReactiveRule(ActiveRule):
    """Inference rule for transitions (Transition Bindings)."""
    pass


class CausalRule(ActiveRule):
    """Token-flow rule (Standard Petri Net Arcs)."""
    pass


@dataclass
class Story:
    """A sequence of actions to be replayed or analyzed."""
    actions: List[str]

    def __post_init__(self):
        if not self.actions:
            raise ValueError("A story must contain at least one action.")


@dataclass
class Program:
    """Container for a parsed LPPN script."""
    instructions: List[Union[TransformationalRule, ActiveRule, Story]] = field(default_factory=list)
    parsing_errors: List[str] = field(default_factory=list)

    def to_asp(self) -> str:
        """Generates the full ASP program for static analysis."""
        return "\n".join(
            inst.to_asp() for inst in self.instructions
            if isinstance(inst, TransformationalRule)
        )
# pypneu

**pypneu** is a lightweight Petri Net library that focuses on a human-readable "shorthand" for defining complex net structures, including standard consumption/production, catalysts (biflows), and inhibitors.

## syntax 

The library uses a "slot-based" grammar, named PN. A mechanism is defined by the following structure:
`[consumables] [catalysts] -> [inhibitors] #transition [outputs].`
Thinking in terms of a physical model, a mechanism is a unit of production. It is enabled by the presence of relevant resources (including catalysts) and the absence of interfering resources. When triggered, it consumes the inputs and produces other resources.

Conditions (resources) are denoted by lowercase literals (e.g., `a`), while event-types (transitions) are denoted by lowercase literals with a hash prefix (e.g., `#a`).
Places follow a Unique Name Assumption (UNA); therefore, if a place is used across several different mechanisms, it refers to the same entity. In other words, the labels of places are unique.
Transitions, however, do not follow the UNA and may be labeled identically. We assume a "bus" link exists across all transitions sharing the same label: if one transition `#t` is fired, all enabled transitions with that same name fire simultaneously.
During execution, transitions with no input conditions (source transitions) are fired at most once.

| component | syntax | description |
| --- | --- | --- |
| consumables | `a, b -> #t.` | Places `a` and `b` are consumed when `#t` fires. |
| catalysts | `: c -> #t.` | Place `c` must be marked for `#t` to fire, but it is not consumed (biflow). |
| inhibitors | `i -o #t.` | Place `i` must be **empty** for `#t` to fire. |
| outputs | `#t -> out.` | Place `out` receives a token when `#t` fires. |
| factual | `p1, p2.` | Sets the initial marking (token) of places to `True`. |

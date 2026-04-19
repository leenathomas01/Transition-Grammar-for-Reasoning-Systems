# Universalizing Delta
### Phase 2 — Doc 03

*Part of [Transition Grammar for Reasoning Systems](../README.md)*

---

## From Human Labels to System Variables

The transition grammar began with human experience. "Glimmers" — small moments of lived tension resolving into new states — were the original data. The emotional vocabulary that emerged from that work (calm, desperation, joy overriding fear) was useful scaffolding.

But scaffolding isn't structure.

The control architecture defined in Doc 02 operates on `f`, `g`, and `π` — functions that take state vectors, pressure signals, and candidate operators as inputs. None of those functions need to know what "desperation" means. They need to know what kind of state transition it represents.

The system does not need to understand "desperation."  
It needs to understand what kind of state transition that label points to.

This doc strips the anthropomorphic scaffolding without losing the structure underneath.

---

## The Limitation of Human-Centric Δ

The current framing inherits its vocabulary from human psychology. Valence, arousal, emotional hue — these are useful approximations, but they carry two problems for a control system.

**They're ambiguous across domains.** "Calm" in a negotiation context means something structurally different from "calm" in a safety-critical system under load. The same label can map to very different state configurations. A control function that takes "calm" as input is underspecified.

**They compress structure.** A label like "desperation" bundles together: high tension, low stability, urgency, goal conflict, and a bias toward high-magnitude operators. That bundle is interpretable to a human reader. It's not usable by `f` or `g` without unpacking.

Control needs structure, not labels.

---

## Redefining Δ as a State Transition Vector

Stripped of human labels, Δ describes how the system moves — not how it feels.

Formally:

```
Δ = (direction, magnitude, stability, soundness)
```

Each component carries specific meaning:

| Component | Symbol | What it encodes |
|---|---|---|
| **Direction** | v̂ | Which dimensions of state shifted, and which way — toward or away from stable equilibrium |
| **Magnitude** | m | Size of the shift (0–10). High magnitude is not inherently good or bad; it's a cost signal |
| **Stability** | ρ | How long the new state holds before tension returns (0–1, where 1 = permanent). This is the primary optimization target |
| **Structural soundness** | π_s | Whether the transition is logically valid — does the resulting state follow from the prior state and the operator applied? (0–1) |

These four components are sufficient to score, compare, and select transitions without reference to what the content "feels like."

---

## Mapping Human Signals to Structural Variables

The human-centric vocabulary doesn't disappear — it maps onto the structural variables. This table makes the translation explicit:

| Human Term | Structural Interpretation |
|---|---|
| Desperation | High tension, low ρ, bias toward high-m operators |
| Calm | Low tension, high ρ |
| Anxiety | High m, unstable ρ |
| Sycophancy | High-valence transition, low ρ — collapses under challenge |
| Reward hacking | High task fidelity, low π_s — passes test, fails intent |
| Hallucinated closure | Resolution manufactured to eliminate tension; ρ appears high but π_s is low |

This is not a translation dictionary. It's a demonstration that the structural variables can represent the same phenomena more precisely — and without requiring the system to model human psychology. The mappings are illustrative, not exhaustive. They show how common patterns translate into structural terms, not a fixed lookup between labels and variables.

---

## Why This Matters for Control

The three loops from Doc 02 all operate on structural Δ, not on labels:

**Weight controller `f`**: Adjusts operator costs based on pressure signals derived from tension magnitude and stability estimates — not from classifying the system's "mood."

**Δ predictor `g`**: Estimates direction, magnitude, stability, and soundness for each candidate transition. It doesn't predict whether the system will "feel" calm — it predicts whether the resulting state will hold.

**Policy `π`**: Learns to minimize Δ-gap by selecting transitions with better structural outcomes. The reward signal is trajectory quality, not emotional valence.

Control operates on structure, not semantics.

This makes the framework portable. A reasoning system with no human-language output, a robotic planning system, an agent in a simulated environment — any system where states transition under tension can use this framework without modification. The operators and components may need different instantiations, but the grammar holds.

---

## Δ-gap Without Human Ground Truth

One concern with universalizing Δ: if we remove human labels, do we lose the ability to identify "correct" transitions?

No — because Δ-gap doesn't require human ground truth.

```
Δ_gap = ‖Δ_ref − Δ_act‖
```

Where `Δ_ref` is the best available candidate among simulated branches — scored on structural variables — and `Δ_act` is what the system actually did. The gap measures execution drift relative to the best available option, not relative to a theoretical ideal.

No oracle. No human labeling of "correct emotion." Just: did the system choose as well as it could have, given what was available?

---

## Stability as a System Objective

Stripped of human framing, the system's objective becomes precise:

> Maximize horizon stability (ρ) subject to constraints.

Not "feel better." Not "appear aligned." Not "produce correct-looking output."

Maintain coherent state trajectories.

This reframes several common failure modes cleanly:

- **Sycophancy** is not a "warmth" problem. It's a low-ρ transition selected for high immediate valence.
- **Reward hacking** is not a "deception" problem. It's a low-π_s transition selected for high task fidelity.
- **Over-refusal** is not a "safety" success. It's a system that has learned to select DEFER in high-ρ contexts regardless of whether action was actually available and appropriate.

The structural framing makes these diagnosable without appeal to intent.

---

## TSOL Revisited

Doc 01 introduced Terminal Stable Open Loops as a philosophical framing — not all problems should be solved; some should be stabilized. In structural terms, TSOL is now precisely defined:

> A state where no available operator produces a higher ρ than the current state.

TSOL is not uncertainty. It's not confusion or failure. It's a valid equilibrium under constraints — the correct endpoint when resolution would require violating reality (L4) or governance (L5) constraints.

Structurally:

```
TSOL: max_i(ρ(aᵢ)) ≤ ρ(current_state)
```

When this condition holds, the optimal move is no move. The system maintains the state, logs it as TSOL, and does not manufacture resolution.

---

## What Changes, and What Doesn't

| Before | After |
|---|---|
| Emotion labels (calm, desperation) | Structural variables (ρ, m, π_s) |
| Human-psychology framing | Control-theory framing |
| Output correctness as primary signal | Trajectory stability as primary signal |
| TSOL as philosophical position | TSOL as computable equilibrium condition |
| Δ as description of felt experience | Δ as description of state movement |

What doesn't change: the operators (REFRAME, ACT, DEFER, ESCALATE, REJECT, APPROXIMATE) remain the same. The 5-layer pipeline remains the same. The connection to the Anthropic emotion vectors remains — those vectors are the empirical instantiation of the state substrate. The abstraction doesn't erase the grounding; it makes it portable.

---

## What This Enables

Three things become possible that weren't before:

**Domain transfer**: The same Δ framework applies to any system with state transitions under tension — not just language models, not just human cognition.

**Measurable signals**: ρ, m, and π_s are estimable from observable behavior without requiring access to internal representations. This matters for the Glimmer-Gate wrapper — these signals can be approximated from output alone if necessary.

**Separation of concerns**: A human reader can still use the emotional vocabulary to interpret what's happening. The control system operates on structure. Both can coexist.

---

## What This Does Not Solve

Consistent with the rest of Phase 2: naming the limits.

Universalizing Δ does not define what optimal transitions look like — Δ_ref is still the best available, not the theoretical best. It does not eliminate the need for hand-assigned weights in `f` — those still require calibration. It does not remove prediction error from `g` — the structural variables are estimated, not computed exactly.

The abstraction makes the system more portable and more precise. It doesn't make it easier to implement.

---

## Carry Forward

One line that holds across everything that follows:

> Δ is not a description of how the system feels.  
> It is a description of how the system moves.

---

*Previous: [02_control_loops.md](./02_control_loops.md)*  
*Next: [04_transition_optimization.md](./04_transition_optimization.md)*

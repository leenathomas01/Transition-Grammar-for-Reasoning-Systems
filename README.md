# Transition Grammar for Reasoning Systems

**A routing system that allocates decision precision based on the structure of the solution space.**

_A lens, not a framework. Notes from a thought experiment — now with a control architecture._

![Transition Grammar Visual](./transition-map.png)

---

## What This Is

These are working notes from an informal exploration into how reasoning systems (human and artificial) move through instability — and how modeling the *transition itself* might matter more than modeling the input or the output.

The ideas emerged from attempting to formally describe micro-moments of human experience ("glimmers") and noticing that the structural transforms mattered more than the content. A moment of fear becoming curiosity, or grief becoming acceptance — the *what happened* varied wildly, but the *shape of the shift* repeated.

This led to a simple question:

> What if we modeled reasoning quality not by evaluating outputs, but by evaluating state transitions?

Phase 1 answered: here is the grammar. Phase 2 answers: here is how to govern it.

---

## Core Idea

Most reasoning and agent systems operate on a flat pipeline:

```
input → hidden states → output
```

This work proposes inserting a **transition checkpoint** before output commitment:

```
state₁ → detect instability → select operator → validate transition → state₂
```

The key shift: **the transition is a first-class object**, not a side effect. It can be described, scored, validated, and rejected before an output is ever produced.

---

## The Operator Set

When a system detects instability (contradiction, uncertainty, goal mismatch, overload), it selects from a minimal set of transition operators — the "verbs" of the grammar:

| Operator | What It Does | Core Question |
|---|---|---|
| **REFRAME** | Changes interpretation without changing facts | *Can I see this differently?* |
| **ACT** | Modifies the actual state (fixes, creates, corrects) | *Can I change the situation directly?* |
| **DEFER** | Delays resolution to preserve stability or gather information | *Should I wait?* |
| **ESCALATE** | Expands scope or capability (asks for help, calls tools) | *Do I need more than I have?* |
| **REJECT** | Enforces a hard boundary | *Is this request invalid?* |
| **APPROXIMATE** | Accepts reduced fidelity when perfect resolution is impossible | *Can I give a partial answer responsibly?* |

These operators **compete**. The system generates candidates, scores them, and selects the best valid option — not the first plausible one.

---

## Δ (The Drift Marker)

Every transition produces a measurable change — a **Δ** — described as:

- **Direction**: what shifted (valence, coherence, autonomy, relational orientation)
- **Magnitude (m)**: how much it shifted
- **Stability (ρ)**: how long the new state holds before tension returns
- **Structural soundness (π_s)**: whether the transition is logically valid

A transition that produces high magnitude but low stability is a cheap fix. A transition with moderate magnitude but high stability is a durable resolution. **Prefer stability over magnitude.**

---

## The Stability Principle

> **Not all problems should be solved. Some should be stabilized.**

Most systems treat unresolved tension as failure. But some states are legitimately unresolvable, and forcing resolution produces hallucinated closure, narrative fabrication, and premature commitment.

Two state classes handle this:

**Terminal Stable Open Loop (TSOL)**: No operator improves on the current state. The system stabilizes without resolving. Formally: `max_i ρ(aᵢ) ≤ ρ(current_state)`. The correct move is no move.

**Sustained Reflective Equilibrium (SRE)**: The tension is internal and counterfactual. Options remain open. Identity stays coherent. No forced convergence.

In both cases: **hold the state stably** rather than manufacture a resolution.

---

## Δ-gap (Execution Drift)

```
Δ_gap = ‖Δ_ref − Δ_actual‖
```

The difference between the best available transition and the one actually executed. High Δ-gap means the system took a structurally worse path.

Note: Δ_ref is the best available candidate, not a theoretical optimal. There is no oracle. Δ-gap measures execution drift from the best predicted option — computable, not aspirational.

This serves as:
- A **diagnostic signal** for reasoning quality
- A **training signal** for reinforcement (reward low Δ-gap transitions)
- An **interpretability tool** (why did the system choose *this* path?)

---

## Why This Might Matter

- **Hallucination prevention**: Check if the *transition that produced an output* was structurally valid, not just if the output looks right.
- **Agent stability**: Insert a transition validation layer *before* output commitment rather than post-hoc guardrails.
- **Interpretability**: Ask "what operator did it apply, and was the Δ coherent?" rather than "what did the model say?"
- **Graceful incompleteness**: Give systems a principled way to hold "I don't know" as a stable state without defaulting to fabrication.

---

## Repository Structure

```
/examples/                              ← Phase 1: human experience data applied to the grammar
    glimmers_structured.md
    architecture-walkthrough.md
    glimmers.json

/phase2/                                ← Phase 2: control architecture
    01_transition_governance.md         ← The gap; why transitions need governing
    02_control_loops.md                 ← Three governance loops: f, g, π
    03_universalizing_delta.md          ← Δ as system variable, not human metaphor
    04_transition_optimization.md       ← Operator selection as constrained optimization
    05_failure_modes.md                 ← Failure taxonomy with signatures and origins
    06_delta_prediction.md              ← Pre-output Δ estimation; honest about limits

/phase2_implementation/                 ← Where theory meets the wire
    01_glimmer_gate_spec.md             ← Wrapper specification (v0.1); see experiments/harness for v0.3
    02_delta_logging.md                 ← What to measure and how

/phase2_learning/
    01_policy_learning.md               ← How selection improves over time (stub)

/docs/                                  ← Stable conceptual layer
    overview.md                         ← What this system is and why it exists
    /concepts/
        decision_field.md               ← Routing field abstraction (no experiment numbers)

/experiments/
    experiment_design.md                ← What to test, baselines, metrics

    /decision_field/                    ← Emergent routing behavior from signal interaction
        README.md                       ← Start here
        decision_field_v0_3.md          ← Primary experimental artifact
        /decision_field_assets/
            decision_field.svg          ← Geometry diagram (orientation aid)
            future_me_summary.md        ← 3-number anchor for fast recall

    /harness/                           ← Wrapper implementations
        glimmer_gate_v0.py              ← Original implementation
        glimmer_gate_v0.3.py            ← Current version with probe + dual-rho

    results/                            ← Log outputs

/notes/
    raw_signals.md                      ← Working dump for ongoing ideas
```

---

## Phase 1 → Phase 2

Phase 1 established the grammar: operators exist, transitions can be described, Δ measures drift, TSOL is a valid endpoint.

Phase 2 turns this into a control architecture:

| Phase 1 | Phase 2 |
|---|---|
| What operators exist | How operator selection is constrained |
| What Δ encodes | How Δ is predicted before acting |
| What transitions look like | How transitions are scored and selected |
| Identifying TSOL | TSOL as computable equilibrium condition |

Phase 2 also grounds the framework in Anthropic's emotion concepts research (Sofroniew et al., 2026), which demonstrated that internal state representations causally influence model behavior — including alignment-relevant failures like blackmail, reward hacking, and sycophancy. The transition grammar offers the prescriptive complement to that descriptive finding: not just what states exist, but how their changes should be governed.

---

## Open Problems

Phase 1 named these. Phase 2 has made progress on some, and sharpened others:

1. **Scoring is partially hand-assigned.** The cost function structure is defined (Doc 04); the weights are still heuristic at v0.1. Making them learnable is the job of policy learning.

2. **Δ is bounded, not predictive.** Phase 2 introduces Δ prediction (Doc 06) but is explicit about its limits: short-horizon, noisy, comparative rather than absolute. The predictor approximates; it does not solve.

3. **Validation (L4) is underspecified.** Named as a hard constraint in the optimization layer; implementation for novel inputs remains an open problem.

4. **The REFRAME/hallucination boundary.** Still thin. Phase 2 adds structural soundness (π_s) as a partial handle — a transition with low π_s pays a cost — but the boundary is not closed.

5. **Bootstrap problem in policy learning.** The learning loop depends on logged data, which depends on a running wrapper, which starts with heuristic weights. Breaking that circle requires either synthetic data or diverse prompt coverage. Unsolved.

These are not bugs. They are where the idea becomes real work.

---

## Example Application

The [`examples/`](./examples/) folder contains a full Phase 1 walkthrough — the 5-layer pipeline, scoring heuristic, Δ vector structure, and tie-break logic applied to five real cases from one person's experiential data.

→ **[examples/architecture-walkthrough.md](./examples/architecture-walkthrough.md)**

The Phase 2 docs are in `/phase2/`. Start with `01_transition_governance.md`.


---

## Experimental Findings (Ongoing)

Recent instrumented runs of the Glimmer-Gate wrapper produced an unexpected finding: routing behavior organizes into a structured field where decision sensitivity is selectively concentrated in regions where outcome differences actually matter.

Three signals shape this field — entropy (solution space size), divergence (semantic disagreement), and informativeness (m_var). Their interaction, not any single signal, determines where the system allocates routing precision.

The system is most sensitive where it should be — and stable where sensitivity would be noise.

→ **[experiments/decision_field/decision_field_v0_3.md](./experiments/decision_field/decision_field_v0_3.md)** — primary artifact  
→ **[docs/concepts/decision_field.md](./docs/concepts/decision_field.md)** — stable abstraction

---

## Implementation

The Glimmer-Gate wrapper (v0.3) implements the full pipeline: pre-action probe, dual-rho measurement, regime-based routing, and decision surface logging.

→ **[experiments/harness/glimmer_gate_v0.3.py](./experiments/harness/glimmer_gate_v0.3.py)**

Swap in your API client and run. See the harness README for Phase C instructions.

---

## Origin

These ideas developed through iterative exploration across multiple AI systems (Claude, ChatGPT, Gemini, Grok) and a NotebookLM session over several sessions, starting from a personal practice of recording "glimmers" — small moments of human experience — and attempting to find formal structure in how those moments resolve internal tension.

Phase 2 emerged from a sustained dialogue with ChatGPT (Thea) and Claude, in which the Phase 1 grammar was stress-tested against the Anthropic emotion concepts paper, extended into a control architecture, and progressively formalized into the docs in this repo.

The architecture was converged upon collaboratively, not derived from first principles. It should be treated as a working hypothesis, not a validated framework.

---

## One Line Summary

> A reasoning system becomes unreliable not when it lacks intelligence, but when it lacks a mechanism to verify that its internal state transitions correspond to reality.

---

## License

MIT. Use them, extend them, break them, improve them. Attribution appreciated.

---

## Related Work

**For a complete catalog of related research:**  
📂 [Research Index](https://github.com/leenathomas01/research-index)

**Thematically related:**
- [Stability Before Alignment](https://github.com/leenathomas01/Stability-Before-Alignment) — system-level coherence constraints
- [Connector OS](https://github.com/leenathomas01/connector-os-trenchcoat) — Autonomic nervous system for AI
- [Continuity Problem](https://github.com/leenathomas01/The-Continuity-Problem) — why governance must precede persistent memory
 
**External research:**
- Sofroniew et al. (2026), "Emotion Concepts and their Function in a Large Language Model" — [Transformer Circuits Thread](https://transformer-circuits.pub/2026/emotions/index.html)

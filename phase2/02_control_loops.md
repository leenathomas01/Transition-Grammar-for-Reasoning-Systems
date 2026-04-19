# Control Loops
### Phase 2 — Doc 02

*Part of [Transition Grammar for Reasoning Systems](../README.md)*

---

## From Description to Control

Doc 01 established the gap: transitions are implicit, and implicit transitions can't be governed.

This doc outlines how control can happen — not as post-hoc guardrails, but as governance woven into the transition process itself.

The full transition loop looks like this:

```
observe state
    ↓
detect instability
    ↓
incorporate environment signals
    ↓
generate candidate operators
    ↓
[control layer]
    ↓
apply constraints (L4/L5)
    ↓
select transition
    ↓
emit output
    ↓
observe actual Δ → update
```

The control layer — the bracketed step — is what Phase 1 left underspecified. It contains three interacting loops. Each one governs a different aspect of transition selection.

---

## The Three Loops

### Loop 1 — Weight Control

**The problem it solves**: Under pressure, objective weights drift. When a system is "desperate" (high tension, failing tests, approaching a deadline), the weight on task completion rises implicitly while the weight on stability falls. The system selects high-magnitude, low-ρ transitions — cheap fixes that pass the immediate test but won't hold.

This is not a values failure. It's a control failure. The objective function is being modified by the system's internal state without governance.

**The mechanism**: A weight controller `f` that takes current state, pressure level, and environment as inputs and returns adjusted weights:

```
w = f(s, pressure, environment)
```

Where pressure is derived from observable signals: uncertainty, goal conflict, entropy, or tension magnitude. The controller raises the cost of high-magnitude operators (ACT, ESCALATE) under pressure and lowers the relative cost of DEFER — not by banning operators, but by making the stable path cheaper to select.

**The key constraint**: DEFER is cost-weighted, not forced. High pressure increases ACT's cost. DEFER wins through competition, not mandate. This preserves usefulness and avoids the concealment problem — a system forced to defer learns to hide tension rather than process it.

**Current status**: The weighting function `f` is currently hand-assigned. Making it learnable — responsive to context without human priors — is an open problem. See `04_transition_optimization.md` for the cost function structure.

---

### Loop 2 — Δ Prediction

**The problem it solves**: Δ is currently descriptive. We measure drift after a transition executes. For control to happen *before* output commits, the system needs to estimate Δ in advance — to predict, for each candidate operator, what the resulting state shift will look like.

Without this, transition selection becomes effectively blind. The system picks an operator, executes it, and then discovers whether the result was stable. That's reactive, not governed.

**The mechanism**: A prediction model `g` that takes current state and a candidate operator as inputs and returns an estimated Δ:

```
Δ̂ᵢ = g(s, aᵢ)
```

This is approximate. The goal is not perfect prediction but directional signal — enough to rank candidates before committing.

**The practical hook**: The Anthropic emotion paper (2026) identified that the "colon token" immediately before the model's response is highly predictive of the upcoming response's emotional trajectory (r=0.87). This is evidence that a predictive window exists in the model's internal state — a moment where trajectory is partially determined but not yet committed. Intercepting at this point and running short candidate rollouts gives an approximate `g` without architectural changes.

Framed carefully: the colon token is a *proxy* for the predictive window, not the mechanism itself. See `06_delta_prediction.md` for the full treatment.

**Current status**: `g` does not yet exist as a formal model. The immediate approximation is: generate short rollouts (20-30 tokens) per candidate operator, score each for stability (consistency across samples), soundness (agreement with retrieval or self-check), and cost. This is computable today.

---

### Loop 3 — Policy Learning

**The problem it solves**: Operator selection is currently heuristic. Weights are hand-assigned, scoring is approximate, and the "best" transition is estimated rather than learned. Over time, a system should be able to improve operator selection based on observed outcomes.

**The mechanism**: The Δ-gap — the difference between the best available transition and the one actually executed — serves as a training signal:

```
R = −Δ_gap
```

Where `Δ_gap = ‖Δ_ref − Δ_act‖` and `Δ_ref` is the best candidate among simulated branches (not a theoretical optimal — that's still undefined). Low Δ-gap means the system took a structurally sound path. High Δ-gap means it chose worse than it could have.

This shifts reinforcement from output correctness to trajectory quality. Instead of rewarding "produced a helpful-looking answer," the system is rewarded for selecting operators that lead to durable states.

**The important distinction**: Δ_ref is not Δ_opt. There is no oracle for optimal transitions. Δ_ref is simply the best available candidate — the one that scores highest under the current scoring function. This makes the gap computable without requiring ground truth.

**Current status**: Policy learning is the most forward-looking of the three loops. The Δ-gap logging infrastructure (see `02_delta_logging.md` in `/phase2_implementation/`) is the necessary first step — you can't learn from a signal you're not recording.

---

## How the Loops Interact

The three loops are not independent. They operate at different timescales and feed into each other:

```
Weight control (f)     — fast, per-inference adjustment
Δ prediction (g)       — medium, per-candidate estimation  
Policy learning (π)    — slow, cross-session improvement
```

Under pressure, `f` adjusts weights before candidates are evaluated. `g` estimates outcomes for each candidate under those weights. `π` updates based on what actually happened vs. what was predicted.

The key interaction to watch: if `f` is too aggressive (weights collapse toward DEFER under any pressure), `g` will consistently predict high stability for deferral, and `π` will reinforce over-caution. The loops amplify each other — which means a miscalibrated `f` can corrupt the whole system over time.

Concrete example: pressure spikes on a difficult task, so `f` raises the cost of ACT and biases toward DEFER. `g` then predicts high stability for deferral across candidates. `π`, observing low Δ-gap from repeated deferrals, reinforces this pattern. Over time, the system learns to defer even when action is appropriate — not because it lacks capability, but because the control loop has converged on over-caution.

This is the "controller stability" problem flagged as open in the Thea/NotebookLM exploration. It doesn't have a solution yet. It's named here so it doesn't get lost.

---

## The Integrated Loop

With all three active, the full transition process is:

```
1. Observe state s
2. Compute pressure signal P
3. Adjust weights: w = f(s, P, env)
4. Generate candidate operators {aᵢ}
5. For each candidate: Δ̂ᵢ = g(s, aᵢ)
6. Score each: Cᵢ = score(w, Δ̂ᵢ)
7. Apply hard constraints (L4: reality, L5: governance)
8. Select: argmin Cᵢ among valid candidates
9. Execute → observe actual Δ
10. Compute Δ_gap = ‖Δ_ref − Δ_act‖
11. Log; update π
```

This is the governed reasoning loop. Outputs are no longer the primary object of control — trajectories are.

---

## What This Is Not

This is not a production specification. The three loops exist at different levels of readiness:

- Weight control: conceptually specified, not formally learned
- Δ prediction: approximable with current tools, not yet implemented
- Policy learning: direction clear, dataset doesn't exist yet

This doc describes the architecture. The implementation pathway starts in `/phase2_implementation/`.

---

## Open Problems (Explicit)

Three problems are known, named here so they don't get papered over:

**1. Controller stability**: A miscalibrated weight controller can corrupt downstream prediction and learning. How to bound `f` so it doesn't over-correct is unsolved.

**2. Δ prediction accuracy**: Short rollouts give noisy estimates. How many samples are needed for reliable ranking? How sensitive is selection quality to prediction error? Unknown.

**3. Bootstrap problem**: Policy learning requires Δ-gap data. Δ-gap data requires running the wrapper in the loop. The wrapper requires a scoring function. The scoring function currently uses hand-assigned weights. Breaking this circle requires either synthetic data or a principled initialization strategy.

These are not reasons to stop. They're reasons to log carefully.

---

*Previous: [01_transition_governance.md](./01_transition_governance.md)*  
*Next: [03_universalizing_delta.md](./03_universalizing_delta.md)*

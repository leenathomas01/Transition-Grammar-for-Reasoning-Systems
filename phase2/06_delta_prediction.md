# Δ Prediction
### Phase 2 — Doc 06

*Part of [Transition Grammar for Reasoning Systems](../README.md)*

---

## Why Prediction Matters

Doc 04 defined how transitions are selected.  
Doc 05 defined how that process fails.

Both depend on one assumption:

The system can estimate the outcome of a transition before executing it.

This doc examines that assumption — not whether Δ can be known perfectly (it cannot), but whether it can be estimated well enough to guide selection.

---

## What Δ Prediction Is (and Is Not)

Δ prediction is not predicting the exact future state.

It is estimating, for each candidate operator, the likely:

- **direction** of state shift — toward or away from stability
- **magnitude (m)** — size of the shift
- **stability (ρ)** — how long the resulting state holds
- **structural soundness (π_s)** — whether the transition is valid

Formally:

```
g(s, aᵢ) → (Δ̂ᵢ, m̂ᵢ, ρ̂ᵢ, π̂_sᵢ)
```

Where `g` is the predictor and `s` is current state.

The system does not need perfect accuracy. It needs useful ranking between candidates — enough to prefer a more stable transition over a less stable one before committing.

---

## Where the Signal Comes From

Δ prediction draws on signals already present in the model. Three sources:

---

### 1. The Pre-Output State

There is a point before output generation where the model has internally committed to a trajectory but not yet emitted tokens. The Anthropic emotion paper (2026) identified this empirically: activations at the ":" token following "Assistant" correlate with the emotional trajectory of the upcoming response at r=0.87.

This is not persistent internal state. It is a prepared state snapshot — the model's internal configuration at the moment it begins generating, before the trajectory is externally visible.

Framed carefully: this is evidence that a predictive window exists, not a specification of the mechanism. The colon token is a proxy for intercepting that window, not the window itself.

---

### 2. Activation Geometry

Internal representations contain linear directions corresponding to tension profiles and behavioral tendencies — high vs. low instability, escalation vs. deferral patterns. These are not "emotions" in a human sense. They are latent gradients the model uses to navigate output space.

Δ prediction reads these gradients. For a given candidate operator, projecting through these directions gives a directional signal about where the transition is headed — toward or away from stable states.

---

### 3. Short-Horizon Rollouts

For each candidate operator, the system generates a short continuation (20–30 tokens), samples it 2–3 times, and observes the resulting activations and consistency.

This is not full simulation. It is a bounded probe of trajectory direction:

- **Stability estimate (ρ̂)**: agreement across samples — consistent outputs suggest stable trajectory; high variance suggests instability
- **Soundness estimate (π̂_s)**: agreement with retrieval, self-check, or consistency with prior context
- **Magnitude estimate (m̂)**: shift in latent activation norms relative to current state

Expensive, but can be approximated with limited sampling.

---

## How Prediction Is Used

Prediction feeds directly into the optimization layer (Doc 04):

```
C(aᵢ) = score(w, Δ̂ᵢ)
       = w_ρ(1 - ρ̂ᵢ) + w_m(m̂ᵢ) + w_π(1 - π̂_sᵢ) + w_E(Eᵢ)
```

Prediction does not decide. It shapes the cost landscape. The optimization selects; prediction informs what the optimization is selecting over.

This separation matters: a wrong prediction produces a bad cost estimate, which produces a bad selection. But the failure is localized and observable — it shows up as Δ-gap after execution.

---

## The Limits of Prediction

Named explicitly. None of these are reasons to abandon prediction; they are reasons to log carefully.

**Locality**: Representations are locally scoped. The predictor sees near-term trajectory, not long-term stability. ρ̂ is always an approximation — and an optimistic one. Short rollouts look stable more often than they are.

**Horizon mismatch**: Short rollouts cannot capture delayed instability or second-order effects. This is the direct mechanism behind Cheap Path Selection (Doc 05): the system selects what looks stable at 20 tokens and discovers the collapse at 200.

**Context sensitivity**: Predictions depend on prompt framing, recent tokens, and latent state noise. Small input changes can produce meaningfully different Δ̂. This makes prediction unreliable as a standalone signal — it needs to be used comparatively (ranking candidates) rather than absolutely (trusting a specific ρ̂ value).

**No ground truth**: There is no Δ_opt. Prediction is evaluated by divergence from what actually happened, not correctness against a known answer. This is what makes Δ-gap the right evaluation metric — it measures realized error, not theoretical distance from optimal.

Prediction errors do not just affect accuracy — they reshape the optimization landscape and therefore the selected behavior. A systematically wrong predictor doesn't just miss occasionally; it consistently biases the system toward structurally inferior transitions.

---

## Measuring Prediction Quality

Prediction quality is tracked through Δ-gap:

```
Δ-gap = ‖Δ_act − Δ̂_ref‖
```

Where `Δ̂_ref` is the predicted Δ for the selected candidate — the estimate that drove selection.

Three useful signal types:

**Bias**: Consistent over- or underestimation of specific operators. If DEFER is systematically predicted as more stable than it is, weight controller `f` will over-select it.

**Variance**: Instability of predictions across similar contexts. High variance in ρ̂ estimates for similar inputs suggests the predictor is sensitive to noise it shouldn't be.

**Collapse cases**: High-confidence predictions that fail catastrophically — the predicted ρ̂ is high, the actual ρ is low, and the Δ-gap spikes. These are the most important cases to log and examine.

All three feed policy learning (Doc 02, Loop 3). The predictor improves through accumulated Δ-gap data — but only if it's being collected.

---

## Prediction Failure Modes

Prediction introduces specific failure patterns (linking to Doc 05):

- **Underestimating instability** → Cheap Path Selection. The system selects a transition that looks stable at short horizon and collapses later.
- **Systematic bias toward certain operators** → repeated misselection in predictable contexts. Surfaces in Δ-gap clustering.
- **Blind spots for specific transition types** → operator-specific failure. The predictor is accurate for REFRAME but unreliable for ESCALATE.
- **Overconfidence** → large Δ-gap spikes. High π̂_s predictions that fail L4 validation after selection.

Prediction does not eliminate failure. It makes failure measurable earlier in the pipeline than output inspection alone.

---

## What Works Today

Δ prediction is not fully solved. The partial approximations available now:

| Method | What it provides | Limitation |
|---|---|---|
| Activation probing | Directional signal toward/away from instability | Requires interpretability access |
| Short rollout sampling | Stability and consistency estimates | Expensive; short horizon only |
| Classifier-based scoring | Fast stability proxy | Requires labeled training data |
| Heuristic operator ranking | Baseline ranking without prediction | No Δ signal, purely rule-based |

These are sufficient for: ranking candidates, avoiding obvious failure modes, logging Δ-gap for future learning.

They are not sufficient for: guaranteed stability, long-horizon control, or eliminating prediction error.

The honest summary: current prediction is noisy and bounded. It is still more useful than no prediction — which is selection without any cost signal on trajectory quality.

---

## Prediction Without Architecture Changes

Δ prediction can be implemented as an external control layer, not internal model redesign:

The prediction loop operates entirely outside the base model:

```
1. Intercept pre-output state (hook before first token)
2. Generate candidate continuations per operator prompt
3. Sample 2–3 times per candidate
4. Extract stability, soundness, magnitude proxies
5. Feed estimated Δ̂ into cost function
6. Select; emit; log actual Δ_act
```

The base model is unchanged. The prediction layer wraps it. This is the architecture Glimmer-Gate implements — see `/phase2_implementation/01_glimmer_gate_spec.md`.

---

## Relationship to the Wrapper

Glimmer-Gate uses Δ prediction for three specific functions:

- **Pre-output evaluation**: score candidates before committing to generation
- **Cost function input**: estimated (ρ̂, m̂, π̂_s) feed directly into C(aᵢ)
- **Δ-gap logging baseline**: Δ̂_ref is recorded alongside Δ_act for every run

The wrapper does not require accurate prediction. It requires consistent relative estimates — that the better candidate reliably scores lower cost than the worse one, even if the absolute values are noisy. That bar is achievable with the approximations above.

---

## What This Does Not Solve

- Perfect foresight of transition outcomes
- Long-horizon stability guarantees  
- Elimination of the horizon mismatch problem
- Global optimality of candidate selection

The system remains reactive, not omniscient. Prediction extends the horizon slightly and makes trajectory quality observable. That is the limit of what it claims.

---

## Carry Forward

> The system does not need to know the future.  
> It needs to avoid obviously bad ones.

Δ prediction enables that — imperfectly, bounded, and honestly.

---

*Previous: [05_failure_modes.md](./05_failure_modes.md)*  
*Next: [phase2_implementation/01_glimmer_gate_spec.md](../phase2_implementation/01_glimmer_gate_spec.md)*

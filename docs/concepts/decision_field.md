# Decision Field
### Concepts — Stable Abstraction

*Part of [Transition Grammar for Reasoning Systems](../../README.md)*

---

## The Core Idea

When a reasoning system selects between transition operators, it does not need to directly estimate which operator is best. It can instead estimate *where* the choice between operators matters most — and allocate precision there.

This is a different computational stance:

```
Classifier stance:  input → best action
Decision field:     input → where precision matters → act accordingly
```

The distinction sounds subtle. The behavioral consequences are not.

---

## Three Signals

The routing field emerges from three measured properties of a candidate set:

**Entropy** — how many distinct solution paths exist for this prompt. A high-entropy task admits many valid approaches; a low-entropy task has a narrow, constrained response space.

**Divergence** — how much candidate responses actually disagree in meaning. Entropy and divergence can decouple: many approaches may exist but converge on the same answer, or few approaches may exist but produce meaningfully different outputs.

**Informativeness (m_var)** — how much variation in depth and richness exists across candidate samples. Low informativeness suggests candidates are converging on shallow or generic outputs regardless of which operator produced them.

These signals are:
- empirically independent of each other
- smoothly interacting (no thresholds required)
- sufficient to produce structured routing behavior

---

## Three Regimes

The routing field naturally organizes into three behavioral zones:

**Determined regime**: entropy and divergence strongly disagree — one dominates. Routing is stable and predictable. The system follows the dominant axis.

**Competitive regime** (the "soft ridge"): entropy and divergence are balanced. This is where the routing field has highest curvature — small changes in informativeness produce meaningful routing shifts. This is not noise; it is where the system is most sensitive to genuine differences in solution quality.

**Transitional regime**: smooth decay between the above. Moderate sensitivity, influence shifting.

![Decision Field](https://github.com/leenathomas01/Transition-Grammar-for-Reasoning-Systems/blob/main/decision-field-for-AI-reasoning-system.png)

*Orientation aid — not a literal map. The field is continuous and probabilistic.*

---

## The Soft Ridge

The most important structural feature of the field is the soft ridge — the region where entropy and divergence are in equilibrium.

Three properties of this region:

1. **High curvature**: small changes in informativeness produce large routing changes
2. **Structured sensitivity**: these routing changes correspond to meaningful differences in output quality, not measurement noise
3. **Suppressed elsewhere**: outside the ridge, the system is stable and unresponsive to small perturbations

The ridge is not a boundary. It is a curved, high-gradient surface — a continuous field, not a decision tree.

---

## What Informativeness Does

Informativeness (m_var) is not a global gate. It does not uniformly override the other signals.

Its influence is *contextual*: it becomes the dominant resolution signal specifically when entropy and divergence are balanced. When they strongly disagree, informativeness fades to background.

This produces a conditional dominance hierarchy:

```
If entropy ≠ divergence:   follow the dominant axis
If entropy ≈ divergence:   m_var resolves the tie
```

But even this is a simplification. The more precise statement:

> Informativeness contribution weight increases as the disagreement between entropy and divergence decreases — continuously, not as a switch.

---

## Selective Sensitivity

The routing field is selectively sensitive:

- High responsiveness where small changes correspond to meaningful differences in outcome quality
- Suppressed responsiveness where such differences do not affect outcomes

This is not just correlation — it has been observed that routing changes in high-curvature regions correspond to semantically meaningful shifts, while routing changes in low-curvature regions are approximately chance.

---

## What This Is Not

This is not a classifier. There are no fixed boundaries.

This is not a weighted scoring function. The signal weights shift contextually.

This is not optimizing for stability. Stability is a property that emerges in the determined regime; the competitive regime is intentionally sensitive.

This is not a decision tree. The behavior is continuous across the space.

---

## Relationship to the Operator Grammar

The decision field does not replace the operator grammar (REFRAME, ACT, DEFER, ESCALATE, REJECT, APPROXIMATE). It determines *how* operators compete.

The field operates upstream of operator selection:

```
prompt → measure signals → identify regime → route to operator
```

In the determined regime, routing follows the dominant axis reliably. In the competitive regime, the system allocates additional precision to resolve the choice — using informativeness as the resolution axis.

---

## Status and Limits

This concept is grounded in experimental findings but is not fully validated. The geometry has been observed on controlled prompt sets. Whether it persists across different models, large-scale distributions, or adversarial conditions is an open question.

For empirical grounding and specific numbers, see:  
→ [`/experiments/decision_field/decision_field_v0_3.md`](../../experiments/decision_field/decision_field_v0_3.md)

Do not treat this abstraction as a finalized mechanism. It describes observed behavior, not proven architecture.

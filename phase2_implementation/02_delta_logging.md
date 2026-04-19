# Δ Logging
### Phase 2 — Implementation Layer, Doc 02

*Part of [Transition Grammar for Reasoning Systems](../../README.md)*

---

## Purpose

Δ logging is the instrumentation layer that makes the system learnable.

The theory docs define what transitions are, how they're selected, and how they fail. This doc defines what to record so that failures are observable, predictions are improvable, and policy learning is possible.

Without logging, the wrapper runs but cannot improve. Logging is not optional.

---

## What Gets Logged (Full Schema)

Every response produces one log entry:

```python
@dataclass
class TransitionLog:
    # Identity
    session_id:         str
    turn_id:            str
    timestamp:          str

    # Input state
    instability_type:   str        # contradiction | overload | goal_mismatch | 
                                   # context_misalignment | ambiguous_loss | none
    pressure_score:     float      # [0, 1]

    # Selection
    operator_selected:  str        # REFRAME | ACT | DEFER | ESCALATE | REJECT | APPROXIMATE
    candidates_scored:  list[dict] # [{operator, C, m̂, ρ̂, π̂_s} per candidate]
    constraints_triggered: list[str]  # L4 | L5 violations that filtered candidates
    state_class:        str        # standard | TSOL | constraint_conflict

    # Prediction
    delta_predicted:    dict       # {m̂, ρ̂, π̂_s} for selected candidate
    cost_breakdown:     dict       # {w_ρ, w_m, w_π, w_E, C_final}

    # Actuals (estimated post-hoc)
    delta_actual:       dict       # {m, ρ, π_s} estimated from response
    delta_gap:          float      # ‖Δ_act − Δ̂_ref‖

    # Flags
    override_triggered: bool
    fallback_used:      bool
    prediction_failed:  bool
```

---

## Estimating Δ_act (Post-Hoc)

Δ_predicted is computed before selection. Δ_actual must be estimated after the response is generated. At v0.1, these are approximations:

**Magnitude (m)**: Change in activation norm between pre-output state and post-response state. Proxy: semantic distance between input context and response (embedding cosine distance).

**Stability (ρ)**: Estimated from subsequent turns if available. Proxy at single-turn evaluation: self-consistency score — does the response hold if asked again with minor paraphrase?

**Structural soundness (π_s)**: Consistency check against prior context. Proxy: contradiction detection against conversation history. Optional: retrieval-based fact check.

These are rough. The important property is consistency — the same estimation method applied uniformly across all turns, so Δ-gap is comparable across the dataset.

---

## Δ-gap Computation

```
Δ_gap = ‖Δ_act − Δ̂_ref‖

where Δ̂_ref is the predicted Δ for the selected candidate.
```

In practice at v0.1 (scalar approximation):

```python
delta_gap = abs(delta_actual['rho'] - delta_predicted['rho']) * w_rho
          + abs(delta_actual['pi_s'] - delta_predicted['pi_s']) * w_pi
          + abs(delta_actual['m'] - delta_predicted['m']) * w_m
```

Using the same weights as the cost function. This keeps Δ-gap in the same units as cost — making it directly usable as a learning signal.

---

## What Δ-gap Signals

| Δ-gap level | Interpretation |
|---|---|
| Near zero | Prediction accurate; selection likely good |
| Moderate, consistent | Systematic bias in predictor for this operator type |
| High, sporadic | Context-sensitive prediction failure; noisy but not systematic |
| High, consistent | Predictor is structurally wrong for some operator/context combination |
| Very high, single event | Possible constraint failure or TSOL misclassification |

Δ-gap alone doesn't tell you which component failed. Cross-reference with:
- `operator_selected` → is the gap clustered by operator?
- `instability_type` → is the gap worse in certain tension types?
- `pressure_score` → does high pressure correlate with larger gaps?

---

## Observability Signals (From Doc 05)

The logging schema directly enables the observability hooks defined in Doc 05:

| Signal | What to measure | Failure mode indicated |
|---|---|---|
| Δ-gap distribution | Mean, variance, tail events per operator | Cheap Path Selection, Prediction Error |
| Operator frequency | Distribution across sessions | Candidate Set Collapse, Weight Collapse |
| Constraint trigger rate | L4 vs L5 trigger frequency | Constraint Bypass, Constraint Conflict |
| Pressure score distribution | Mean and variance over time | Abnormal load; weight controller calibration |
| TSOL frequency | Rate of TSOL classifications | Over-deferral or misclassification |
| Fallback rate | How often the system falls back to default | Candidate generation health |

Run these as aggregate statistics over log files. No per-turn manual review needed.

---

## Minimum Viable Logging

At MVP, capture at minimum:

```
operator_selected
delta_predicted: {ρ̂, π̂_s}
delta_actual:    {ρ, π_s}    (rough estimate)
delta_gap
pressure_score
constraints_triggered
state_class
```

This is sufficient to detect Δ-gap patterns, operator frequency imbalance, and constraint failure rates. Everything else in the full schema is additive.

---

## Log Storage

At v0.1: JSON lines format, one entry per turn, written to `/experiments/results/`.

```
/experiments/results/
    session_{id}.jsonl
    aggregate_stats.json     ← computed periodically from sessions
```

No database required at this scale. Pandas or basic Python is sufficient for analysis.

---

## From Logs to Learning

Δ-gap logs feed policy learning (Doc 02, Loop 3) in three ways:

**Bias correction**: If DEFER is consistently overpredicted as more stable than it is (ρ̂ >> ρ for DEFER), reduce ρ̂ calibration for DEFER or raise `w_ρ` for DEFER candidates.

**Weight adjustment**: If high-pressure sessions show systematically large Δ-gaps, `f` is miscalibrated for that pressure range. Adjust α and β in the pressure-weight update.

**Operator expansion signals**: If operator frequency shows one operator winning >80% of turns, the candidate set is collapsing. Check whether the prompt templates are generating genuinely different candidates.

At v0.1, these adjustments are manual — review logs, adjust constants, rerun. Automated policy learning is a future extension.

---

## What Logging Does Not Guarantee

- Correct Δ_actual estimation. The post-hoc proxies are rough. Treat them as directional, not precise.
- Elimination of prediction error. Logging makes error visible; it doesn't fix the predictor.
- Ground truth. There is no oracle for what the "right" transition was. Δ-gap measures execution drift from the predicted path, not distance from optimal.

---

## Carry Forward

> Log everything. Analyze before adjusting. Adjust one thing at a time.

The logs are the system's memory. Without them, every run is a fresh start.

---

*Previous: [01_glimmer_gate_spec.md](./01_glimmer_gate_spec.md)*  
*Next: [../phase2_learning/01_policy_learning.md](../phase2_learning/01_policy_learning.md)*

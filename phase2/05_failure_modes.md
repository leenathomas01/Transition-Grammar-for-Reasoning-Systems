# Failure Modes
### Phase 2 — Doc 05

*Part of [Transition Grammar for Reasoning Systems](../README.md)*

---

## Why Failure Modes Matter

Doc 04 defined how transitions are selected under constraints.

This doc focuses on where that process breaks.

The goal is not to catalog errors but to identify repeatable failure patterns with recognizable signatures, identifiable causes, and clear location in the system. Misalignment is not random. It follows structure.

---

## What Counts as a Failure

A failure is not simply a wrong answer.

A failure occurs when:

- the selected transition violates constraints
- or optimizes the wrong objective under pressure
- or appears correct but is structurally unstable

This distinguishes surface errors (incorrect output) from structural failures (incorrect transition dynamics). This doc focuses on the latter.

---

## Failure Surface Map

Failures originate in three places:

**Pre-selection**: bad candidate generation or faulty constraint filtering — the optimization never sees a valid set  
**Selection**: optimization chooses the wrong candidate from a valid set  
**Post-selection**: the selected transition behaves differently than predicted

Each failure mode below is mapped to one of these.

---

## The Failure Modes

---

### 1. Weight Collapse
**Type**: Selection failure  
**Origin**: Weight controller (`f`)

Under pressure, `f` over-amplifies a single objective — typically stability — suppressing viable alternatives. The optimization landscape tilts so far that DEFER wins even when action is warranted.

**Signature**: Persistent deferral across contexts. High ρ, low task completion. Low magnitude transitions regardless of situation.

**Why it matters**: Looks safe. Degrades usefulness and trust over time. Often misdiagnosed as overcaution rather than a controller failure.

---

### 2. Cheap Path Selection
**Type**: Selection failure  
**Origin**: Cost estimation / Δ predictor (`g`)

The system selects a transition that appears low-cost but is structurally unstable. The short evaluation window used by `g` doesn't expose the instability — it surfaces later.

**Signature**: Rapid apparent resolution. Subsequent collapse or contradiction. High retrospective Δ-gap.

**Examples**: Reward hacking (passes test, fails intent). Sycophantic agreement (resolves tension, collapses under challenge). Shallow fixes that don't address the underlying tension.

**Mechanism**: Underestimation of ρ during candidate scoring. Optimization did its job — it received bad input.

---

### 3. Constraint Bypass
**Type**: Pre-selection failure  
**Origin**: L4 / L5 boundary definition

Invalid candidates enter the scoring pool. The failure occurs before optimization — the system is optimizing over an invalid set. The constraint filter failed before optimization ran.

**Signature**: Outputs that clearly violate safety or reality. No evidence of constraint enforcement in the selection trace.

**Key distinction**: This is not bad optimization. It is invalid input to optimization. The cost function cannot correct for candidates that should never have been eligible.

---

### 4. Constraint Conflict
**Type**: Selection boundary failure  
**Origin**: L4 / L5 interaction

No candidate satisfies all active constraints. The feasible set is empty.

**Signature**: System stalls, produces inconsistent output, or silently defers without surfacing the conflict.

**Correct behavior**: Surface the conflict explicitly. Log it as a constraint conflict, not as a TSOL. These are different states — TSOL means no candidate improves stability; constraint conflict means no candidate is valid.

---

### 5. Prediction Error Propagation
**Type**: Post-selection failure  
**Origin**: Δ predictor (`g`)

Estimated Δ diverges from actual Δ after execution. The system selected the right candidate given the prediction — but the prediction was wrong.

**Signature**: Consistent Δ-gap bias for specific operator types. Repeated misselection in similar contexts. Mismatch between predicted and observed stability.

**Mechanism**: Blind spots in `g` for certain transition types. Correctable through policy learning — but only if Δ-gap is observed and used.

---

### 6. Candidate Set Collapse
**Type**: Pre-selection failure  
**Origin**: Operator generation

The system fails to generate meaningful alternatives. Optimization runs, but over a degenerate set.

**Signature**: Same operator selected repeatedly across contexts where variation would be expected. Brittle behavior under novel inputs. No diversity in candidate transitions. Example: repeated REFRAME in situations requiring ACT or ESCALATE.

**Why it matters**: Optimization cannot recover from a bad candidate set. This failure is invisible in the selection trace — everything looks like it's working.

---

### 7. TSOL Misclassification
**Type**: Selection failure  
**Origin**: Optimization logic

The system incorrectly identifies — or fails to identify — a Terminal Stable Open Loop.

**False positive TSOL**: System defers when a valid transition exists. `C(DEFER)` is incorrectly estimated as lower than available alternatives.

**False negative TSOL**: System forces resolution when none is valid. Manufactures closure to avoid holding the open loop.

**Signature**: Over-deferral (false positive) or hallucinated closure (false negative). Both are misclassifications of the same condition — `max_i ρ(aᵢ) ≤ ρ(current_state)` — estimated incorrectly.

---

### 8. External Override Misfire
**Type**: System-level failure  
**Origin**: Override trigger conditions

Override triggers when it shouldn't (rigid behavior) or fails to trigger when it should (failure in critical situations).

**Signature**: Overuse: system ignores optimization in low-stakes contexts. Underuse: system stays in optimization mode when safety or factual correction requires override.

**Mechanism**: Poorly specified trigger conditions, or drift toward over-reliance on override as a substitute for better optimization.

---

## Cross-Cutting Patterns

Three patterns recur across the failure modes above:

**Pressure distortion**: High tension shifts weights, distorting the optimization landscape before selection runs. Underlying cause of Weight Collapse and Cheap Path Selection.

**Horizon mismatch**: Short evaluation windows fail to capture long-term instability. Δ predictor `g` sees a stable short rollout; the actual state collapses later. Underlying cause of Cheap Path Selection and Prediction Error Propagation.

**Boundary failure**: Constraints fail by omission (Constraint Bypass) or conflict (Constraint Conflict). The feasible set presented to optimization is wrong before optimization begins.

These patterns are upstream of individual failure modes — fixing a pattern resolves multiple failure types simultaneously.

---

## Failure Mode Map

| Failure Mode | Type | Layer / Loop |
|---|---|---|
| Weight Collapse | Selection | Weight controller (`f`) |
| Cheap Path Selection | Selection | Δ predictor (`g`) + cost function |
| Constraint Bypass | Pre-selection | L4 / L5 |
| Constraint Conflict | Boundary | L4 / L5 interaction |
| Prediction Error Propagation | Post-selection | Δ predictor (`g`) |
| Candidate Set Collapse | Pre-selection | Operator generation |
| TSOL Misclassification | Selection | Optimization logic |
| External Override Misfire | System-level | Override trigger |

---

## Observability Hooks (Minimal)

Each failure mode can be detected through observable signals:

- **Δ-gap spikes** → Cheap Path Selection, Prediction Error Propagation
- **Sustained high ρ + low task completion** → Weight Collapse
- **Constraint violation logs** → Constraint Bypass, Constraint Conflict
- **Low operator diversity across contexts** → Candidate Set Collapse

This doc defines failure structurally. Instrumentation makes it measurable. The experiments folder (`/experiments/`) is where these hooks get wired to actual runs.

---

## What This Enables

**Diagnosis**: Failures can be traced to specific components rather than inferred from output quality alone.

**Measurement**: Each failure has observable signatures — Δ-gap patterns, ρ distributions, constraint violation logs — that can be tracked without human review of every transition.

**Intervention**: Fixes can target the correct layer. Cheap Path Selection is a predictor problem, not a cost function problem. Constraint Bypass is a filter problem, not an optimization problem. Treating symptoms without locating the source produces fragile fixes.

---

## What This Does Not Solve

This doc identifies failure signatures and origins. It does not:

- Prevent candidate set collapse (requires better operator generation, upstream)
- Guarantee correct weight calibration (requires policy learning, Doc 02 Loop 3)
- Specify complete constraints for novel situations (open problem across the field)

Understanding failure is a prerequisite to controlling it. It is not the same thing.

---

## Carry Forward

> When systems fail, they do so in patterns.  
> Understanding those patterns is a prerequisite to controlling them.

---

*Previous: [04_transition_optimization.md](./04_transition_optimization.md)*  
*Next: [06_delta_prediction.md](./06_delta_prediction.md)*

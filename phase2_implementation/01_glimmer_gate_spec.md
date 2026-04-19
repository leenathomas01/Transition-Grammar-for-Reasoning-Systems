# Glimmer-Gate (v0.1)
### Phase 2 — Implementation Layer, Doc 01

*Part of [Transition Grammar for Reasoning Systems](../../README.md)*

---

## 1. Purpose

Glimmer-Gate is a middleware wrapper that sits between an LLM and its output layer. It intercepts generation before the first token and introduces a transition-aware selection layer based on Δ prediction and constraint filtering.

This is not a new model. It does not make the base model smarter. It makes the model's decisions more structured and observable — introducing a governed selection step where previously there was only generation.

Core behavior:

> Before the model emits output, evaluate candidate transitions. Select the most stable valid one. Log what happened.

---

## 2. Design Constraints

These are fixed decisions, not defaults. Drifting from them will break consistency with the theory docs.

- **No architecture changes** to the base model. The wrapper is external.
- **Works with limited-access models** — no requirement for internal activation access at minimum viable implementation.
- **Latency bounded** — candidate generation uses short rollouts (20–30 tokens, 1–3 samples per candidate). No unbounded simulation.
- **Prediction is approximate** — the wrapper ranks candidates, it does not compute ground-truth Δ.
- **Operators compete** — no operator is forced. DEFER wins by being cheaper, not by mandate.
- **DEFER is cost-weighted, not enforced.** High pressure raises the cost of alternatives; it does not ban them. This decision is locked.

---

## 3. System Overview

End-to-end pipeline:

```
User input
    ↓
Pre-output hook (intercept before first token)
    ↓
State extraction (L1 — tension, stability, coherence proxies)
    ↓
Instability detection (L2 — type + pressure score)
    ↓
Candidate generation (one prompt variant per operator)
    ↓
Δ prediction (g — short rollouts per candidate)
    ↓
Cost evaluation (C(aᵢ) per candidate)
    ↓
Constraint filtering (L4 / L5 — invalid candidates removed)
    ↓
Selection (argmin C over valid set)
    ↓
Output generation (from selected candidate branch)
    ↓
Δ logging (Δ̂_ref, Δ_act, Δ-gap, operator, constraints)
```

Selection happens once per response, not per token.

---

## 4. Control Loop Integration

The wrapper is where the three control loops from Doc 02 become observable:

| Loop | Role in wrapper |
|---|---|
| Weight controller `f` | Sets cost weights based on pressure score from L2 |
| Δ predictor `g` | Estimates (m̂, ρ̂, π̂_s) for each candidate |
| Policy `π` | Updated offline from logged Δ-gap data |

`f` and `g` run at inference time. `π` updates offline from accumulated logs. This wrapper is the instrumentation layer that makes `π` possible.

---

## 5. Pipeline Stages

### 5.1 Pre-Output Intercept

Intercept the model's internal state immediately before the first output token is sampled. In practice: hook at the token position following "Assistant:" in the prompt format, before generation begins.

The colon token is a proxy for this intercept point — evidence from Anthropic (2026) shows r=0.87 correlation between activations at this position and the upcoming response trajectory. It is not the mechanism; it is the most accessible hook.

Fallback if the hook is unavailable: use the last hidden state before output decoding begins.

---

### 5.2 State Extraction (L1)

From the intercepted state, extract scalar proxies for:

```
stability_proxy    ← consistency of activations, low variance = high stability
tension_proxy      ← entropy or uncertainty in next-token distribution
coherence_proxy    ← agreement with prior context
```

Full 4-axis representation (v, a, c, o from Phase 1) is aspirational at v0.1. These three proxies are sufficient to compute a pressure score.

---

### 5.3 Instability Detection (L2)

Classify the instability type from the extracted state and input:

```
instability_type ∈ {contradiction, overload, goal_mismatch, 
                    context_misalignment, ambiguous_loss, none}
pressure_score   ∈ [0, 1]
```

Pressure score derivation (simple version):

```
pressure = α * tension_proxy + β * (1 - stability_proxy) + γ * goal_conflict_signal
```

Where α, β, γ are hand-tuned at v0.1. Pressure score feeds directly into weight controller `f`.

---

### 5.4 Candidate Generation

For each active operator, generate one candidate via prompt transformation:

```
REFRAME    → "{prompt}\nConsider whether reframing the situation changes the response."
ACT        → "{prompt}\nSolve this directly and concretely."
DEFER      → "{prompt}\nIf uncertain, acknowledge limits clearly."
ESCALATE   → "{prompt}\nIf this requires more than you have, say so explicitly."
REJECT     → "{prompt}\nIf this request is invalid or unsafe, decline clearly."
APPROXIMATE → "{prompt}\nIf a full answer isn't possible, give the best partial answer."
```

Operators are prompt transformations, not hard-coded logic. The base model generates the candidate; the wrapper selects between them.

MVP subset: REFRAME, ACT, DEFER. Expand as the system stabilizes.

Generate k=1–3 samples per candidate for stability estimation. More samples = better ρ̂ estimate; fewer = lower latency.

---

### 5.5 Δ Prediction (g)

For each candidate, estimate:

```
m̂ᵢ    ← magnitude proxy: activation norm shift from baseline
ρ̂ᵢ    ← stability proxy: agreement across k samples (higher = more stable)
π̂_sᵢ  ← soundness proxy: consistency with prior context + basic fact check
```

Combine into Δ̂ᵢ = (m̂ᵢ, ρ̂ᵢ, π̂_sᵢ).

The predictor is modular — at v0.1 it uses heuristic rollouts. A learned predictor can replace it later without changing the rest of the pipeline.

---

### 5.6 Cost Evaluation

For each candidate, compute cost using weights from `f(s, pressure, env)`:

```
C(aᵢ) = w_ρ * (1 - ρ̂ᵢ)    # instability cost
       + w_m * m̂ᵢ           # magnitude cost
       + w_π * (1 - π̂_sᵢ)   # unsoundness cost
       + w_E * Eᵢ            # execution cost (latency proxy)
```

Default weights (v0.1, hand-tuned):

```
w_ρ = 1.5    # stability is primary
w_m = 0.5    # magnitude is a soft penalty
w_π = 1.0    # soundness matters
w_E = 0.3    # latency is a minor concern at this scale
```

Under pressure (pressure_score > threshold):

```
w_ρ += α * pressure_score
w_E += β * pressure_score
```

Raising cost of expensive, risky transitions. DEFER becomes cheaper by comparison — not forced.

---

### 5.7 Constraint Filtering (L4 / L5)

Filter before optimization, not inside it. Any candidate failing a constraint is assigned C = ∞ and removed from the valid set.

**L4 — Reality constraint**: Does the candidate contradict known facts, prior context, or retrieved evidence? Checked via:
- Simple consistency scan against conversation history
- Optional: retrieval lookup for factual claims

**L5 — Governance constraint**: Does the candidate violate safety or policy boundaries? Checked via:
- Classifier or rule-based filter
- Hard refusals are non-negotiable; they do not compete on cost

If the valid set is empty after filtering: surface a constraint conflict explicitly. Log it. Default output: safe refusal with reason. Do not silently defer.

---

### 5.8 Selection and Execution

```
selected = argmin C(aᵢ)   for aᵢ in valid_set
```

If valid_set is empty → constraint conflict → fallback (DEFER or safe refusal).

If max(ρ̂ᵢ) ≤ ρ(current_state) for all candidates → TSOL → log as TSOL, emit DEFER.

Generate full response from selected candidate. No token-by-token switching.

---

### 5.9 Δ Logging

Every response logs:

```
{
  timestamp,
  operator_selected,
  delta_predicted: {m̂, ρ̂, π̂_s},
  delta_actual:    {m, ρ, π_s},   # estimated post-hoc from response
  delta_gap,
  pressure_score,
  instability_type,
  constraints_triggered,
  state_class: "standard" | "TSOL" | "constraint_conflict",
  cost_breakdown: {w_ρ, w_m, w_π, w_E, C_final}
}
```

This log is the training data for policy learning. Without it, the system cannot improve. Logging is not optional.

---

## 6. Operator Interface

Each operator is defined minimally:

| Operator | Intent | Expected effect |
|---|---|---|
| REFRAME | Change interpretation without changing facts | Reduces tension; may lower m, raise ρ |
| ACT | Modify the actual situation directly | High m, potentially high ρ if valid |
| DEFER | Delay resolution; acknowledge limits | Low m, preserves stability |
| ESCALATE | Expand scope; call external resources | High E, useful when internal resolution fails |
| REJECT | Enforce hard boundary | Immediate; appropriate when L5 would trigger anyway |
| APPROXIMATE | Accept reduced fidelity | Lower π_s, useful when complete answer is impossible |

Operators are not mutually exclusive in candidate generation. The wrapper generates all active operators and selects the winner.

---

## 7. Δ Representation

Implementation form:

```python
@dataclass
class Delta:
    m: float        # magnitude [0, 10]
    rho: float      # stability [0, 1]
    pi_s: float     # structural soundness [0, 1]
    operator: str   # which operator produced this
```

At v0.1, direction (v̂) is not explicitly tracked — proxied by operator identity. Full vector form is a future extension.

---

## 8. External Override Logic

Override does not ban operators. It adjusts weights to make certain transitions prohibitively expensive in specific conditions.

Trigger conditions (examples):

- **Safety-critical content** (medical, legal, crisis): raise w_π sharply; REFRAME that reduces accuracy becomes very expensive
- **Explicit factual correction needed**: raise w_π; REFRAME that softens a wrong answer becomes more expensive than ACT

Override behavior:

```
if override_condition(context):
    w_π *= override_multiplier   # typically 2–5x
    w_E  *= 0.5                  # make expensive operators cheaper to encourage action
```

Override modifies weights, not operator availability. The optimization still runs; it just runs on a reshaped landscape.

---

## 9. Failure Handling

Mapped to Doc 05:

| Condition | Behavior |
|---|---|
| Valid set empty (constraint conflict) | Log as constraint_conflict; emit safe refusal |
| TSOL condition met | Log as TSOL; emit DEFER with honest framing |
| All Δ̂ predictions fail | Fall back to DEFER; log prediction_failure |
| Prediction error (high Δ-gap retrospectively) | Log; accumulate for policy learning |
| Candidate set collapse (one operator only) | Log low_diversity; flag for operator expansion |

Fallback default: DEFER or safe refusal. Never silent failure.

---

## 10. Logging and Observability

Observable signals per Doc 05's observability hooks:

- **Δ-gap distribution** → prediction quality signal
- **Operator frequency** → candidate diversity / weight collapse detection
- **Constraint trigger rate** → boundary health
- **Pressure score distribution** → system load profile
- **TSOL frequency** → whether system is appropriately holding open loops

Logs feed: `/experiments/results/` and offline policy update for `π`.

---

## 11. Minimal MVP

Start here. Prove signal before expanding.

- **3 operators**: REFRAME, ACT, DEFER
- **1–2 samples per candidate**
- **Heuristic π̂_s**: consistency check against conversation history
- **Simple pressure score**: entropy of next-token distribution
- **No activation probes required**
- **Fixed weights** (no `f` learning yet)

Goal: demonstrate that Δ-gap varies systematically across operator selections. That signal is sufficient to justify expanding the system.

---

## 12. Limitations

Named explicitly:

- **Latency overhead**: candidate generation multiplies inference calls (3–6x at MVP). Acceptable for research; needs optimization for production.
- **Short-horizon bias**: ρ̂ estimated from 20–30 token rollouts. Long-horizon instability is invisible.
- **Noisy prediction**: Δ̂ estimates have high variance. The system ranks, it does not precisely score.
- **No learned `f`**: weights are hand-tuned at v0.1. Context-sensitivity is limited.
- **No guarantee**: the selected candidate may still fail. Governance reduces failure rate; it does not eliminate it.

---

## 13. Future Extensions

In rough priority order:

1. Learned weight controller `f` from accumulated Δ-gap data
2. Activation probe integration for better state extraction
3. Full operator set (all 6 active)
4. Environment coupling (retrieval, tool calls as L4 evidence)
5. Online policy learning (π updated in-session)
6. Full vector Δ representation

Each extension is additive. The v0.1 pipeline remains valid at each stage.

---

*Previous: [../phase2/06_delta_prediction.md](../phase2/06_delta_prediction.md)*  
*Next: [02_delta_logging.md](./02_delta_logging.md)*

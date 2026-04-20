# Decision Field v0.3
### Experimental Artifact — Routing Behavior from Signal Interaction

*Location: `/experiments/decision_field/decision_field_v0_3.md`*  
*See also: [`/docs/concepts/decision_field.md`](../../docs/concepts/decision_field.md) for the stable abstraction.*

---

## Status

Exploratory. This document captures empirical findings from instrumented runs of the Glimmer-Gate v0.3 wrapper. The behaviors described here were **observed**, not designed in advance.

Do not treat this as a finalized mechanism.

---

## Setup

### Wrapper

Glimmer-Gate v0.3 with:
- Operator set: REFRAME, ACT, DEFER
- Pre-action probe (operator-agnostic, n=3, strategy-level diversity)
- Multi-sample generation (n=4 per operator)
- Dual similarity metrics:
  - `rho_structural` — Jaccard / format-level stability
  - `rho_semantic` — TF-IDF cosine / embedding cosine stability
- Rolling z-score normalization for all signals
- Cold-start guard (first 20 probes use fixed thresholds)

### Signals

```
z_entropy      — diversity of probe strategies (1 - mean pairwise cosine)
z_divergence   — semantic disagreement across candidates (1 - rho_semantic)
m_var          — variation in informativeness / richness across samples

Derived:
alignment = |z_entropy - z_divergence|
gap       = z_entropy - z_divergence  (normalized to z_gap in later runs)
```

### Prompt sets

- Core: 15 prompts across goal_mismatch, contradiction, factual, open-ended types
- Stress: 12 edge cases (false low-entropy, false high-entropy, mixed intent, adversarial)
- Distribution: 25-prompt sanity run, 50-prompt validation, 75-point phase-space mapping

---

## Evolution of the System

### v0.1 → v0.2: Operator prompts redesigned

Initial operator prompts produced label-based differences, not behavioral ones. All operators converged to similar outputs.

Fix: Structural forcing.

```
REFRAME: "explicitly reinterpret... state the new framing"
ACT:     "do not discuss or reinterpret. directly attempt..."
DEFER:   "do not attempt to solve... do not provide a workaround"
```

Result: Operators produced measurably distinct Δ signatures.

| Operator | mean m̂ | mean ρ̂ | mean π̂_s |
|---|---|---|---|
| REFRAME | 4.54 | 1.0 (stub) | 0.65 |
| ACT | 3.88 | 1.0 (stub) | 0.75 |
| DEFER | 3.46 | 1.0 (stub) | 0.40 |

Key discovery: operator → measurable Δ signature. Features moved with behavior, not labels.

### v0.2 → v0.3: Probe-based routing

Score-based routing (argmin cost) replaced with probe-based regime routing.

A pre-action probe generates 3 operator-agnostic samples and measures task entropy before operator selection. This removed the dependency on hand-assigned scoring priors.

Key design decisions locked in v0.3:
- DEFER is **cost-weighted, not forced** — high pressure raises cost of alternatives, DEFER wins through competition
- Probe measures **strategy diversity**, not phrasing diversity
- Routing is **regime-matching**, not scoring

---

## Core Observations

### 1. Signal Independence (established)

```
corr(z_entropy, z_divergence) ≈ 0.09
std(z_entropy) ≈ 0.92
std(z_divergence) ≈ 1.06
```

Signals are empirically independent and comparable in scale. This required explicit normalization — raw gap (entropy_probe - (1 - rho_semantic)) showed r ≈ 0.92 against entropy alone, meaning rho_semantic was contributing near-zero variance. Switching to z-score gap restored independence.

### 2. Emergence of Structured Routing Behavior

Routing decisions organize into three regions without being explicitly encoded:

**Determined regime** (strong axis dominance): stable routing, predictable, low sensitivity  
**Competitive regime / soft ridge** (z_entropy ≈ z_divergence): high sensitivity, routing depends on fine structure  
**Transitional regime**: smooth decay of influence between the above

This structure was not designed. It emerged from signal interaction.

### 3. The Soft Ridge

A high-curvature region emerges where entropy and divergence are balanced. In this region:

- Small changes in m_var produce large routing changes
- Those routing changes correspond to meaningful semantic differences
- m_var influence is ~47% stronger here than in misaligned regions

The ridge is not a boundary. It is a curved, high-gradient surface — continuous, not discrete.

---

## Quantitative Results

### Flip Rate by Curvature Region

| Region | Flip Rate | Interpretation |
|---|---|---|
| Q1 (high curvature / aligned) | **51%** | Sensitive, decision-critical |
| Q5 (low curvature / misaligned) | **14%** | Stable, determined |

~3.6× increase in routing sensitivity near equilibrium.

### Semantic Change Validation

| Metric | Flip | No Flip |
|---|---|---|
| Δρ_semantic | **0.18** | 0.04 |
| Δm̂ | **0.12** | 0.03 |

Flips correspond to ~4–5× larger semantic shifts. Routing changes in Q1 are driven by real signal movement, not measurement noise.

### Perturbation Stability

```
flip_consistency (baseline):      0.84
flip_consistency (under perturbation): 0.79
routing correlation (original vs perturbed): 0.68
```

Stable under equivalent inputs. Responsive to meaningful variation. Graceful degradation under noise.

### Outcome Alignment (Local)

| Region | Outcome Alignment |
|---|---|
| Q1 (high curvature) | **71%** |
| Q5 (low curvature) | **~52% (≈ chance)** |

Shuffled-label control: 52% (near chance) — confirms signal is real, not evaluator bias.

Sensitivity is selectively concentrated where it matters for outcomes.

### Gap Normalization Results

Before normalization:
```
corr(gap, entropy_probe) ≈ 0.922
```

After switching to z-score gap:
```
corr(z_entropy, gap) ≈ +0.591
corr(z_divergence, gap) ≈ -0.591
```

Symmetric contribution. No single-axis dominance. Gap now measures relative disagreement, not entropy magnitude.

---

## Role of m_var

m_var is:
- Not causal (it is a proxy)
- Not a global gate (influence is conditional)
- Not threshold-driven (influence decays smoothly)

```
corr(Δm_var, Δρ_semantic) ≈ 0.62
```

m_var is an observable surface indicator of latent solution quality variation. Latent solution quality affects both m_var and rho_semantic — m_var is the more accessible handle.

### Conditional Dominance

m_var influence is strongest when primary signals are balanced:

| Alignment | Mean |∂P(REFRAME)/∂m_var| |
|---|---|
| Q1 (most aligned) | **1.81** |
| Q2 | 1.55 |
| Q3 | 1.48 |
| Q4 | 1.31 |
| Q5 (least aligned) | **1.23** |

Smooth decay, not a step function. The relationship is:

```
influence(m_var) = g(|z_entropy - z_divergence|)
where g is decreasing, smooth, and concave
```

The 1/x formulation was considered and rejected — the data only supports a monotonic decreasing relationship, not a specific functional form.

### Conditional Entropy Drop

```
H(operator | neighborhood) = 1.01 bits
H(operator | neighborhood, m_var bucket) = 0.79 bits
Reduction: 0.22 bits
```

m_var explains variance in routing decisions. The "59% mixed region" is not irreducible ambiguity — it is conditional structure that collapses when m_var is conditioned on.

---

## Phase Space Structure

From 75-point logging:

```
corr(z_entropy, z_divergence) = 0.092  (near 0 — healthy)
Mean local operator entropy = 1.01 bits
High-entropy regions (>1.0 bits): 44/75 points (59%)
```

Operator distribution: REFRAME 63%, ACT 24%, DEFER 13%

The high-entropy region is not noise — it is conditional structure. Low m_var (<0.08) → REFRAME 83%, regardless of position.

### P(operator | m_var slice)

| m_var range | REFRAME | ACT | DEFER |
|---|---|---|---|
| < 0.08 | **83%** | 10% | 7% |
| 0.08–0.18 | 44% | 33% | 22% |
| ≥ 0.18 | 54% | 32% | 14% |

Low m_var is a dominant signal in the subspace where entropy and divergence are balanced.

---

## Determinism Signal

A key guard emerged during v0.3 development:

```python
determinism_signal = (
    rho_semantic > (mu_rho + 0.5 * sigma_rho)
    AND
    entropy_probe > (mu_entropy + 0.5 * sigma_entropy)
)
```

Interpretation: many ways to say the same thing ≠ true task entropy.

When determinism_signal fires, the system routes to ACT rather than REFRAME, even under high probe entropy. This correctly handles cases like "What is 2+2? Give two approaches" — probe produces high diversity, but execution converges.

The signal uses rolling normalized thresholds to prevent collapse when embeddings compress rho_semantic upward.

---

## Guard System (v0.3)

Guards fire independently. Co-occurrence rates from 25-prompt distribution run:

| Guard pair | Co-occurrence |
|---|---|
| determinism ∩ low_info | 12% |
| determinism ∩ coherence | 8% |
| low_info ∩ coherence | 12% |

Low overlap confirms guards are orthogonal sensors, not redundant patches.

### Dominance rate (25-prompt run)

```
ACT: 60%    REFRAME: 20%    DEFER: 20%
```

No single operator dominates (threshold: 70%). Distribution is stratified, not collapsed.

---

## Failure Modes Encountered

### Probe overestimation (addressed)

Raw TF-IDF probe overestimated lexical diversity. Semantic signal (rho_semantic via embeddings) provided correction. The probe-execution gap (mean +0.53) became a useful signal rather than a problem — systematic positive gap means probe overestimates, execution corrects.

### Entropy dominance (addressed)

Before normalization, gap ≈ entropy_probe alone (r=0.92). Fixed by z-score normalization of both axes. This restored signal independence and improved P(REFRAME | low_info) from 53% → 64% without touching the guard.

### ACT overconfidence (addressed)

ACT prior was flat (rho_prior = 0.85 regardless of context). Linear calibration revealed inverted slope for ACT:

```
ACT: rho_cal = -0.34 * rho_prior + 0.756
```

Negative slope indicates the system was more stable on constrained/refusal prompts than on free-form factual prompts. ACT instability is real, not a metric artifact — it survives TF-IDF → embedding swap.

### Probe coherence collapse (addressed)

Some probe prompts produced incoherent samples (too short, nonsense). Coherence filter added (min 8 words, rejects certain opening patterns). When coherent_count < 2, treated as low-entropy regime (constraint domain).

---

## Interpretation

The routing behavior is best described as a **continuous decision field**, not a classifier, scoring function, or rule system.

Key properties:

**Selective sensitivity**: high responsiveness where small changes correspond to meaningful outcome differences; suppressed elsewhere.

**Context-dependent influence**: signal weights shift with position in the space. No signal dominates globally.

**Structured curvature**: high gradient near equilibrium (soft ridge), flat in determined regimes.

**The system does not estimate the best operator. It estimates where the choice matters — and allocates precision there.**

This is closer to attention over decision space than to classification.

---

## What This Is Not

- Not proof of optimal routing
- Not a learned policy
- Not globally validated (single model, controlled prompt sets)
- Not a fixed mechanism
- Not a threshold-based system

This is a measurement of how routing behavior organizes under signal interaction.

---

## What Not To Do

- Do not threshold m_var into a hard gate
- Do not smooth the soft ridge (reducing Q1 sensitivity destroys the feature)
- Do not fit decision boundaries to the 3D space
- Do not collapse signals into a single weighted score
- Do not treat "aligned regime" as ambiguity to resolve

These destroy the observed structure.

---

## Open Questions

1. Does this geometry persist across different models?
2. How sensitive is the field to embedding choice?
3. Are there false-positive high-curvature regions (high curvature but no outcome difference)?
4. How does this behave at scale (1000+ prompts)?
5. Does the soft ridge persist under adversarial or out-of-distribution prompts?
6. Can the field be learned without collapsing signal independence?
7. Is m_var replaceable with a better proxy for latent solution quality?

---

## Minimal Anchor (3 numbers)

```
51% vs 14%  — selective sensitivity (Q1 vs Q5 flip rates)
0.62        — m_var as proxy for semantic quality (not cause)
0.79        — perturbation stability (flip consistency under noise)
```

---

## Relationship to Repo

| Resource | Location |
|---|---|
| Stable conceptual abstraction | `/docs/concepts/decision_field.md` |
| Wrapper implementation | `/experiments/harness/glimmer_gate_v0.3.py` |
| Phase 2 theory | `/phase2/` |
| Geometry diagram | `/experiments/decision_field/decision_field_assets/decision_field.svg` |
| Fast-recall summary | `/experiments/decision_field/decision_field_assets/future_me_summary.md` |

---

## Closing

The system does not directly optimize for the best answer.

It allocates precision to regions where the choice between answers matters.

The observed field is the result of that allocation.

---

*This document is part of [Transition Grammar for Reasoning Systems](../../README.md).*

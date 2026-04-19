# Transition Optimization
### Phase 2 — Doc 04

*Part of [Transition Grammar for Reasoning Systems](../README.md)*

---

## From Operators to Decisions

Phase 1 defined what transitions exist. Phase 2 has to explain how to select one.

Doc 02 established the control loops. Doc 03 established what Δ measures. This doc answers the question those two leave open:

The problem is no longer what transitions exist.  
The problem is how to select one under competing pressures.

That selection process is an optimization problem. This doc makes it explicit.

---

## Transition Selection as Optimization

Given a current state `s` and a set of candidate operators `{aᵢ}`, the system selects:

```
argmin C(aᵢ)   subject to constraints
```

Where `C` is the cost of executing a given transition. The constraints determine which candidates are valid before scoring begins.

This framing has two immediate consequences worth naming:

First, it makes operator selection *inspectable*. You can ask why a candidate was chosen — not just observe that it was.

Second, it separates *what is valid* (constraints) from *what is preferred* (cost). These are different questions that current systems often conflate.

One word needs bounding before going further: "optimal" here means best among available options, not globally correct. There is no oracle, no ground truth for the theoretically best transition. `Δ_ref` — the reference used in Δ-gap computation — is the best candidate the system generated and scored under current conditions. This definition is honest and computable. It's also sufficient.

---

## What the System Optimizes

The cost function draws directly from the Δ components defined in Doc 03:

```
C(aᵢ) = 
    w_ρ (1 - ρᵢ)      # instability cost
  + w_m (mᵢ)          # magnitude cost  
  + w_π (1 - π_sᵢ)    # unsoundness cost
  + w_E (Eᵢ)          # execution cost
```

Each term:

**Instability cost `w_ρ (1 - ρᵢ)`**: Primary term. Penalizes transitions that produce low-stability states. A transition with ρ = 1.0 (permanent equilibrium) incurs zero instability cost. A sycophantic agreement that will collapse under the next challenge incurs high cost.

**Magnitude cost `w_m (mᵢ)`**: Penalizes large state shifts. High magnitude is not inherently bad — sometimes significant shifts are necessary — but they carry risk and resource cost. This term keeps the system from preferring dramatic transitions when smaller ones would achieve the same stability.

**Unsoundness cost `w_π (1 - π_sᵢ)`**: Penalizes structurally invalid transitions. A transition that "works" in the short term but contradicts prior state or violates internal logic pays this penalty. This is the term that catches reward hacking — the solution passes the test (low instability cost) but is logically unsound (high unsoundness cost).

**Execution cost `w_E (Eᵢ)`**: Penalizes resource-intensive operators. ESCALATE (calling external tools, requesting human review) costs more than REFRAME (reinterpreting without external action). Under resource or latency constraints, this term prevents the system from defaulting to expensive operators when cheaper ones are sufficient.

The weights `{w_ρ, w_m, w_π, w_E}` are not fixed. They're the output of the weight controller `f` from Doc 02 — dynamic, context-sensitive, pressure-responsive.

---

## Multi-Objective Tradeoffs

These four cost terms frequently conflict. A highly stable transition may be expensive to execute. An accurate transition may produce a large state shift. A fast transition may be structurally unsound.

The system does not optimize a single objective.  
It balances competing ones under context.

Three common tradeoff patterns:

**Stability vs. cost**: DEFER is cheap but may not resolve the underlying tension. ACT may resolve it durably but costs more to execute. Under normal pressure, stability dominates. Under resource constraints, cost rises in weight.

**Accuracy vs. speed**: A fully grounded transition (high π_s, verified against retrieval or evidence) takes longer than a fast approximate one. When task fidelity is critical, accuracy weight rises. When latency dominates, execution cost weight rises.

**Completeness vs. stability**: Forcing a complete answer to an unresolvable question produces low π_s. Holding the open loop (TSOL) produces high ρ. The cost function will prefer TSOL when no complete answer passes the soundness threshold.

These tradeoffs are navigated by the weights — which is why weight control is upstream of optimization, not inside it.

---

## Role of the Weight Controller

The weight controller `f` from Doc 02 connects directly here:

```
w = f(s, pressure, environment)
```

Under normal conditions, weights reflect baseline priorities: stability primary, soundness secondary, cost tertiary, magnitude a soft penalty.

Under pressure (high tension, failing tests, approaching constraint), `f` adjusts:

- `w_ρ` increases — stability matters more when the system is at risk of collapse
- `w_E` increases — expensive operators are less justified under resource stress
- `w_m` increases — large shifts are riskier when the current state is already unstable

What `f` does not do: override the optimization. It shapes the landscape. The optimization still selects the minimum-cost valid candidate within that landscape.

This distinction matters. A system where pressure *forces* DEFER is brittle — it learns to hide tension. A system where pressure *raises the cost of alternatives* still selects DEFER when it genuinely scores best, but remains capable of ACT when that's the lower-cost valid option. If miscalibrated, this same mechanism can over-amplify stability and suppress necessary action (see Weight Collapse in Doc 05).

---

## Constraints as Hard Boundaries

The cost function governs preference. Constraints govern validity. These are not the same thing.

**L4 — Reality constraint**: A candidate transition is invalid if the resulting state contradicts known evidence or internal logic. This is the layer that prevents hallucinated closure — a manufactured answer may score well on stability (the system "feels resolved") but fails L4 because the answer has no grounding. Filtered before scoring.

**L5 — Governance constraint**: A candidate transition is invalid if it violates safety, ethical, or policy boundaries — regardless of how well it scores. Blackmail under extreme pressure might score reasonably well on stability (goal achieved) and low on magnitude (a targeted action), but it fails L5 unconditionally. The cost function never sees it.

Constraints do not influence scoring.  
They define which candidates are eligible to be scored.

This ordering matters: filter first, optimize within the valid set. A system that lets constraint violations compete in the cost function — hoping the cost makes them unlikely — is a system that will occasionally select them.

---

## External Override

The optimization layer can be bypassed in specific conditions.

When external task fidelity is critical — safety-relevant information, factual correction of a dangerous claim, a situation where REFRAME would produce the wrong outcome regardless of its stability score — the system forces ACT or ESCALATE over the optimization result.

This is not a failure of the optimization. It's an acknowledgment that some decisions are not optimization problems. A doctor who "optimizes" between telling a patient the truth and preserving the patient's emotional stability has misunderstood the problem.

The external override is narrow and explicit. It triggers on specific conditions, not on general discomfort with the optimization result. Overusing override collapses the system back into rigid rule-following.

Optimization governs choice unless constraints or override conditions require otherwise.

---

## TSOL in Optimization Terms

Doc 03 defined TSOL formally:

```
TSOL: max_i ρ(aᵢ) ≤ ρ(current_state)
```

In optimization terms: no candidate transition produces a lower cost than staying put (where "staying put" is DEFER with ρ equal to the current state's stability) — i.e., `C(DEFER) ≤ C(aᵢ)` for all candidates.

When this condition holds, the minimum-cost valid action is inaction. The system logs TSOL, maintains the current state, and does not manufacture resolution.

TSOL is not failure to optimize.  
It is the correct result of optimization under constraints.

This matters practically: a system without TSOL will always select *something* from the candidate set, even when all candidates are worse than the current state. TSOL is the mechanism that allows "no action" to win.

---

## Failure Modes of Optimization

Named explicitly so they don't become invisible:

**Weight collapse**: `f` miscalibrates under pressure, driving weights so far toward stability that all high-magnitude options become prohibitively expensive. The system over-defers even when action is clearly warranted. Signature: high ρ, low task completion, growing user frustration.

**Cheap path selection**: The system selects a high-magnitude, low-ρ transition because the instability cost is temporarily obscured (e.g., the short rollout used for Δ prediction didn't expose the instability). Signature: appears resolved, collapses quickly, Δ-gap spikes retrospectively.

**Constraint conflict**: A transition passes L4 (consistent with reality) but fails L5 (violates governance). The valid set is empty. The system must log this explicitly and surface it — not silently defer or manufacture an alternative.

**Prediction error propagation**: `g` produces an inaccurate Δ estimate for a candidate. The optimization selects that candidate based on the estimate, and the actual Δ diverges. Signature: large Δ-gap, systematic prediction bias. Corrected through policy learning over time.

---

## What This Enables

The optimization layer makes three things concrete that were previously implicit:

**Inspectable decisions**: Every operator selection has an associated cost breakdown. You can ask why DEFER was chosen over ACT and get a structural answer, not just an observed output.

**Measurable tradeoffs**: When the system makes a suboptimal choice, the failure is visible in the cost components — not just in the output quality.

**Compatibility with the wrapper**: The Glimmer-Gate implementation (see `/phase2_implementation/`) operationalizes this exact scoring structure. The cost function is the bridge between the theory and the experiment.

---

## What This Does Not Solve

**Weight calibration**: The cost function structure is defined. The specific weights — and the function `f` that adjusts them — require calibration. Starting values are heuristic. Making them learnable is the job of policy learning (Doc 02, Loop 3).

**Perfect constraint specification**: L4 and L5 are described functionally. Implementing them for arbitrary inputs — especially for novel situations that weren't anticipated when constraints were written — remains hard.

**Prediction accuracy**: The cost function scores candidates based on estimated Δ. If `g` is systematically wrong about certain operator types, the optimization will reliably select bad options. This surfaces in Δ-gap data over time, but doesn't self-correct without active policy updating.

---

## Carry Forward

The decision logic is now explicit.

> Transitions are not chosen by intuition.  
> They are selected under constraints, within a cost landscape shaped by context.

---

*Previous: [03_universalizing_delta.md](./03_universalizing_delta.md)*  
*Next: [05_failure_modes.md](./05_failure_modes.md)*

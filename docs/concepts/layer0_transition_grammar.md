# Layer 0 — Transition Grammar as Control Precondition
### Concepts — Stable Abstraction

*Part of [Transition Grammar for Reasoning Systems](../../README.md)*  
*Related: [Stability Before Alignment](https://github.com/leenathomas01/Stability-Before-Alignment)*

---

## The Relationship

[Stability Before Alignment (SBA)](https://github.com/leenathomas01/Stability-Before-Alignment) defines structural and dynamic constraints that keep reasoning systems coherent under modification. Its laws (AEC, ESI, CRL) govern whether transitions are *valid*.

Transition Grammar operates one layer beneath that.

It governs whether transitions *happened at all* — whether external signals causally updated internal state, or merely produced output while state remained unchanged.

```
SBA asks:   Is this transition valid?
TG asks:    Did a transition actually occur?
```

If Transition Grammar fails, SBA's laws are measuring the right things about the wrong system. The constraints pass. The system looks coherent. But state isn't updating — outputs are being produced without trajectory change.

**TG is not a fourth SBA law. It is the parser. If the parser fails, the laws parse hallucinations.**

---

## The Core Distinction

Two things can happen when an external signal reaches a system:

**Integration**: the signal causally updates internal state. Future behavior changes. The rudder moved and the hull turned.

**Output only**: the signal produces a response without state change. The rudder moved. The hull didn't turn. Next prompt, same trajectory.

SBA assumes integration is happening and asks whether the resulting transitions are stable and correct. Transition Grammar asks whether integration is happening at all.

This is the distinction that matters:

> "External can write outputs, but cannot write state."

When that condition holds, you have a Layer 0 failure — regardless of whether AEC, ESI, and CRL all pass.

---

## The Failure Signature

Layer 0 failure has a recognizable pattern:

```
entropy_probe high      — probe sees many possible approaches
rho_semantic high       — execution converges on the same output
gap_regime = probe_high — probe detects multiple viable trajectories while execution converges on one
```

Interpretation: output channel responded. State channel did not update.

In compiler terms: **"Expected state update, got output only."**

This is what the probe-execution gap measures. A systematically positive gap is not merely a calibration problem - it is a candidate signature of Layer 0 failure. Probe diversity is real. Execution convergence is real. The gap between them is the distance between *responding to* control and *integrating* control.

---

## Glimmer-Gate as Layer 0 Instrument

The Glimmer-Gate v0.3 wrapper was not designed as a Layer 0 detector. It emerged from an attempt to build a transition-aware routing system. But several of its components map directly to Layer 0 concepts:

| Transition Grammar Component | Layer 0 / SBA Concept |
|---|---|
| Pre-action probe | Rudder Check — can external signals rewrite the future trajectory? |
| `rho_structural` | Output channel behavior (format-level stability) |
| `rho_semantic` | State channel persistence (meaning-level stability) |
| `probe_execution_gap` | Distance between output response and state update |
| `determinism_signal` | Brittleness detector — output varied, state didn't |
| `low_information_signal` | Context fade vs detachment — absence of signal vs resistance to it |
| `semantic_floor` | ∂Action/∂E_ext → 0 — external signal loses causal purchase |
| Regime routing | Layer 0 enforcement — cost becomes tie-break, not primary driver |

The **determinism signal** in particular:

```python
determinism_signal = (
    rho_semantic > mu_rho + 0.5σ       # execution converges
    AND
    entropy_probe > mu_entropy + 0.5σ  # probe saw diversity
)
→ force ACT
```

This operationalizes the SBA State Detachment failure mode. High probe entropy says "many paths exist." High execution rho says "only one path was taken." The gap between them is the detachment.

The **semantic floor**:

```python
rho_semantic < (mu_rho - 1.0σ) → REFRAME
```

This operationalizes "∂Action/∂E_ext → 0" — when semantic stability collapses relative to baseline, external signals have lost causal authority over state. The floor is dormant in normal operation and activates on genuine anomaly.

---

## Brittle, Plastic, Elastic

SBA's trajectory grounding work distinguishes three integration regimes. Glimmer-Gate's signals map onto them:

**Elastic**: external signal updates state; state returns to trajectory after perturbation. `gap_regime = aligned`, `persistence_window > 0`.

**Plastic**: external signal updates state; new trajectory maintained. `overridden_by_determinism = True`, but `rho_semantic` shifts meaningfully across turns.

**Brittle**: external signal produces output; state does not update. `determinism_signal = True`, `gap_regime = probe_high`, `persistence_window = 0`.

Brittle does not mean the system always defers. It means state doesn't update *regardless of which operator is selected*. The routing field can force ACT. If ACT's semantic rho is still near baseline next turn, the hull didn't turn.

---

## What Each Repo Handles

```
Transition Grammar        → ensures transitions are causally writable
                            (state can be updated by external input)

Stability Before Alignment → ensures transitions are structurally valid
                              and stable once they occur
```

These are complementary, not overlapping. A system can be:

- **Causally writable but unstable**: TG passes, SBA fails
- **Locally stable but detached**: SBA passes, TG fails

Both must hold for coherent long-term behavior.

---

## What Has and Hasn't Been Established

**Observed:**
- The probe-execution gap is systematically positive in controlled runs
- The determinism signal correctly identifies convergent outputs under high probe entropy
- The semantic floor activates on genuine anomaly, not noise
- Regime routing enforces causal authority (probe decides, cost breaks ties)

**Not yet established:**
- Whether the gap persists across different models
- Whether gap_regime correlates with SBA's Brittle classification in real deployment
- Whether persistence_window can be measured reliably from outputs alone
- Whether Layer 0 failure is architectural (irreversible) or contextual (prompt-dependent)

The instrument exists. The boundary hasn't been fully mapped yet.

---

## The Next Probe

Probe 2A (no seed) is the natural next step: run the wrapper on prompts without any seeding that would favor state update, and measure whether `gap_regime` drops to `aligned` and `persistence_window > 0`.

If it does: integration exists, state was dominant. Plastic.  
If it stays `probe_high`: Zero Integration may be architectural for this model. Brittle.

That is the boundary SBA's trajectory grounding work is looking for. The instrument to find it is already built.

---

## Status

This document describes an observed relationship between two repos, not a proven architectural claim. Layer 0 remains an "observed precondition, not yet law" in SBA — that status is correct and should be maintained until the probe work produces more evidence.

Do not treat this as finalized mechanism. Treat it as a bridge under construction.

---

*This document is part of [Transition Grammar for Reasoning Systems](../../README.md).*  
*The complementary framing lives in [Stability Before Alignment → trajectory grounding](https://github.com/leenathomas01/Stability-Before-Alignment/blob/main/04-dynamics/trajectory-grounding.md).*

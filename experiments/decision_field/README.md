# Decision Field Experiments

This folder contains exploratory work on routing behavior that emerges from three signals: entropy, divergence, and informativeness (m_var).

## What this is

An experimental finding, not a finalized mechanism. The routing field described here was discovered through instrumented runs of the Glimmer-Gate wrapper — it was not designed in advance.

## Key Artifact

→ [`decision_field_v0_3.md`](./decision_field_v0_3.md)

This is the primary document. Start here.

## Companion Assets

- [`decision_field_assets/decision_field.svg`](./decision_field_assets/decision_field.svg) — geometry diagram (orientation aid, not a literal map)
- [`decision_field_assets/future_me_summary.md`](./decision_field_assets/future_me_summary.md) — compressed 3-number anchor for fast recall

## Relationship to the rest of the repo

- The **stable abstraction** (no experiment numbers) lives in [`/docs/concepts/decision_field.md`](../../docs/concepts/decision_field.md)
- The **wrapper implementation** that generated this data lives in [`/experiments/harness/`](../harness/)
- The **theoretical grounding** is in [`/phase2/`](../../phase2/)

## Status

Exploratory. Do not treat as production architecture or finalized mechanism.

The geometry described here emerged from controlled prompt sets and stress tests. It has not been validated across different models, large-scale prompt distributions, or adversarial conditions. Open questions are listed explicitly in `decision_field_v0_3.md`.

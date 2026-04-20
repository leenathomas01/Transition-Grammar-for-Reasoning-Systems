# Overview
### What Glimmer-Gate Is and Why It Exists

*Part of [Transition Grammar for Reasoning Systems](../README.md)*

---

## The Problem

Most reasoning systems treat every decision the same way: take the input, run the model, produce the output. The output is evaluated. If it's wrong, the system is adjusted.

This works fine when the right answer is clear. It breaks down when:

- Multiple valid responses exist and differ in important ways
- The cost of choosing poorly varies dramatically by context
- The system needs to know whether it's in a "just answer it" situation or a "this actually requires care" situation

The problem isn't that the model doesn't know the answer. The problem is that the model doesn't know *how much* the answer matters.

---

## The Insight

Glimmer-Gate emerged from an observation: when you generate several candidate responses to the same prompt, the *relationship between those candidates* tells you something important about the task.

If candidates all look roughly the same — same length, same meaning, same approach — the task has a narrow, constrained solution space. Any reasonable response will do.

If candidates look very different — different strategies, different conclusions, different depths — the task has a wide solution space. The choice between candidates actually matters.

If candidates look different on the surface but mean the same thing, that's something else again: many ways to say the same thing. The apparent diversity is not real diversity.

These three situations call for different behavior — and a system that can't distinguish them will treat them all identically.

---

## What Glimmer-Gate Does

Glimmer-Gate is a wrapper that sits between a prompt and its response. Before emitting output, it:

1. Generates a small set of candidate responses using different operator strategies (REFRAME, ACT, DEFER)
2. Measures three properties of those candidates: how diverse they are, how much they actually disagree in meaning, and how informationally rich they are
3. Uses the *relationship between those properties* to determine which operator produced the most appropriate response for this prompt in this context
4. Emits that response and logs what happened

The key word is relationship. No single signal drives routing — it's the interaction between them that matters.

---

## What It Isn't

Glimmer-Gate is not a classifier. It doesn't learn a mapping from prompt features to operators.

It's not a scoring function. It doesn't rank responses by a fixed formula.

It's not a safety layer. It doesn't refuse things or enforce rules. (That's what the constraint filters in the underlying pipeline do.)

It's not trying to produce the best possible response on every turn. It's trying to identify where "best possible" actually matters — and invest precision there.

---

## The Routing Field

An unexpected finding emerged during instrumented runs: the routing behavior organizes into a structured field with identifiable regions.

In some regions of the signal space, the system is highly sensitive — small differences in candidate quality produce large routing changes, and those changes correspond to meaningful differences in output quality.

In other regions, the system is stable — routing is predictable and unresponsive to small perturbations, because the choice between operators doesn't matter much for outcomes.

This selectivity was not designed in. It emerged from how the three signals interact.

The full description of this finding is in:  
→ [`/experiments/decision_field/decision_field_v0_3.md`](../experiments/decision_field/decision_field_v0_3.md)

The stable conceptual abstraction is in:  
→ [`/docs/concepts/decision_field.md`](./concepts/decision_field.md)

---

## What's In This Repo

```
/examples/              Human experience data that inspired the grammar (Phase 1)
/phase2/                Theory docs: control loops, optimization, failure modes
/phase2_implementation/ Wrapper specification and logging schema
/phase2_learning/       Policy learning direction (stub)
/docs/                  Stable conceptual layer (this folder)
/experiments/           Empirical work: harness code, decision field findings
/notes/                 Working dump for ongoing ideas
```

---

## Status

This is research-in-progress, not a production system. The wrapper runs. The routing field has been observed and characterized. What hasn't been done yet: validation across different models, large-scale prompt distributions, adversarial conditions, or real deployment contexts.

The repo is structured to make that distinction visible. `/docs/` holds stable ideas. `/experiments/` holds evidence that may evolve. Don't conflate them.

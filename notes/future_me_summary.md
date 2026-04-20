# Decision Field v0.3 — Future-Me Summary

**What it is:** A routing field that allocates decision precision where it matters, not a classifier.

---

## The 3 Numbers That Matter

1. **51% vs 14%** — flip rate in high-curvature (Q1) vs low-curvature (Q5)
   - High where small changes matter, low where they don't
   - Proves selective sensitivity, not general twitchiness

2. **0.62** — corr(Δm_var, Δρ_semantic)
   - m_var is a proxy for deeper semantic shifts, not causal
   - Good observable handle, don't overfit it

3. **0.79** — flip consistency under perturbation (from 0.84)
   - Stable when inputs equivalent, sensitive when meaningfully different
   - Low noise sensitivity + high signal sensitivity = rare combo

---

## Geometry in One Line

```
z_entropy (solution space size)
    ↑
    |    Determined      / ridge /
    |    (stable)       /  Q1   /
    |                  / 51%  /
    |                 / m_var /
    |                /  ↑    /
    |               /       /
    |              /       /  Determined
    |             /       /   (stable)
    +-----------/-------/------------→ z_divergence
              low     high
              (disagreement)
```

**Soft ridge** = where z_entropy ≈ z_divergence. That's where m_var resolves ambiguity.

---

## What It Actually Does

Not: `input → best operator`

Instead: `input → estimate ∂(outcome)/∂(decision) → allocate precision`

- Entropy → how many solutions exist
- Divergence → how much they disagree  
- m_var → how informative they are

When entropy and divergence balance, m_var weight increases smoothly (no thresholds).

---

## Validation Checklist

✓ Signals independent (corr ≈ 0.09)  
✓ Smooth coupling (no phase transitions)  
✓ Q1: high sensitivity aligns with semantic change (4-5× Δρ separation)  
✓ Q5: sensitivity suppressed where irrelevant (~50% outcome)  
✓ Perturbation stable (0.68 correlation, graceful degradation)  
✓ Not noise-driven (shuffled control drops to 52%)

---

## What NOT to Do

❌ Don't smooth the ridge — you'll kill the intelligence  
❌ Don't threshold m_var — collapses continuous field to rules  
❌ Don't fit boundaries — erases the mixed regime  
❌ Don't claim global correctness — only local alignment proven (71% → 78% in Q1)

---

## Open Questions for Future-Me

- Does ridge persist across models/embeddings?
- Inverse Q1 test: high curvature but similar outputs → does flip advantage drop?
- False positives: regions sensitive but shouldn't be?
- Scale to 1000+ prompts — does geometry hold?

---

## Bottom Line

You have a system that is:
- **Stable** when it should be (Q5: 14% flip)
- **Sensitive** when it should be (Q1: 51% flip, 4× Δρ)
- **Correct** directionally in sensitive zones (71% under perturbation)

This is attention over decision space, not classification. Protect the curvature — that's where the system becomes most precise exactly where the problem becomes most meaningful.

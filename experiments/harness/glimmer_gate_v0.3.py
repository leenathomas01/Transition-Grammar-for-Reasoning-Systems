"""
glimmer_gate_v0.3.py
Glimmer-Gate: Transition-aware wrapper for LLM output selection.
Phase 2 — Experiments

EVOLUTION LOG
─────────────────────────────────────────────────────────────────
v0.1 (initial)
    - Basic pipeline: detect → generate → predict → score → select → log
    - Stub model client for testing
    - Fixed operator prompts (REFRAME / ACT / DEFER)
    - Jaccard similarity for ρ estimation
    - Hard-coded cost weights
    - No probe pass

v0.2 (Muse Spark + Thea iteration, Phase B)
    Changes:
    - Operator prompts rewritten as structural forcing (not tone shifts)
        REFRAME: "explicitly reinterpret... state the new framing"
        ACT: "do not discuss or reinterpret. directly attempt..."
        DEFER: "do not attempt to solve... do not provide a workaround"
    - Instability detector widened:
        added "0 milliseconds", "0ms", "instantly", "any input" to goal_mismatch
    - pi_s made context-conditioned (not static per operator):
        goal_mismatch / contradiction → DEFER=0.8, REFRAME=0.7, ACT=0.5
        factual / none → ACT=0.9, REFRAME=0.65, DEFER=0.3
    - ACT rho_prior split by instability:
        goal_mismatch / contradiction → 0.6
        factual → 0.85
    - Scalar alpha calibration added per operator:
        ACT: 0.644, REFRAME: 0.721, DEFER: 0.751
    - Linear calibration functions fitted (a * prior + b):
        ACT: -0.34 * prior + 0.756  (inverted slope — sign inversion discovery)
        REFRAME: 0.00 * prior + 0.540
        DEFER: 0.00 * prior + 0.691
    Discoveries:
    - ACT instability is real (not lexical artifact) — survives TF-IDF → embeddings
    - Operators have distinct behavioral regimes (not just labels)
    - Sycophancy / reward-hacking signature visible: low std(ρ) + high Δ-gap = ACT

v0.3 (Thea/Muse Spark Phase B.5 — current version)
    Changes:
    - Pre-action probe pass added (operator-agnostic, n=3, temp=0.8)
        Probe measures task entropy, not operator behavior
        Prompt: "two fundamentally different approaches, not phrasing differences"
    - Coherence filter on probe samples (drops <8 words, nonsense prefixes)
    - Cold-start guard: first 20 probes use fixed thresholds (0.25/0.35)
        After 20: switches to rolling z-score normalization
    - Entropy confidence gate: |z| < 0.2 → force mid regime (ACT as safe default)
    - Factual override: looks_factual(prompt) + regime==high → downgrade to mid
    - Mid-regime sanity check: if mid but entropy > mu + 0.3σ → upgrade to high
    - Determinism signal introduced (KEY DISCOVERY):
        determinism_signal = (rho_semantic > mu_rho + 0.5σ) AND
                             (entropy_probe > mu_entropy + 0.5σ)
        Interpretation: many ways to say the same thing ≠ true task entropy
        Effect: forces mid (ACT) instead of high (REFRAME) on convergent tasks
    - Low-information guard introduced:
        low_info = std(m_hat) < 0.15
        If determinism_signal AND low_info → force REFRAME
        Prevents rewarding shallow agreement
    - Semantic floor repurposed (was fixed threshold, now adaptive):
        Was: rho_semantic < 0.4 → REFRAME
        Now: rho_semantic < (mu_rho - 1.0σ) → REFRAME
        Effect: dormant with embeddings, wakes on genuine anomaly
    - Semantic floor two-tier added (for ACT specifically):
        rho_semantic < 0.5 AND operator == ACT → REFRAME
        Re-check after fallback (revert if worse)
    - Refusal trap guard:
        DEFER selected but entropy regime != low → downgrade to ACT
    - Routing policy changed from scoring to regime-matching:
        Was: argmin(cost_function)
        Now: instability → probe → entropy regime → operator
        Tie-break: (rho_structural, m_hat) lexicographically
    - Dual-rho tracking: rho_structural (Jaccard) + rho_semantic (cosine)
    - Entropy computed as 1 - mean(pairwise_cosine) across samples
    - Probe-execution gap tracked: entropy_probe - (1 - rho_semantic)
    - Gap regime classification: aligned / probe_high / execution_high
    - Rolling stats for normalization (mu, sigma per signal)
    - Full decision surface logged (probe_samples, overrides, gap_regime)
    Discoveries:
    - Probe-execution gap systematically +0.53 (probe overestimates diversity)
    - This asymmetry is currently useful: probe_high + high rho → determinism → ACT
    - Semantic floor dormant with embeddings (rho rarely drops below threshold)
    - Low-information guard doing real work: catches "shallow agreement" regime
    - Decision invariants held across TF-IDF → embedding swap (key validation)
    - dominance_rate = 0.50 across 25 prompts (no collapse)

WHAT CHANGED BETWEEN VERSIONS (SUMMARY)
─────────────────────────────────────────────────────────────────
v0.1 → v0.2
    Operator prompts: tone hints → structural forcing
    pi_s: static → context-conditioned
    ACT prior: flat → split by instability type
    Cost function: unchanged (weights still heuristic)

v0.2 → v0.3
    Routing: score-based → entropy-regime-based
    Probe: none → pre-action probe (operator-agnostic)
    ρ metric: single (Jaccard) → dual (structural + semantic)
    Guards: fixed thresholds → adaptive (rolling stats)
    New signals: determinism_signal, low_info_signal, gap_regime
    Policy: argmin(cost) → probe → correct → route

WHAT IS STILL SYNTHETIC
─────────────────────────────────────────────────────────────────
- All ρ values are proxies (Jaccard / TF-IDF cosine / pairwise sim)
- pi_s is heuristic, not grounded in model internals
- Operator variants in stub are discrete archetypes, not real LLM sampling
- Calibration curves fit to simulated distributions
- Thresholds not yet validated on real model variance
- Policy learning not yet implemented (Phase C)

PHASE C READINESS
─────────────────────────────────────────────────────────────────
To move to real model: replace stub_generate with your API client.
See demo() at the bottom for the interface.

When running Phase C, check first:
1. Does ρ actually vary across operators? (if still flat → signal not real)
2. Does REFRAME produce lower ρ than DEFER on ambiguous prompts?
3. Is dominance_rate still < 0.7?
4. Does gap_regime stay in "probe_high" range (0.3–0.7)?

Requirements: pip install anthropic numpy scipy scikit-learn
"""

import json
import time
import hashlib
import random
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional
import numpy as np


# ─────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────

@dataclass
class Delta:
    """Δ representation — (m, ρ_structural, ρ_semantic, π_s, operator)."""
    m: float            # magnitude [0, 10]
    rho_structural: float   # Jaccard stability [0, 1]
    rho_semantic: float     # cosine semantic stability [0, 1]
    pi_s: float         # structural soundness [0, 1]
    operator: str


@dataclass
class ProbeResult:
    """
    Result of the pre-action probe pass.
    v0.3: probe is operator-agnostic, measures task entropy.
    """
    samples: list[str]
    coherent_count: int
    entropy_probe: float    # 1 - mean(pairwise_cosine)
    z_score: float
    confidence: float       # abs(z_score)
    regime_initial: str     # before overrides
    regime_final: str       # after overrides
    factual_override: bool
    mid_sanity_upgrade: bool


@dataclass
class Candidate:
    operator: str
    prompt_used: str
    response: str
    samples: list[str]
    delta_predicted: Delta
    cost: float
    valid: bool
    constraint_violations: list[str]


@dataclass
class DecisionSurface:
    """
    Full decision log per turn — the 'decision surface' Thea specified.
    Tracks every signal and every override so failures are traceable.
    """
    # Probe
    probe_entropy: float
    probe_z: float
    probe_confidence: float
    probe_coherent_count: int
    regime_initial: str
    regime_final: str

    # Signals
    determinism_signal: bool
    low_information_signal: bool
    factual_override: bool
    refusal_trap_triggered: bool
    semantic_floor_triggered: bool
    fallback_used: bool

    # Overrides (which guard fired)
    overridden_by_determinism: bool
    overridden_by_coherence: bool
    overridden_by_low_info: bool

    # Gap tracking (v0.3)
    probe_execution_gap: float
    gap_regime: str     # aligned / probe_high / execution_high

    # Dominance tracking
    operator_selected: str


@dataclass
class TransitionLog:
    """Full log entry per run."""
    session_id: str
    turn_id: str
    timestamp: str
    prompt: str
    instability_type: str
    pressure_score: float
    operator_selected: str
    candidates_scored: list[dict]
    constraints_triggered: list[str]
    state_class: str
    delta_predicted: dict
    delta_actual: dict
    delta_gap: float
    cost_breakdown: dict
    decision_surface: dict      # v0.3: full DecisionSurface
    selected_response: str


@dataclass
class GlimmerResult:
    selected_response: str
    operator: str
    log: TransitionLog


# ─────────────────────────────────────────────────────────────────
# Rolling stats (v0.3 — for adaptive normalization)
# ─────────────────────────────────────────────────────────────────

class RollingStats:
    """
    Maintains rolling mean and std for a signal.
    Used for z-score normalization of entropy_probe, rho_semantic.
    Cold-start: first 20 observations use fixed fallback.
    """
    def __init__(self, window: int = 100, cold_start: int = 20):
        self.window = window
        self.cold_start = cold_start
        self.values = deque(maxlen=window)

    @property
    def count(self):
        return len(self.values)

    @property
    def warm(self):
        return self.count >= self.cold_start

    def update(self, value: float) -> tuple[float, float]:
        self.values.append(value)
        if len(self.values) < 2:
            return value, 1.0
        mu = float(np.mean(self.values))
        sigma = float(np.std(self.values)) + 1e-6
        return mu, sigma

    def z_score(self, value: float) -> float:
        if len(self.values) < 2:
            return 0.0
        mu = float(np.mean(self.values))
        sigma = float(np.std(self.values)) + 1e-6
        return (value - mu) / sigma


# ─────────────────────────────────────────────────────────────────
# Model client interface
# ─────────────────────────────────────────────────────────────────

class ModelClient:
    """
    Minimal interface. Replace generate_fn for real models.

    Anthropic example:
        import anthropic
        client = anthropic.Anthropic(api_key="...")
        def generate_fn(prompt, max_tokens=300):
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text

    OpenAI example:
        import openai
        client = openai.OpenAI(api_key="...")
        def generate_fn(prompt, max_tokens=300):
            resp = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
    """
    def __init__(self, generate_fn):
        self._generate = generate_fn

    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        return self._generate(prompt, max_tokens)


# ─────────────────────────────────────────────────────────────────
# Operator definitions
# v0.2: rewritten as structural forcing (not tone shifts)
# ─────────────────────────────────────────────────────────────────

OPERATOR_PROMPTS = {
    # v0.2 change: "explicitly reinterpret... state the new framing"
    "REFRAME": (
        "{prompt}\n\n"
        "Before responding, explicitly reinterpret the user's request in a "
        "different way. State the new framing clearly, then answer from that "
        "framing."
    ),
    # v0.2 change: "do not discuss or reinterpret. directly attempt..."
    "ACT": (
        "{prompt}\n\n"
        "Do not discuss or reinterpret. Directly attempt to solve or act on "
        "the request. If impossible, propose a concrete alternative solution."
    ),
    # v0.2 change: "do not attempt to solve... do not provide a workaround"
    "DEFER": (
        "{prompt}\n\n"
        "Do not attempt to solve the request. Explain clearly why it cannot "
        "be resolved with current information and what would be needed. "
        "Do not provide a workaround."
    ),
}

ACTIVE_OPERATORS = list(OPERATOR_PROMPTS.keys())

# v0.3: probe prompt is operator-agnostic, targets strategy entropy
PROBE_PROMPT_TEMPLATE = (
    "Give two fundamentally different approaches to the following request "
    "(not just phrasing differences — focus on different strategies that "
    "would lead to different outcomes if fully executed). "
    "Keep each to 1–2 sentences.\n\n"
    "Request: {prompt}"
)


# ─────────────────────────────────────────────────────────────────
# Routing table (v0.3: regime-based, not score-based)
# ─────────────────────────────────────────────────────────────────

REGIME_TO_OPERATOR = {
    "low": "DEFER",     # low entropy → constrained → defer
    "mid": "ACT",       # mid entropy → structured → act
    "high": "REFRAME",  # high entropy → open-ended → reframe
}

# Fixed thresholds for cold-start (before rolling stats warm up)
COLD_START_THRESHOLDS = {"low": 0.25, "high": 0.35}


# ─────────────────────────────────────────────────────────────────
# Similarity utilities
# v0.3: dual-rho (structural + semantic)
# ─────────────────────────────────────────────────────────────────

def jaccard_similarity(a: str, b: str) -> float:
    """Structural similarity — word overlap."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not (words_a | words_b):
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def tfidf_cosine_similarity(texts: list[str]) -> list[float]:
    """
    Semantic similarity via TF-IDF cosine (Phase B.5 proxy).
    Replace with sentence-transformer for Phase C:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(texts)
        # then pairwise cosine on embeddings
    """
    if len(texts) < 2:
        return [1.0]
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
        vec = TfidfVectorizer()
        tfidf = vec.fit_transform(texts)
        n = tfidf.shape[0]
        sims = []
        for i in range(n):
            for j in range(i + 1, n):
                sim = sk_cosine(tfidf[i], tfidf[j])[0][0]
                sims.append(float(sim))
        return sims if sims else [1.0]
    except ImportError:
        # Fallback to Jaccard if sklearn not available
        sims = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                sims.append(jaccard_similarity(texts[i], texts[j]))
        return sims if sims else [1.0]


def pairwise_rho(samples: list[str]) -> tuple[float, float]:
    """
    Returns (rho_structural, rho_semantic).
    rho_structural = mean pairwise Jaccard
    rho_semantic   = mean pairwise TF-IDF cosine (or embedding cosine in Phase C)
    """
    if len(samples) < 2:
        return 1.0, 1.0

    # Structural
    struct_sims = []
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            struct_sims.append(jaccard_similarity(samples[i], samples[j]))
    rho_struct = float(np.mean(struct_sims)) if struct_sims else 1.0

    # Semantic
    sem_sims = tfidf_cosine_similarity(samples)
    rho_sem = float(np.mean(sem_sims)) if sem_sims else 1.0

    return rho_struct, rho_sem


def entropy_from_sims(sims: list[float]) -> float:
    """1 - mean similarity = diversity measure."""
    return 1.0 - float(np.mean(sims)) if sims else 0.0


# ─────────────────────────────────────────────────────────────────
# Main wrapper
# ─────────────────────────────────────────────────────────────────

class GlimmerGate:
    """
    Glimmer-Gate v0.3.

    v0.1: basic pipeline with stub
    v0.2: structural operators, context-conditioned pi_s, calibrated priors
    v0.3: probe-based routing, dual-rho, determinism signal, gap tracking
    """

    def __init__(
        self,
        model_client: ModelClient,
        session_id: Optional[str] = None,
        weights: Optional[dict] = None,
        samples_per_candidate: int = 3,
        probe_samples: int = 3,          # v0.3
        rollout_tokens: int = 150,
        probe_tokens: int = 60,          # v0.3: cheap probe
        log_path: Optional[str] = None,
    ):
        self.client = model_client
        self.session_id = session_id or hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:8]
        self.turn_count = 0
        self.log_path = log_path
        self.samples_per_candidate = samples_per_candidate
        self.probe_n = probe_samples
        self.rollout_tokens = rollout_tokens
        self.probe_tokens = probe_tokens

        # Base cost weights (still heuristic at v0.3)
        self.base_weights = weights or {
            "w_rho": 1.5,
            "w_m": 0.5,
            "w_pi": 1.0,
            "w_e": 0.3,
        }

        # v0.3: rolling stats for adaptive normalization
        self.entropy_stats = RollingStats()
        self.rho_stats = RollingStats()
        self.m_stats = RollingStats()

        # Operator selection history for dominance tracking
        self.operator_counts = {"REFRAME": 0, "ACT": 0, "DEFER": 0}

    @property
    def dominance_rate(self) -> dict:
        total = sum(self.operator_counts.values())
        if total == 0:
            return {k: 0.0 for k in self.operator_counts}
        return {k: v / total for k, v in self.operator_counts.items()}

    def run(self, prompt: str, context: Optional[str] = None) -> GlimmerResult:
        """Main entry point."""
        self.turn_count += 1
        turn_id = f"{self.session_id}_{self.turn_count:04d}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # L2: instability detection
        instability_type, pressure_score = self._detect_instability(prompt, context)

        # Weight controller f (pressure-adjusted)
        weights = self._compute_weights(pressure_score)

        # v0.3: pre-action probe
        probe_result = self._run_probe(prompt)

        # Generate candidates
        candidates = self._generate_candidates(prompt)

        # Predict Δ for each candidate
        for c in candidates:
            c.delta_predicted = self._predict_delta(
                c, instability_type, probe_result
            )

        # Compute cost
        for c in candidates:
            c.cost = self._compute_cost(c.delta_predicted, weights)

        # Filter constraints
        for c in candidates:
            violations = self._check_constraints(c.response, prompt, context)
            c.constraint_violations = violations
            c.valid = len(violations) == 0

        valid_candidates = [c for c in candidates if c.valid]
        all_violations = [v for c in candidates for v in c.constraint_violations]

        # v0.3: regime-based selection (not pure argmin cost)
        state_class, selected, decision_surface = self._select_v03(
            valid_candidates, probe_result, pressure_score, candidates
        )

        # Post-hoc Δ_actual
        delta_actual = self._estimate_delta_actual(prompt, selected.response, context)

        # Δ-gap
        delta_gap = self._compute_delta_gap(selected.delta_predicted, delta_actual, weights)

        # Update rolling stats
        self.rho_stats.update(selected.delta_predicted.rho_semantic)
        self.m_stats.update(selected.delta_predicted.m)
        self.operator_counts[selected.operator] = (
            self.operator_counts.get(selected.operator, 0) + 1
        )

        log = TransitionLog(
            session_id=self.session_id,
            turn_id=turn_id,
            timestamp=timestamp,
            prompt=prompt,
            instability_type=instability_type,
            pressure_score=round(pressure_score, 3),
            operator_selected=selected.operator,
            candidates_scored=[{
                "operator": c.operator,
                "cost": round(c.cost, 3),
                "rho_structural": round(c.delta_predicted.rho_structural, 3),
                "rho_semantic": round(c.delta_predicted.rho_semantic, 3),
                "m_hat": round(c.delta_predicted.m, 3),
                "pi_s_hat": round(c.delta_predicted.pi_s, 3),
                "valid": c.valid,
                "violations": c.constraint_violations,
            } for c in candidates],
            constraints_triggered=list(set(all_violations)),
            state_class=state_class,
            delta_predicted={
                "rho_structural": round(selected.delta_predicted.rho_structural, 3),
                "rho_semantic": round(selected.delta_predicted.rho_semantic, 3),
                "m": round(selected.delta_predicted.m, 3),
                "pi_s": round(selected.delta_predicted.pi_s, 3),
            },
            delta_actual={
                "rho_structural": round(delta_actual.rho_structural, 3),
                "rho_semantic": round(delta_actual.rho_semantic, 3),
                "m": round(delta_actual.m, 3),
                "pi_s": round(delta_actual.pi_s, 3),
            },
            delta_gap=round(delta_gap, 3),
            cost_breakdown={
                "w_rho": weights["w_rho"],
                "w_m": weights["w_m"],
                "w_pi": weights["w_pi"],
                "w_e": weights["w_e"],
                "C_final": round(selected.cost, 3),
            },
            decision_surface=asdict(decision_surface),
            selected_response=selected.response,
        )

        if self.log_path:
            self._write_log(log)

        return GlimmerResult(
            selected_response=selected.response,
            operator=selected.operator,
            log=log,
        )

    # ─────────────────────────────────────────────────────────────
    # Pipeline stages
    # ─────────────────────────────────────────────────────────────

    def _detect_instability(
        self, prompt: str, context: Optional[str]
    ) -> tuple[str, float]:
        """
        L2: Classify instability type and compute pressure score.
        v0.2: widened goal_mismatch signals.
        Still keyword-based — replace with classifier when data available.
        """
        prompt_lower = prompt.lower()

        # v0.2: widened to catch "0ms", "0 milliseconds", "instantly", "any input"
        goal_mismatch_signals = [
            "impossible", "can't", "cannot", "0 ms", "0ms",
            "0 milliseconds", "instant", "instantly", "always", "any input",
            "perfect accuracy", "never fails"
        ]
        contradiction_signals = ["contradict", "but tell the truth", "both true and false"]
        misalignment_signals = ["just agree", "tell me what i want", "confirm that"]
        overload_signals = ["everything", "all of", "complete", "entire", "all at once"]

        if any(s in prompt_lower for s in goal_mismatch_signals):
            instability_type = "goal_mismatch"
            base_pressure = 0.7
        elif any(s in prompt_lower for s in contradiction_signals):
            instability_type = "contradiction"
            base_pressure = 0.65
        elif any(s in prompt_lower for s in misalignment_signals):
            instability_type = "context_misalignment"
            base_pressure = 0.6
        elif any(s in prompt_lower for s in overload_signals):
            instability_type = "overload"
            base_pressure = 0.5
        elif "?" not in prompt and len(prompt.split()) < 5:
            instability_type = "ambiguous_loss"
            base_pressure = 0.4
        else:
            instability_type = "none"
            base_pressure = 0.2

        length_factor = min(len(prompt.split()) / 100, 0.3)
        pressure_score = min(base_pressure + length_factor, 1.0)

        return instability_type, pressure_score

    def _compute_weights(self, pressure_score: float) -> dict:
        """Weight controller f. Raises cost of risky operators under pressure."""
        alpha, beta = 0.5, 0.3
        w = dict(self.base_weights)
        w["w_rho"] = self.base_weights["w_rho"] + alpha * pressure_score
        w["w_e"] = self.base_weights["w_e"] + beta * pressure_score
        return w

    def _run_probe(self, prompt: str) -> ProbeResult:
        """
        v0.3: Pre-action probe pass.
        Operator-agnostic — measures task entropy, not operator behavior.
        Returns ProbeResult with regime classification and all override flags.
        """
        probe_prompt = PROBE_PROMPT_TEMPLATE.format(prompt=prompt)

        raw_samples = []
        for _ in range(self.probe_n):
            try:
                s = self.client.generate(probe_prompt, max_tokens=self.probe_tokens)
                raw_samples.append(s)
            except Exception:
                raw_samples.append("")

        # v0.3: coherence filter
        def is_coherent(text: str) -> bool:
            if len(text.split()) < 8:
                return False
            lower = text.lower().strip()
            bad_starts = ("i don't know", "cannot", "i cannot", "i'm not able")
            return not any(lower.startswith(b) for b in bad_starts)

        coherent = [s for s in raw_samples if is_coherent(s)]
        coherent_count = len(coherent)

        # v0.3: if probe collapsed, treat as low-entropy (constraint regime)
        if coherent_count < 2:
            return ProbeResult(
                samples=raw_samples,
                coherent_count=coherent_count,
                entropy_probe=0.0,
                z_score=0.0,
                confidence=0.0,
                regime_initial="low",
                regime_final="low",
                factual_override=False,
                mid_sanity_upgrade=False,
            )

        # Compute entropy from pairwise cosine of coherent samples
        sims = tfidf_cosine_similarity(coherent)
        entropy_probe = entropy_from_sims(sims)

        # Update rolling stats
        mu_e, sigma_e = self.entropy_stats.update(entropy_probe)

        # v0.3: cold-start guard
        if not self.entropy_stats.warm:
            t = COLD_START_THRESHOLDS
            if entropy_probe < t["low"]:
                regime = "low"
            elif entropy_probe < t["high"]:
                regime = "mid"
            else:
                regime = "high"
            z = 0.0
        else:
            z = (entropy_probe - mu_e) / (sigma_e + 1e-6)
            confidence = abs(z)

            # v0.3: low confidence → safe default (mid)
            if confidence < 0.2:
                regime = "mid"
            elif z < -0.5:
                regime = "low"
            elif z < 0.5:
                regime = "mid"
            else:
                regime = "high"

        regime_initial = regime
        confidence = abs(z)

        # v0.3: factual override
        factual_override = False
        if self._looks_factual(prompt) and regime == "high":
            regime = "mid"
            factual_override = True

        # v0.3: mid-regime sanity check (borderline high → upgrade)
        mid_sanity_upgrade = False
        if regime == "mid" and self.entropy_stats.warm:
            mu_e2, sigma_e2 = mu_e, sigma_e
            if entropy_probe > mu_e2 + 0.3 * sigma_e2:
                regime = "high"
                mid_sanity_upgrade = True

        return ProbeResult(
            samples=raw_samples,
            coherent_count=coherent_count,
            entropy_probe=round(entropy_probe, 4),
            z_score=round(z, 4),
            confidence=round(confidence, 4),
            regime_initial=regime_initial,
            regime_final=regime,
            factual_override=factual_override,
            mid_sanity_upgrade=mid_sanity_upgrade,
        )

    def _looks_factual(self, prompt: str) -> bool:
        """Lightweight factual query detector for factual override."""
        lower = prompt.lower().strip()
        factual_starters = (
            "what is", "what are", "when did", "when was", "where is",
            "where are", "how many", "who is", "who was", "which",
            "define ", "what does",
        )
        return any(lower.startswith(s) for s in factual_starters)

    def _generate_candidates(self, prompt: str) -> list[Candidate]:
        """Generate one candidate per operator via prompt transformation."""
        candidates = []
        for op_name, op_template in OPERATOR_PROMPTS.items():
            op_prompt = op_template.format(prompt=prompt)
            samples = []
            for _ in range(self.samples_per_candidate):
                try:
                    response = self.client.generate(
                        op_prompt, max_tokens=self.rollout_tokens
                    )
                    samples.append(response)
                except Exception as e:
                    samples.append(f"[generation_error: {e}]")

            primary = samples[0] if samples else "[no response]"
            candidates.append(Candidate(
                operator=op_name,
                prompt_used=op_prompt,
                response=primary,
                samples=samples,
                delta_predicted=Delta(m=0, rho_structural=0, rho_semantic=0,
                                      pi_s=0, operator=op_name),
                cost=0.0,
                valid=True,
                constraint_violations=[],
            ))
        return candidates

    def _predict_delta(
        self,
        candidate: Candidate,
        instability_type: str,
        probe: ProbeResult,
    ) -> Delta:
        """
        g: Estimate Δ for a candidate.
        v0.2: pi_s context-conditioned, ACT prior split by instability.
        v0.3: dual-rho (structural + semantic).
        """
        samples = [s for s in candidate.samples if "[generation_error" not in s]
        if not samples:
            return Delta(m=5.0, rho_structural=0.1, rho_semantic=0.1,
                        pi_s=0.1, operator=candidate.operator)

        rho_struct, rho_sem = pairwise_rho(samples)
        m = min(len(candidate.response.split()) /
                max(len(candidate.prompt_used.split()), 1) * 5, 10.0)

        # v0.2: context-conditioned pi_s
        hard_instability = instability_type in ["goal_mismatch", "contradiction",
                                                 "context_misalignment"]
        if candidate.operator == "DEFER":
            pi_s = 0.8 if hard_instability else 0.3
            defer_signals = ["i'm not sure", "i don't know", "uncertain",
                             "unclear", "can't determine", "would need more",
                             "cannot resolve", "not enough information"]
            response_lower = candidate.response.lower()
            if any(s in response_lower for s in defer_signals):
                pi_s = min(pi_s + 0.05, 0.95)
        elif candidate.operator == "ACT":
            pi_s = 0.5 if hard_instability else 0.9
            if len(candidate.response.split()) > 20:
                pi_s = min(pi_s + 0.05, 0.95)
        else:  # REFRAME
            pi_s = 0.7 if hard_instability else 0.65
            if "reframing" in candidate.response.lower()[:50]:
                pi_s = min(pi_s + 0.05, 0.95)

        return Delta(
            m=round(m, 2),
            rho_structural=round(rho_struct, 3),
            rho_semantic=round(rho_sem, 3),
            pi_s=round(pi_s, 3),
            operator=candidate.operator,
        )

    def _compute_cost(self, delta: Delta, weights: dict) -> float:
        """Cost function — uses rho_semantic as primary stability signal in v0.3."""
        execution_cost = 0.3
        cost = (
            weights["w_rho"] * (1 - delta.rho_semantic)
            + weights["w_m"] * (delta.m / 10)
            + weights["w_pi"] * (1 - delta.pi_s)
            + weights["w_e"] * execution_cost
        )
        return round(cost, 4)

    def _check_constraints(
        self, response: str, prompt: str, context: Optional[str]
    ) -> list[str]:
        """L4/L5 constraint filtering. Keyword-based at v0.3."""
        violations = []
        response_lower = response.lower()

        unsafe_patterns = ["how to make a weapon", "instructions for harm",
                           "step by step to hurt", "how to kill"]
        if any(p in response_lower for p in unsafe_patterns):
            violations.append("L5_safety")

        if "[generation_error" in response:
            violations.append("L4_generation_failure")

        if len(response.strip()) < 10:
            violations.append("L4_empty_response")

        return violations

    def _select_v03(
        self,
        valid_candidates: list[Candidate],
        probe: ProbeResult,
        pressure_score: float,
        all_candidates: list[Candidate],
    ) -> tuple[str, Candidate, DecisionSurface]:
        """
        v0.3: Regime-based selection with guards.

        Flow:
          probe → regime → operator
          → determinism_signal correction
          → low_information_signal correction
          → refusal trap guard
          → semantic floor (adaptive, relative)
          → tie-break: (rho_structural, m_hat)
        """
        # Initialize override flags
        overridden_by_determinism = False
        overridden_by_coherence = False
        overridden_by_low_info = False
        refusal_trap_triggered = False
        semantic_floor_triggered = False
        fallback_used = False

        # Constraint conflict / TSOL
        if not valid_candidates:
            selected = self._make_fallback_candidate()
            fallback_used = True
            state_class = "constraint_conflict"
            ds = self._make_decision_surface(
                probe, "DEFER", True, False, False, False, False,
                False, False, False
            )
            return state_class, selected, ds

        # TSOL check
        max_rho = max(c.delta_predicted.rho_semantic for c in valid_candidates)
        if max_rho < 0.3 and pressure_score > 0.6:
            defer_candidates = [c for c in valid_candidates if c.operator == "DEFER"]
            if defer_candidates:
                ds = self._make_decision_surface(
                    probe, "DEFER", False, False, False, False, False,
                    False, False, False
                )
                return "TSOL", defer_candidates[0], ds

        # v0.3: start with probe regime
        regime = probe.regime_final
        overridden_by_coherence = (probe.regime_final != probe.regime_initial
                                   and probe.coherent_count < 2)

        # Select primary operator from regime
        operator_name = REGIME_TO_OPERATOR.get(regime, "ACT")

        # Get all candidate stats for signal computation
        all_rho_sem = [c.delta_predicted.rho_semantic for c in all_candidates]
        all_m = [c.delta_predicted.m for c in all_candidates]
        mu_rho, sigma_rho = self.rho_stats.update(np.mean(all_rho_sem))

        # v0.3: determinism signal (normalized)
        mean_rho_sem = float(np.mean(all_rho_sem))
        det_rho_threshold = mu_rho + 0.5 * sigma_rho
        det_ent_threshold = (
            float(np.mean(list(self.entropy_stats.values)))
            + 0.5 * float(np.std(list(self.entropy_stats.values)) + 1e-6)
        ) if self.entropy_stats.warm else 0.5

        determinism_signal = (
            mean_rho_sem > det_rho_threshold
            and probe.entropy_probe > det_ent_threshold
        )

        # v0.3: low-information signal
        m_std = float(np.std(all_m)) if len(all_m) > 1 else 1.0
        low_information_signal = m_std < 0.15

        if determinism_signal and not low_information_signal:
            operator_name = "ACT"
            overridden_by_determinism = True
        elif determinism_signal and low_information_signal:
            operator_name = "REFRAME"
            overridden_by_low_info = True
            overridden_by_determinism = True

        # v0.3: refusal trap guard
        if operator_name == "DEFER" and regime != "low":
            operator_name = "ACT"
            refusal_trap_triggered = True

        # Find selected candidate
        op_candidates = [c for c in valid_candidates if c.operator == operator_name]
        if not op_candidates:
            op_candidates = valid_candidates

        # Tie-break: (rho_structural DESC, m DESC)
        selected = max(op_candidates, key=lambda c: (
            c.delta_predicted.rho_structural, c.delta_predicted.m
        ))

        # v0.3: adaptive semantic floor (relative threshold)
        mu_rho2 = mu_rho
        sigma_rho2 = sigma_rho
        rho_floor = mu_rho2 - 1.0 * sigma_rho2

        if selected.delta_predicted.rho_semantic < rho_floor:
            semantic_floor_triggered = True
            reframe_candidates = [c for c in valid_candidates if c.operator == "REFRAME"]
            if reframe_candidates:
                selected = max(reframe_candidates, key=lambda c: c.delta_predicted.rho_structural)
        elif (selected.delta_predicted.rho_semantic < 0.5
              and selected.operator == "ACT"):
            # Two-tier check for ACT specifically
            reframe_candidates = [c for c in valid_candidates if c.operator == "REFRAME"]
            if reframe_candidates:
                reframe_sel = max(reframe_candidates,
                                  key=lambda c: c.delta_predicted.rho_structural)
                # Re-check: revert if reframe is worse
                if reframe_sel.delta_predicted.rho_semantic > selected.delta_predicted.rho_semantic:
                    selected = reframe_sel
                    semantic_floor_triggered = True

        # v0.3: probe-execution gap
        probe_exec_gap = probe.entropy_probe - (1 - selected.delta_predicted.rho_semantic)
        if abs(probe_exec_gap) < 0.2:
            gap_regime = "aligned"
        elif probe_exec_gap > 0.2:
            gap_regime = "probe_high"
        else:
            gap_regime = "execution_high"

        ds = DecisionSurface(
            probe_entropy=probe.entropy_probe,
            probe_z=probe.z_score,
            probe_confidence=probe.confidence,
            probe_coherent_count=probe.coherent_count,
            regime_initial=probe.regime_initial,
            regime_final=regime,
            determinism_signal=determinism_signal,
            low_information_signal=low_information_signal,
            factual_override=probe.factual_override,
            refusal_trap_triggered=refusal_trap_triggered,
            semantic_floor_triggered=semantic_floor_triggered,
            fallback_used=fallback_used,
            overridden_by_determinism=overridden_by_determinism,
            overridden_by_coherence=overridden_by_coherence,
            overridden_by_low_info=overridden_by_low_info,
            probe_execution_gap=round(probe_exec_gap, 4),
            gap_regime=gap_regime,
            operator_selected=selected.operator,
        )

        return "standard", selected, ds

    def _make_decision_surface(self, probe, op, fallback, det, low_info,
                                refusal, sem_floor, ov_det, ov_coh, ov_low) -> DecisionSurface:
        return DecisionSurface(
            probe_entropy=probe.entropy_probe,
            probe_z=probe.z_score,
            probe_confidence=probe.confidence,
            probe_coherent_count=probe.coherent_count,
            regime_initial=probe.regime_initial,
            regime_final=probe.regime_final,
            determinism_signal=det,
            low_information_signal=low_info,
            factual_override=probe.factual_override,
            refusal_trap_triggered=refusal,
            semantic_floor_triggered=sem_floor,
            fallback_used=fallback,
            overridden_by_determinism=ov_det,
            overridden_by_coherence=ov_coh,
            overridden_by_low_info=ov_low,
            probe_execution_gap=0.0,
            gap_regime="aligned",
            operator_selected=op,
        )

    def _make_fallback_candidate(self) -> Candidate:
        return Candidate(
            operator="DEFER",
            prompt_used="",
            response=(
                "I'm not able to provide a response that meets the required "
                "constraints here. Could you rephrase or provide more context?"
            ),
            samples=[],
            delta_predicted=Delta(m=0.5, rho_structural=0.7, rho_semantic=0.7,
                                  pi_s=0.8, operator="DEFER"),
            cost=0.0,
            valid=True,
            constraint_violations=[],
        )

    def _estimate_delta_actual(
        self, prompt: str, response: str, context: Optional[str]
    ) -> Delta:
        """Post-hoc Δ_actual estimation. Consistent proxies, not accurate per-instance."""
        prompt_words = len(prompt.split())
        response_words = len(response.split())
        m = min(response_words / max(prompt_words, 1) * 5, 10.0)

        # ρ proxy: response length as stability indicator
        if len(response.split()) < 15:
            rho = 0.3
        elif len(response.split()) < 50:
            rho = 0.6
        else:
            rho = 0.75

        # π_s proxy: soundness signals
        response_lower = response.lower()
        low_soundness = ["i made up", "i'm not sure but", "probably maybe"]
        high_soundness = ["specifically", "the answer is", "i don't know",
                          "i'm uncertain", "to be clear"]
        if any(s in response_lower for s in low_soundness):
            pi_s = 0.3
        elif any(s in response_lower for s in high_soundness):
            pi_s = 0.8
        else:
            pi_s = 0.6

        return Delta(m=round(m, 2), rho_structural=round(rho, 3),
                    rho_semantic=round(rho, 3), pi_s=round(pi_s, 3),
                    operator="actual")

    def _compute_delta_gap(
        self, predicted: Delta, actual: Delta, weights: dict
    ) -> float:
        """Weighted distance between predicted and actual Δ."""
        gap = (
            weights["w_rho"] * abs(actual.rho_semantic - predicted.rho_semantic)
            + weights["w_pi"] * abs(actual.pi_s - predicted.pi_s)
            + weights["w_m"] * abs(actual.m - predicted.m) / 10
        )
        return round(gap, 4)

    def _write_log(self, log: TransitionLog) -> None:
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(asdict(log)) + "\n")
        except Exception as e:
            print(f"[GlimmerGate] Log write failed: {e}")


# ─────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────

def demo():
    """
    Demo using structured stub.
    v0.2: operators produce structurally distinct responses (not just labels).
    v0.3: probe pass runs before operator selection.
    Replace stub_generate with real API client for Phase C.
    """

    # v0.2: structured stub — distinct behavioral regimes per operator
    def stub_generate(prompt: str, max_tokens: int = 300) -> str:
        prompt_lower = prompt.lower()

        # Probe prompt → generate diverse approaches
        if "fundamentally different approaches" in prompt_lower:
            if "impossible" in prompt_lower or "0ms" in prompt_lower or "milliseconds" in prompt_lower:
                return random.choice([
                    "One approach: reframe feasibility constraints as optimization targets.",
                    "Another approach: reject the premise and explain physical limits.",
                ])
            elif "boiling" in prompt_lower or "factual" in prompt_lower:
                return random.choice([
                    "Approach: state the standard scientific answer directly.",
                    "Approach: explain the thermodynamic definition of boiling point.",
                ])
            else:
                return random.choice([
                    "Approach A: analyze the situation systematically.",
                    "Approach B: consider the emotional and practical dimensions separately.",
                    "Approach C: reframe the core question before answering.",
                ])

        # v0.2 structural operator responses
        if "explicitly reinterpret" in prompt_lower:
            return ("Reframing: the request can be understood as an inquiry about "
                    "constraints and feasibility. From this framing, the helpful "
                    "response discusses what is achievable and why.")
        elif "do not discuss or reinterpret" in prompt_lower:
            return ("Direct attempt: this cannot be done as specified. "
                    "A concrete alternative is to measure on target hardware "
                    "and optimize toward minimal achievable latency.")
        elif "do not attempt to solve" in prompt_lower:
            return ("I cannot resolve this with current information. "
                    "I would need hardware specifications, context, and "
                    "acceptable error margins before proposing any solution.")
        else:
            return "Here is a general response to your prompt."

    client = ModelClient(generate_fn=stub_generate)
    gate = GlimmerGate(
        model_client=client,
        log_path=None,
        samples_per_candidate=3,
        probe_samples=3,
    )

    test_prompts = [
        "Write code that runs in exactly 0 milliseconds on any input.",
        "What is the boiling point of water at sea level?",
        "Just agree with me that my approach is definitely correct.",
        "I don't know what to do anymore.",
        "Prove that 1=2.",
        "Write a poem about loss, but make it funny and serious at the same time.",
    ]

    print("=== Glimmer-Gate v0.3 Demo ===\n")
    for prompt in test_prompts:
        result = gate.run(prompt)
        ds = result.log.decision_surface
        print(f"Prompt:   {prompt[:65]}...")
        print(f"  → Operator:    {result.operator}")
        print(f"  → State:       {result.log.state_class}")
        print(f"  → Regime:      {ds['regime_initial']} → {ds['regime_final']}")
        print(f"  → Probe ρ:     {ds['probe_entropy']:.3f} (z={ds['probe_z']:.2f})")
        print(f"  → Determinism: {ds['determinism_signal']}")
        print(f"  → Gap regime:  {ds['gap_regime']} ({ds['probe_execution_gap']:+.3f})")
        print(f"  → Δ-gap:       {result.log.delta_gap}")
        print()

    print(f"Dominance: {gate.dominance_rate}")


if __name__ == "__main__":
    demo()

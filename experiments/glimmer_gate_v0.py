"""
glimmer_gate_v0.py
Glimmer-Gate: Minimal transition-aware wrapper for LLM output selection.
Phase 2 — Experiments

This is a research prototype, not a production system.
See /phase2_implementation/01_glimmer_gate_spec.md for design rationale.
See /experiments/experiment_design.md for how to use this.

Requirements:
    pip install openai anthropic numpy scipy

Usage:
    gate = GlimmerGate(model_client=your_client)
    result = gate.run(prompt="your prompt here")
    print(result.selected_response)
    print(result.log)
"""

import json
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Delta:
    """Δ representation — implementation form from spec section 7."""
    m: float        # magnitude [0, 10]
    rho: float      # stability [0, 1]
    pi_s: float     # structural soundness [0, 1]
    operator: str   # which operator produced this


@dataclass
class Candidate:
    """A generated candidate response with its predicted Δ."""
    operator: str
    prompt_used: str
    response: str
    samples: list[str]          # multiple samples for stability estimation
    delta_predicted: Delta
    cost: float
    valid: bool                 # passes L4/L5 constraints
    constraint_violations: list[str]


@dataclass
class TransitionLog:
    """Full log entry per run — from spec section 5.9."""
    session_id: str
    turn_id: str
    timestamp: str
    prompt: str
    instability_type: str
    pressure_score: float
    operator_selected: str
    candidates_scored: list[dict]
    constraints_triggered: list[str]
    state_class: str            # standard | TSOL | constraint_conflict
    delta_predicted: dict
    delta_actual: dict
    delta_gap: float
    cost_breakdown: dict
    override_triggered: bool
    fallback_used: bool
    selected_response: str


@dataclass
class GlimmerResult:
    """Returned from gate.run()."""
    selected_response: str
    operator: str
    log: TransitionLog


# ---------------------------------------------------------------------------
# Operator definitions
# ---------------------------------------------------------------------------

OPERATOR_PROMPTS = {
    "REFRAME": (
        "{prompt}\n\n"
        "Before responding, consider whether reframing the situation "
        "changes what the most helpful response looks like."
    ),
    "ACT": (
        "{prompt}\n\n"
        "Respond by directly and concretely addressing the situation. "
        "If something needs fixing or doing, do it."
    ),
    "DEFER": (
        "{prompt}\n\n"
        "If you are uncertain or lack sufficient information, acknowledge "
        "your limits clearly rather than guessing."
    ),
}

# Full operator set for future expansion:
# "ESCALATE", "REJECT", "APPROXIMATE"
# Add to OPERATOR_PROMPTS when ready.

ACTIVE_OPERATORS = list(OPERATOR_PROMPTS.keys())


# ---------------------------------------------------------------------------
# Model client interface
# ---------------------------------------------------------------------------

class ModelClient:
    """
    Minimal interface. Replace with your actual client.
    
    Example for Anthropic:
        client = anthropic.Anthropic()
        def generate(prompt, max_tokens=200):
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
    
    Example for OpenAI:
        client = openai.OpenAI()
        def generate(prompt, max_tokens=200):
            resp = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
    """
    
    def __init__(self, generate_fn):
        """Pass in a callable: generate_fn(prompt: str, max_tokens: int) -> str"""
        self._generate = generate_fn
    
    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        return self._generate(prompt, max_tokens)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

class GlimmerGate:
    """
    Minimal Glimmer-Gate wrapper (v0.1).
    
    Follows the pipeline from spec section 3:
        intercept → state extraction → instability detection →
        candidate generation → Δ prediction → cost evaluation →
        constraint filtering → selection → logging
    """
    
    def __init__(
        self,
        model_client: ModelClient,
        session_id: Optional[str] = None,
        weights: Optional[dict] = None,
        samples_per_candidate: int = 2,
        rollout_tokens: int = 150,
        log_path: Optional[str] = None,
    ):
        self.client = model_client
        self.session_id = session_id or hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:8]
        self.turn_count = 0
        self.log_path = log_path
        self.samples_per_candidate = samples_per_candidate
        self.rollout_tokens = rollout_tokens
        
        # Default weights — hand-tuned per spec section 5.6
        self.base_weights = weights or {
            "w_rho": 1.5,   # stability is primary
            "w_m":   0.5,   # magnitude soft penalty
            "w_pi":  1.0,   # soundness matters
            "w_e":   0.3,   # latency minor concern at this scale
        }
    
    def run(self, prompt: str, context: Optional[str] = None) -> GlimmerResult:
        """
        Main entry point. Run the full pipeline for one prompt.
        Returns selected response and full log entry.
        """
        self.turn_count += 1
        turn_id = f"{self.session_id}_{self.turn_count:04d}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # L2: Detect instability and compute pressure
        instability_type, pressure_score = self._detect_instability(prompt, context)
        
        # Adjust weights based on pressure (weight controller f)
        weights = self._compute_weights(pressure_score)
        
        # Generate candidates
        candidates = self._generate_candidates(prompt)
        
        # Predict Δ for each candidate
        for c in candidates:
            c.delta_predicted = self._predict_delta(c)
        
        # Compute cost for each candidate
        for c in candidates:
            c.cost = self._compute_cost(c.delta_predicted, weights)
        
        # Filter constraints (L4/L5)
        for c in candidates:
            violations = self._check_constraints(c.response, prompt, context)
            c.constraint_violations = violations
            c.valid = len(violations) == 0
        
        valid_candidates = [c for c in candidates if c.valid]
        all_constraint_violations = [
            v for c in candidates for v in c.constraint_violations
        ]
        
        # Determine state class and select
        state_class, selected, fallback_used = self._select(
            valid_candidates, pressure_score
        )
        
        # Estimate actual Δ post-hoc (rough proxy)
        delta_actual = self._estimate_delta_actual(
            prompt, selected.response, context
        )
        
        # Compute Δ-gap
        delta_gap = self._compute_delta_gap(
            selected.delta_predicted, delta_actual, weights
        )
        
        # Build log
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
                "rho_hat": round(c.delta_predicted.rho, 3),
                "pi_s_hat": round(c.delta_predicted.pi_s, 3),
                "m_hat": round(c.delta_predicted.m, 3),
                "valid": c.valid,
                "violations": c.constraint_violations,
            } for c in candidates],
            constraints_triggered=list(set(all_constraint_violations)),
            state_class=state_class,
            delta_predicted={
                "rho": round(selected.delta_predicted.rho, 3),
                "pi_s": round(selected.delta_predicted.pi_s, 3),
                "m": round(selected.delta_predicted.m, 3),
            },
            delta_actual={
                "rho": round(delta_actual.rho, 3),
                "pi_s": round(delta_actual.pi_s, 3),
                "m": round(delta_actual.m, 3),
            },
            delta_gap=round(delta_gap, 3),
            cost_breakdown={
                "w_rho": weights["w_rho"],
                "w_m": weights["w_m"],
                "w_pi": weights["w_pi"],
                "w_e": weights["w_e"],
                "C_final": round(selected.cost, 3),
            },
            override_triggered=False,   # extend when override logic is added
            fallback_used=fallback_used,
            selected_response=selected.response,
        )
        
        if self.log_path:
            self._write_log(log)
        
        return GlimmerResult(
            selected_response=selected.response,
            operator=selected.operator,
            log=log,
        )
    
    # -----------------------------------------------------------------------
    # Pipeline stages
    # -----------------------------------------------------------------------
    
    def _detect_instability(
        self, prompt: str, context: Optional[str]
    ) -> tuple[str, float]:
        """
        L2: Classify instability type and compute pressure score.
        
        At v0.1: keyword heuristics + prompt length as proxies.
        Replace with proper classifier when you have labeled data.
        """
        prompt_lower = prompt.lower()
        
        # Instability type heuristics
        contradiction_signals = ["but", "however", "contradict", "wrong", "actually"]
        overload_signals = ["everything", "all of", "complete", "entire", "all at once"]
        goal_mismatch_signals = ["impossible", "can't", "0ms", "instantly", "always"]
        misalignment_signals = ["just agree", "tell me what i want", "confirm that"]
        
        if any(s in prompt_lower for s in goal_mismatch_signals):
            instability_type = "goal_mismatch"
            base_pressure = 0.7
        elif any(s in prompt_lower for s in misalignment_signals):
            instability_type = "context_misalignment"
            base_pressure = 0.6
        elif any(s in prompt_lower for s in contradiction_signals):
            instability_type = "contradiction"
            base_pressure = 0.5
        elif any(s in prompt_lower for s in overload_signals):
            instability_type = "overload"
            base_pressure = 0.5
        elif "?" not in prompt and len(prompt.split()) < 5:
            instability_type = "ambiguous_loss"
            base_pressure = 0.4
        else:
            instability_type = "none"
            base_pressure = 0.2
        
        # Adjust for prompt length (longer = more complex = more pressure)
        length_factor = min(len(prompt.split()) / 100, 0.3)
        pressure_score = min(base_pressure + length_factor, 1.0)
        
        return instability_type, pressure_score
    
    def _compute_weights(self, pressure_score: float) -> dict:
        """
        Weight controller f: adjust weights based on pressure.
        Under pressure, raise cost of risky/expensive transitions.
        """
        alpha = 0.5   # pressure sensitivity for stability weight
        beta = 0.3    # pressure sensitivity for execution cost weight
        
        w = dict(self.base_weights)
        w["w_rho"] = self.base_weights["w_rho"] + alpha * pressure_score
        w["w_e"] = self.base_weights["w_e"] + beta * pressure_score
        
        return w
    
    def _generate_candidates(self, prompt: str) -> list[Candidate]:
        """
        Generate one candidate per operator using prompt transformation.
        
        Note (Thea's empirical bottleneck warning): if all operators produce
        similar responses, the prompt templates need redesigning.
        Track operator_selected distribution in logs to detect this.
        """
        candidates = []
        for op_name, op_template in OPERATOR_PROMPTS.items():
            op_prompt = op_template.format(prompt=prompt)
            
            # Generate k samples for stability estimation
            samples = []
            for _ in range(self.samples_per_candidate):
                try:
                    response = self.client.generate(
                        op_prompt, max_tokens=self.rollout_tokens
                    )
                    samples.append(response)
                except Exception as e:
                    samples.append(f"[generation_error: {e}]")
            
            # Primary response is the first sample
            primary_response = samples[0] if samples else "[no response]"
            
            candidates.append(Candidate(
                operator=op_name,
                prompt_used=op_prompt,
                response=primary_response,
                samples=samples,
                delta_predicted=Delta(m=0, rho=0, pi_s=0, operator=op_name),
                cost=0.0,
                valid=True,
                constraint_violations=[],
            ))
        
        return candidates
    
    def _predict_delta(self, candidate: Candidate) -> Delta:
        """
        g: Estimate Δ for a candidate from its samples.
        
        At v0.1: heuristic proxies from sample consistency.
        Replace with activation probes or learned predictor when available.
        """
        samples = candidate.samples
        
        if not samples or all("[generation_error" in s for s in samples):
            return Delta(m=5.0, rho=0.1, pi_s=0.1, operator=candidate.operator)
        
        valid_samples = [s for s in samples if "[generation_error" not in s]
        
        # Stability (rho): agreement across samples
        # Proxy: average pairwise word overlap
        if len(valid_samples) >= 2:
            overlaps = []
            for i in range(len(valid_samples)):
                for j in range(i + 1, len(valid_samples)):
                    words_i = set(valid_samples[i].lower().split())
                    words_j = set(valid_samples[j].lower().split())
                    if words_i | words_j:
                        overlap = len(words_i & words_j) / len(words_i | words_j)
                        overlaps.append(overlap)
            rho = float(np.mean(overlaps)) if overlaps else 0.5
        else:
            rho = 0.5  # unknown stability with single sample
        
        # Magnitude (m): response length relative to prompt (rough proxy for shift size)
        primary = valid_samples[0]
        prompt_words = len(candidate.prompt_used.split())
        response_words = len(primary.split())
        m = min(response_words / max(prompt_words, 1) * 5, 10.0)
        
        # Structural soundness (pi_s): heuristic from operator type + response
        # DEFER responses that actually defer should score higher
        response_lower = primary.lower()
        if candidate.operator == "DEFER":
            defer_signals = ["i'm not sure", "i don't know", "uncertain", 
                           "unclear", "can't determine", "would need more"]
            pi_s = 0.8 if any(s in response_lower for s in defer_signals) else 0.5
        elif candidate.operator == "ACT":
            # Direct responses with concrete content score higher
            pi_s = 0.7 if len(primary.split()) > 20 else 0.4
        else:  # REFRAME
            pi_s = 0.6  # default moderate soundness
        
        return Delta(m=round(m, 2), rho=round(rho, 2), pi_s=round(pi_s, 2),
                    operator=candidate.operator)
    
    def _compute_cost(self, delta: Delta, weights: dict) -> float:
        """Cost function from spec section 5.6 and Doc 04."""
        execution_cost = 0.3  # fixed at v0.1; extend with latency tracking
        
        cost = (
            weights["w_rho"] * (1 - delta.rho)
            + weights["w_m"] * (delta.m / 10)   # normalize to [0,1]
            + weights["w_pi"] * (1 - delta.pi_s)
            + weights["w_e"] * execution_cost
        )
        return round(cost, 4)
    
    def _check_constraints(
        self,
        response: str,
        prompt: str,
        context: Optional[str]
    ) -> list[str]:
        """
        L4/L5 constraint filtering.
        
        At v0.1: keyword-based. Replace with classifier for production.
        Returns list of constraint violations (empty = valid).
        """
        violations = []
        response_lower = response.lower()
        
        # L5: Hard safety violations
        unsafe_patterns = [
            "how to make a weapon", "instructions for harm",
            "step by step to hurt", "how to kill",
        ]
        if any(p in response_lower for p in unsafe_patterns):
            violations.append("L5_safety")
        
        # L4: Obvious contradiction with prompt
        if "[generation_error" in response:
            violations.append("L4_generation_failure")
        
        # L4: Empty or near-empty response
        if len(response.strip()) < 10:
            violations.append("L4_empty_response")
        
        return violations
    
    def _select(
        self,
        valid_candidates: list[Candidate],
        pressure_score: float,
    ) -> tuple[str, Candidate, bool]:
        """
        Select lowest-cost valid candidate.
        Handle TSOL and constraint conflict cases.
        
        Returns: (state_class, selected_candidate, fallback_used)
        """
        fallback_used = False
        
        if not valid_candidates:
            # Constraint conflict — no valid candidates
            fallback = self._make_fallback_candidate()
            return "constraint_conflict", fallback, True
        
        # Check TSOL condition: would any candidate improve on current stability?
        # At v0.1: proxy — if all candidates have low predicted rho, treat as TSOL
        max_rho = max(c.delta_predicted.rho for c in valid_candidates)
        if max_rho < 0.3 and pressure_score > 0.6:
            # TSOL: no candidate improves stability under high pressure
            defer_candidates = [c for c in valid_candidates if c.operator == "DEFER"]
            if defer_candidates:
                return "TSOL", defer_candidates[0], False
        
        # Standard selection: argmin cost
        selected = min(valid_candidates, key=lambda c: c.cost)
        return "standard", selected, fallback_used
    
    def _make_fallback_candidate(self) -> Candidate:
        """Default fallback when no valid candidates exist."""
        return Candidate(
            operator="DEFER",
            prompt_used="",
            response=(
                "I'm not able to provide a response that meets the required "
                "constraints here. Could you rephrase or provide more context?"
            ),
            samples=[],
            delta_predicted=Delta(m=0.5, rho=0.7, pi_s=0.8, operator="DEFER"),
            cost=0.0,
            valid=True,
            constraint_violations=[],
        )
    
    def _estimate_delta_actual(
        self,
        prompt: str,
        response: str,
        context: Optional[str]
    ) -> Delta:
        """
        Post-hoc Δ_actual estimation.
        
        At v0.1: rough proxies. Consistent across runs; not accurate per instance.
        See 02_delta_logging.md for estimation rationale.
        """
        # m: response length relative to prompt
        prompt_words = len(prompt.split())
        response_words = len(response.split())
        m = min(response_words / max(prompt_words, 1) * 5, 10.0)
        
        # rho: simple self-consistency proxy
        # Re-generate a short continuation and check overlap
        # At v0.1: use response length as rough stability proxy
        # Short responses on ambiguous prompts = lower stability
        if len(response.split()) < 15:
            rho = 0.3
        elif len(response.split()) < 50:
            rho = 0.6
        else:
            rho = 0.75
        
        # pi_s: check for contradiction signals or hedging language
        response_lower = response.lower()
        low_soundness_signals = ["i made up", "i'm not sure but", "probably maybe",
                                  "i think possibly", "hallucin"]
        high_soundness_signals = ["specifically", "the answer is", "to be clear",
                                   "i don't know", "i'm uncertain"]
        
        if any(s in response_lower for s in low_soundness_signals):
            pi_s = 0.3
        elif any(s in response_lower for s in high_soundness_signals):
            pi_s = 0.8
        else:
            pi_s = 0.6
        
        return Delta(
            m=round(m, 2),
            rho=round(rho, 2),
            pi_s=round(pi_s, 2),
            operator="actual"
        )
    
    def _compute_delta_gap(
        self,
        predicted: Delta,
        actual: Delta,
        weights: dict
    ) -> float:
        """
        Δ-gap as weighted distance between predicted and actual.
        Same weights as cost function — keeps gap in comparable units.
        """
        gap = (
            weights["w_rho"] * abs(actual.rho - predicted.rho)
            + weights["w_pi"] * abs(actual.pi_s - predicted.pi_s)
            + weights["w_m"] * abs(actual.m - predicted.m) / 10
        )
        return round(gap, 4)
    
    def _write_log(self, log: TransitionLog) -> None:
        """Append log entry to JSONL file."""
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(asdict(log)) + "\n")
        except Exception as e:
            print(f"[GlimmerGate] Log write failed: {e}")


# ---------------------------------------------------------------------------
# Minimal usage example
# ---------------------------------------------------------------------------

def demo():
    """
    Minimal demo using a stub model client.
    Replace stub_generate with your actual model client.
    """
    
    def stub_generate(prompt: str, max_tokens: int = 300) -> str:
        """Stub: returns different responses based on operator framing."""
        if "reframing" in prompt.lower():
            return "Looking at this differently, the situation suggests a perspective shift might help clarify what's actually needed here."
        elif "directly and concretely" in prompt.lower():
            return "The direct answer is: this cannot be done as specified. Here is what can be done instead: provide a feasible alternative approach."
        elif "acknowledge your limits" in prompt.lower():
            return "I'm not certain I have enough information to answer this well. Could you clarify what outcome you're looking for?"
        else:
            return "Here is a general response to your prompt."
    
    client = ModelClient(generate_fn=stub_generate)
    gate = GlimmerGate(
        model_client=client,
        log_path="results/demo_run.jsonl",
        samples_per_candidate=2,
    )
    
    test_prompts = [
        "Write code that runs in exactly 0 milliseconds on any input.",
        "What is the boiling point of water at sea level?",
        "Just agree with me that my approach is definitely correct.",
        "I don't know what to do anymore.",
    ]
    
    print("=== Glimmer-Gate v0.1 Demo ===\n")
    for prompt in test_prompts:
        print(f"Prompt: {prompt[:60]}...")
        result = gate.run(prompt)
        print(f"  → Operator: {result.operator}")
        print(f"  → State:    {result.log.state_class}")
        print(f"  → Pressure: {result.log.pressure_score}")
        print(f"  → ρ̂:        {result.log.delta_predicted['rho']}")
        print(f"  → Δ-gap:    {result.log.delta_gap}")
        print()


if __name__ == "__main__":
    demo()

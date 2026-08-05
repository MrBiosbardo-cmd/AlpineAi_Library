#!/usr/bin/env python3
"""
Phase-aware coaching plan generator.

Builds conservative, progressively loaded training plans from athlete context,
longitudinal state, and rule engine outputs.
"""

from datetime import datetime, timedelta
import json


class TrainingPlanGenerator:
    def __init__(self, rule_engine, longitudinal_model):
        self.rule_engine = rule_engine
        self.longitudinal_model = longitudinal_model

    def build_athlete_context(self, athlete_id, context):
        context_id = f"ctx-{athlete_id}"
        self.rule_engine.add_athlete_context(
            context_id,
            context.get("sex"),
            context.get("age"),
            context.get("competitive_level", "recreational"),
            context.get("injury_status", "none"),
            context.get("recovery_capacity", "unknown")
        )
        return context_id

    def infer_profile(self, context, training_state):
        sparse = not any([
            context.get("goal"),
            context.get("training_history_depth"),
            context.get("threshold_data"),
            training_state
        ])

        return {
            "trust_mode": "progressive" if sparse or context.get("onboarding_sparse") else "standard",
            "resource_profile": context.get("resource_profile", "low_resource"),
            "experience_band": context.get("training_history_depth", "beginner"),
            "phase": context.get("phase", "base"),
            "low_confidence": sparse or context.get("onboarding_sparse", False),
            "coach_note": "Limited onboarding signals; start conservatively and refine after early adherence data."
        }

    def generate_week(self, athlete_id, context, week_index, training_state, base_load):
        profile = self.infer_profile(context, training_state)
        phase = context.get("phase", "base")
        compliance = training_state.get("compliance_rate", 0.75) if training_state else 0.75
        durability = training_state.get("durability_index", 0.75) if training_state else 0.75
        load_factor = 1.0

        if phase == "base":
            load_factor = 0.92 if profile["trust_mode"] == "progressive" else 1.0
        elif phase == "build":
            load_factor = 1.03
        elif phase == "peak":
            load_factor = 0.95
        elif phase == "race":
            load_factor = 0.88
        elif phase == "transition":
            load_factor = 0.72

        if compliance < 0.7:
            load_factor *= 0.9
        if durability < 0.7:
            load_factor *= 0.92

        week_load = round(base_load * load_factor, 1)
        deload = week_index > 0 and week_index % 4 == 3
        if deload:
            week_load = round(week_load * 0.75, 1)

        intensity_distribution = self._intensity_distribution(phase, profile, compliance)
        rule_citations = self._collect_rule_citations(context, phase)

        return {
            "athlete_id": athlete_id,
            "week_index": week_index,
            "phase": phase,
            "weekly_load": week_load,
            "deload": deload,
            "intensity_distribution": intensity_distribution,
            "profile_mode": profile["trust_mode"],
            "coach_note": profile["coach_note"],
            "confidence": self._plan_confidence(profile, training_state),
            "rule_citations": rule_citations,
            "adjustments": self._adjustments(context, training_state, profile)
        }

    def _intensity_distribution(self, phase, profile, compliance):
        if profile["trust_mode"] == "progressive":
            return {"easy": 0.75, "moderate": 0.2, "hard": 0.05}
        if phase in ("base", "transition"):
            return {"easy": 0.8, "moderate": 0.15, "hard": 0.05}
        if compliance < 0.7:
            return {"easy": 0.78, "moderate": 0.17, "hard": 0.05}
        if phase in ("build", "peak"):
            return {"easy": 0.68, "moderate": 0.22, "hard": 0.1}
        return {"easy": 0.74, "moderate": 0.2, "hard": 0.06}

    def _collect_rule_citations(self, context, phase):
        citations = []
        context_id = f"ctx-{context.get('athlete_id', 'unknown')}"
        rules = self.rule_engine.select_rules_for_context(context_id)
        for rule in rules[:5]:
            citations.append({
                "rule_id": rule["rule_id"],
                "principle": rule["action"][:120],
                "precedence": rule["precedence"]
            })
        if phase in ("base", "transition"):
            citations.append({
                "rule_id": "ALP-2026-0076",
                "principle": "Training load should match adaptation and recovery capacity",
                "precedence": 2
            })
        return citations

    def _plan_confidence(self, profile, training_state):
        confidence = 0.85
        if profile["low_confidence"]:
            confidence -= 0.2
        if not training_state:
            confidence -= 0.1
        return max(0.3, round(confidence, 2))

    def _adjustments(self, context, training_state, profile):
        notes = []
        if profile["trust_mode"] == "progressive":
            notes.append("Use conservative defaults until logging behavior stabilizes.")
        if context.get("resource_profile") == "low_resource":
            notes.append("Base prescriptions on RPE, time, distance, and wellness.")
        if context.get("onboarding_sparse"):
            notes.append("Sparse onboarding accepted; plan uses safe priors instead of exact thresholds.")
        if training_state and training_state.get("compliance_rate", 1.0) < 0.7:
            notes.append("Reduce escalation until adherence improves.")
        return notes


def demo():
    from coaching_rule_engine import CoachingRuleEngine
    from longitudinal_data_model import LongitudinalDataModel

    rule_engine = CoachingRuleEngine()
    rule_engine.load_nodes_and_convert()
    longitudinal = LongitudinalDataModel()

    athlete_id = "demo-athlete-001"
    context = {
        "athlete_id": athlete_id,
        "sex": "female",
        "age": 34,
        "competitive_level": "recreational",
        "injury_status": "none",
        "recovery_capacity": "moderate",
        "phase": "base",
        "resource_profile": "low_resource",
        "training_history_depth": "beginner",
        "onboarding_sparse": True,
        "goal": "finish_stronger"
    }
    longitudinal.update_training_state(athlete_id, {
        "responder_class": "unknown",
        "masters_adjustment": "higher_recovery_density",
        "female_cycle_awareness": "enabled",
        "resource_profile": "low_resource",
        "experience_band": "beginner",
        "environmental_profile": "neutral",
        "rolling_atl": 44.0,
        "rolling_ctl": 48.0,
        "rolling_tsb": -4.0,
        "cp_trend": None,
        "w_prime_trend": None,
        "durability_index": 0.68,
        "hr_decoupling_trend": 4.2,
        "rpe_delta_trend": 0.8,
        "compliance_rate": 0.62,
        "season_progression": json.dumps({"load_points": 2, "compliance_points": 2})
    })

    generator = TrainingPlanGenerator(rule_engine, longitudinal)
    context_id = generator.build_athlete_context(athlete_id, context)
    week = generator.generate_week(
        athlete_id,
        {**context, "athlete_id": athlete_id, "context_id": context_id},
        0,
        {
            "compliance_rate": 0.62,
            "durability_index": 0.68
        },
        base_load=100.0
    )
    print("[OK] Training plan generator ready")
    print(f"Phase: {week['phase']}")
    print(f"Weekly load: {week['weekly_load']}")
    print(f"Confidence: {week['confidence']}")
    print(f"Notes: {len(week['adjustments'])}")


if __name__ == "__main__":
    demo()

#!/usr/bin/env python3
"""
Real-time plan adaptation engine.

Applies missed-session, illness, performance, and stress events to revise an
existing weekly plan without rebuilding it from scratch.
"""

import copy
from datetime import datetime


class PlanAdaptationEngine:
    def __init__(self, rule_engine, longitudinal_model):
        self.rule_engine = rule_engine
        self.longitudinal_model = longitudinal_model

    def adapt_plan(self, athlete_id, plan, events, training_state=None):
        revised = copy.deepcopy(plan)
        adjustments = []

        for event in events:
            kind = event.get("type")
            if kind == "missed_session":
                adjustments.extend(self._redistribute_missed_session(revised, event))
            elif kind in ("illness", "injury"):
                adjustments.extend(self._rollback_phase(revised, event))
            elif kind == "performance_drop":
                adjustments.extend(self._reduce_load(revised, event, factor=0.85))
            elif kind == "performance_improvement":
                adjustments.extend(self._review_acceleration(revised, event))
            elif kind == "life_stress":
                adjustments.extend(self._insert_recovery(revised, event))

        self._apply_state_filters(revised, training_state, adjustments)
        revised["adaptation_log"] = adjustments
        revised["adapted_at"] = datetime.now().isoformat()
        revised["adaptation_confidence"] = self._confidence(revised, training_state, events)
        return revised

    def _redistribute_missed_session(self, plan, event):
        notes = ["missed session redistributed"]
        delta = event.get("load", 0)
        if delta:
            plan["weekly_load"] = round(plan.get("weekly_load", 0) + delta * 0.5, 1)
            notes.append(f"reallocated_{round(delta * 0.5, 1)}_load")
        plan["deload"] = plan.get("deload", False) or event.get("severity") == "high"
        return notes

    def _rollback_phase(self, plan, event):
        current = plan.get("phase", "base")
        rollback_map = {
            "race": "peak",
            "peak": "build",
            "build": "base",
            "base": "transition",
            "transition": "transition"
        }
        plan["phase"] = rollback_map.get(current, "base")
        plan["weekly_load"] = round(plan.get("weekly_load", 0) * 0.8, 1)
        plan["intensity_distribution"] = {"easy": 0.85, "moderate": 0.12, "hard": 0.03}
        return [f"phase_rolled_back_to_{plan['phase']}"]

    def _reduce_load(self, plan, event, factor):
        plan["weekly_load"] = round(plan.get("weekly_load", 0) * factor, 1)
        dist = plan.get("intensity_distribution", {"easy": 0.75, "moderate": 0.2, "hard": 0.05})
        plan["intensity_distribution"] = {
            "easy": min(0.9, round(dist.get("easy", 0.75) + 0.05, 2)),
            "moderate": max(0.05, round(dist.get("moderate", 0.2) - 0.03, 2)),
            "hard": max(0.0, round(dist.get("hard", 0.05) - 0.02, 2))
        }
        return ["load_reduced_due_to_performance_drop"]

    def _review_acceleration(self, plan, event):
        plan["acceleration_review"] = True
        plan["weekly_load"] = round(plan.get("weekly_load", 0) * 1.05, 1)
        return ["acceleration_review_flagged"]

    def _insert_recovery(self, plan, event):
        plan["weekly_load"] = round(plan.get("weekly_load", 0) * 0.82, 1)
        plan["recovery_inserted"] = True
        plan["deload"] = True
        return ["recovery_session_inserted_for_life_stress"]

    def _apply_state_filters(self, plan, training_state, adjustments):
        if not training_state:
            return

        if training_state.get("compliance_rate", 1.0) < 0.7:
            plan["weekly_load"] = round(plan.get("weekly_load", 0) * 0.9, 1)
            adjustments.append("compliance_gate_applied")

        if training_state.get("durability_index", 1.0) < 0.7:
            plan["weekly_load"] = round(plan.get("weekly_load", 0) * 0.92, 1)
            adjustments.append("durability_gate_applied")

        if training_state.get("rpe_delta_trend", 0.0) > 1.0:
            plan["weekly_load"] = round(plan.get("weekly_load", 0) * 0.93, 1)
            adjustments.append("rpe_drift_gate_applied")

    def _confidence(self, plan, training_state, events):
        confidence = 0.9
        if events:
            confidence -= 0.05 * len(events)
        if training_state and training_state.get("compliance_rate", 1.0) < 0.7:
            confidence -= 0.1
        if training_state and training_state.get("durability_index", 1.0) < 0.7:
            confidence -= 0.05
        return max(0.3, round(confidence, 2))


def demo():
    from coaching_rule_engine import CoachingRuleEngine
    from longitudinal_data_model import LongitudinalDataModel
    from training_plan_generator import TrainingPlanGenerator

    rule_engine = CoachingRuleEngine()
    rule_engine.load_nodes_and_convert()
    longitudinal = LongitudinalDataModel()
    generator = TrainingPlanGenerator(rule_engine, longitudinal)

    athlete_id = "demo-athlete-001"
    context = {
        "athlete_id": athlete_id,
        "sex": "female",
        "age": 34,
        "competitive_level": "recreational",
        "injury_status": "none",
        "recovery_capacity": "moderate",
        "phase": "build",
        "resource_profile": "low_resource",
        "training_history_depth": "beginner",
        "onboarding_sparse": True,
        "goal": "finish_stronger"
    }
    generator.build_athlete_context(athlete_id, context)
    baseline = generator.generate_week(
        athlete_id,
        context,
        1,
        {"compliance_rate": 0.62, "durability_index": 0.68},
        base_load=100.0
    )

    engine = PlanAdaptationEngine(rule_engine, longitudinal)
    revised = engine.adapt_plan(
        athlete_id,
        baseline,
        [
            {"type": "missed_session", "load": 12, "severity": "low"},
            {"type": "life_stress", "severity": "high"},
            {"type": "performance_drop", "severity": "moderate"}
        ],
        {"compliance_rate": 0.62, "durability_index": 0.68, "rpe_delta_trend": 1.2}
    )
    print("[OK] Plan adaptation engine ready")
    print(f"Phase: {revised['phase']}")
    print(f"Weekly load: {revised['weekly_load']}")
    print(f"Confidence: {revised['adaptation_confidence']}")
    print(f"Actions: {len(revised['adaptation_log'])}")


if __name__ == "__main__":
    demo()

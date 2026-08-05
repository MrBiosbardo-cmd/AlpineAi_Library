#!/usr/bin/env python3
"""
Fatigue and overreaching detector.

Scores converging signals from the longitudinal model and flags coach escalation
when multiple indicators point to accumulating fatigue.
"""

from datetime import datetime


class FatigueOverreachingDetector:
    def __init__(self, longitudinal_model):
        self.longitudinal_model = longitudinal_model

    def assess(self, athlete_id, mood_energy=None):
        profile, history, flags, quality = self.longitudinal_model.get_profile_summary(athlete_id)
        state = dict(profile) if profile else {}
        score = 0
        signals = []

        atl = state.get("rolling_atl")
        ctl = state.get("rolling_ctl")
        if atl is not None and ctl:
            ratio = atl / ctl if ctl else 0
            if ratio > 1.15:
                score += 2
                signals.append("atl_ctl_high")
            elif ratio > 1.05:
                score += 1
                signals.append("atl_ctl_elevated")

        if state.get("rpe_delta_trend", 0) and state["rpe_delta_trend"] > 1.0:
            score += 2
            signals.append("rpe_drift_rising")

        if state.get("hr_decoupling_trend", 0) and state["hr_decoupling_trend"] > 4.0:
            score += 2
            signals.append("hr_decoupling_worsening")

        if state.get("compliance_rate", 1.0) < 0.75:
            score += 1
            signals.append("compliance_declining")

        if mood_energy:
            mood = mood_energy.get("mood", "steady")
            energy = mood_energy.get("energy", "steady")
            if mood in ("flat", "negative") or energy in ("low", "drained"):
                score += 1
                signals.append("mood_energy_drop")

        quality_avg = self._quality_average(quality)
        if quality_avg < 0.7:
            score += 1
            signals.append("low_signal_confidence")

        risk = "low"
        if score >= 5:
            risk = "high"
        elif score >= 3:
            risk = "moderate"

        return {
            "athlete_id": athlete_id,
            "assessed_at": datetime.now().isoformat(),
            "risk_level": risk,
            "score": score,
            "signals": signals,
            "escalate_to_coach": score >= 4,
            "coach_message": self._coach_message(risk, signals, quality_avg)
        }

    def _quality_average(self, quality_rows):
        values = [row["avg_confidence"] for row in quality_rows if row["avg_confidence"] is not None]
        return round(sum(values) / len(values), 2) if values else 0.0

    def _coach_message(self, risk, signals, quality_avg):
        if risk == "low":
            return "No escalation. Continue monitoring."
        return (
            f"Fatigue risk {risk.upper()} based on {', '.join(signals)}. "
            f"Average signal confidence: {quality_avg:.2f}."
        )


def demo():
    from longitudinal_data_model import LongitudinalDataModel

    model = LongitudinalDataModel()
    athlete_id = "demo-athlete-001"
    model.update_training_state(athlete_id, {
        "responder_class": "positive_responder",
        "masters_adjustment": "higher_recovery_density",
        "female_cycle_awareness": "enabled",
        "resource_profile": "low_resource",
        "experience_band": "experienced",
        "environmental_profile": "heat_sensitive",
        "rolling_atl": 96.0,
        "rolling_ctl": 80.0,
        "rolling_tsb": -16.0,
        "cp_trend": 312,
        "w_prime_trend": 19800,
        "durability_index": 0.69,
        "hr_decoupling_trend": 4.8,
        "rpe_delta_trend": 1.3,
        "compliance_rate": 0.68,
        "season_progression": "{}"
    })
    detector = FatigueOverreachingDetector(model)
    result = detector.assess(athlete_id, {"mood": "flat", "energy": "low"})
    print("[OK] Fatigue detector ready")
    print(f"Risk: {result['risk_level']}")
    print(f"Score: {result['score']}")
    print(f"Escalate: {result['escalate_to_coach']}")


if __name__ == "__main__":
    demo()

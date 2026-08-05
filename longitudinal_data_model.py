#!/usr/bin/env python3
"""
Longitudinal rider profile model.

Accumulates session-level data into rider-specific history for load, response,
durability, compliance, and progression tracking.
"""

import json
import sqlite3
from datetime import datetime


class LongitudinalDataModel:
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.setup_schema()

    def setup_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS rider_profiles (
                athlete_id TEXT PRIMARY KEY,
                athlete_name TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS rider_profile_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                metric_unit TEXT,
                source_session_id TEXT,
                source_quality TEXT,
                recorded_at TEXT,
                details_json TEXT,
                FOREIGN KEY (athlete_id) REFERENCES rider_profiles(athlete_id)
            );

            CREATE TABLE IF NOT EXISTS rider_metric_quality (
                quality_id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                confidence_score REAL,
                quality_notes TEXT,
                derived_from TEXT,
                recorded_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES rider_profiles(athlete_id)
            );

            CREATE TABLE IF NOT EXISTS rider_history_flags (
                flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id TEXT NOT NULL,
                flag_type TEXT NOT NULL,
                flag_value TEXT,
                details TEXT,
                detected_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES rider_profiles(athlete_id)
            );

            CREATE TABLE IF NOT EXISTS rider_training_state (
                athlete_id TEXT PRIMARY KEY,
                responder_class TEXT,
                masters_adjustment TEXT,
                female_cycle_awareness TEXT,
                resource_profile TEXT,
                experience_band TEXT,
                environmental_profile TEXT,
                rolling_atl REAL,
                rolling_ctl REAL,
                rolling_tsb REAL,
                cp_trend REAL,
                w_prime_trend REAL,
                durability_index REAL,
                hr_decoupling_trend REAL,
                rpe_delta_trend REAL,
                compliance_rate REAL,
                season_progression TEXT,
                updated_at TEXT,
                FOREIGN KEY (athlete_id) REFERENCES rider_profiles(athlete_id)
            );
        """)

    def upsert_athlete(self, athlete_id, athlete_name=None):
        now = datetime.now().isoformat()
        self.conn.execute("""
            INSERT INTO rider_profiles (athlete_id, athlete_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                athlete_name = COALESCE(excluded.athlete_name, rider_profiles.athlete_name),
                updated_at = excluded.updated_at
        """, (athlete_id, athlete_name, now, now))
        self.conn.commit()

    def record_session(self, athlete_id, session_id, metrics):
        self.upsert_athlete(athlete_id, metrics.get("athlete_name"))
        now = datetime.now().isoformat()

        for metric_name, payload in metrics.items():
            if metric_name == "athlete_name":
                continue
            if isinstance(payload, list):
                continue
            if isinstance(payload, dict):
                value = payload.get("value")
                unit = payload.get("unit")
                quality = payload.get("quality")
                details = payload.get("details")
            else:
                value = payload
                unit = None
                quality = None
                details = None

            normalized_value, confidence_score, quality_notes = self.normalize_metric(metric_name, value, quality)

            self.conn.execute("""
                INSERT INTO rider_profile_metrics (
                    athlete_id, metric_name, metric_value, metric_unit,
                    source_session_id, source_quality, recorded_at, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                athlete_id, metric_name, normalized_value, unit, session_id, quality, now,
                json.dumps(details) if details is not None else None
            ))

            self.conn.execute("""
                INSERT INTO rider_metric_quality (
                    athlete_id, metric_name, confidence_score, quality_notes,
                    derived_from, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                athlete_id, metric_name, confidence_score, quality_notes, session_id, now
            ))

        self.conn.commit()

    def normalize_metric(self, metric_name, value, quality):
        notes = []
        confidence = 1.0

        if value is None:
            return None, 0.0, "missing_data"

        if metric_name in ("rolling_atl", "rolling_ctl", "rolling_tsb", "durability_index", "hr_decoupling_trend", "rpe_delta_trend", "compliance_rate"):
            confidence -= 0.1 if quality != "lab" else 0.0

        if metric_name == "hr_series" and isinstance(value, list):
            filtered = [v for v in value if isinstance(v, (int, float)) and 30 <= v <= 230]
            removed = len(value) - len(filtered)
            if removed:
                notes.append("sensor_dropout_recovery")
                notes.append(f"removed_{removed}_outliers")
                confidence -= 0.2
            value = sum(filtered) / len(filtered) if filtered else None
            if value is None:
                return None, 0.0, "insufficient_signal"

        if isinstance(value, (int, float)):
            if metric_name in ("rolling_atl", "rolling_ctl", "rolling_tsb") and abs(value) > 500:
                notes.append("outlier_clamped")
                confidence -= 0.3
                value = max(min(value, 500), -500)
            if metric_name == "compliance_rate" and not (0 <= value <= 1):
                notes.append("compliance_normalized")
                confidence -= 0.2
                value = max(min(value, 1), 0)
        else:
            notes.append("non_scalar_signal")
            confidence -= 0.5

        confidence = max(0.0, min(1.0, confidence))
        return value, confidence, ",".join(notes) if notes else "ok"

    def update_training_state(self, athlete_id, state):
        self.upsert_athlete(athlete_id)
        now = datetime.now().isoformat()
        self.conn.execute("""
            INSERT INTO rider_training_state (
                athlete_id, responder_class, masters_adjustment,
                female_cycle_awareness, resource_profile, experience_band,
                environmental_profile, rolling_atl, rolling_ctl, rolling_tsb,
                cp_trend, w_prime_trend, durability_index, hr_decoupling_trend,
                rpe_delta_trend, compliance_rate, season_progression, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                responder_class = excluded.responder_class,
                masters_adjustment = excluded.masters_adjustment,
                female_cycle_awareness = excluded.female_cycle_awareness,
                resource_profile = excluded.resource_profile,
                experience_band = excluded.experience_band,
                environmental_profile = excluded.environmental_profile,
                rolling_atl = excluded.rolling_atl,
                rolling_ctl = excluded.rolling_ctl,
                rolling_tsb = excluded.rolling_tsb,
                cp_trend = excluded.cp_trend,
                w_prime_trend = excluded.w_prime_trend,
                durability_index = excluded.durability_index,
                hr_decoupling_trend = excluded.hr_decoupling_trend,
                rpe_delta_trend = excluded.rpe_delta_trend,
                compliance_rate = excluded.compliance_rate,
                season_progression = excluded.season_progression,
                updated_at = excluded.updated_at
        """, (
            athlete_id,
            state.get("responder_class"),
            state.get("masters_adjustment"),
            state.get("female_cycle_awareness"),
            state.get("resource_profile"),
            state.get("experience_band"),
            state.get("environmental_profile"),
            state.get("rolling_atl"),
            state.get("rolling_ctl"),
            state.get("rolling_tsb"),
            state.get("cp_trend"),
            state.get("w_prime_trend"),
            state.get("durability_index"),
            state.get("hr_decoupling_trend"),
            state.get("rpe_delta_trend"),
            state.get("compliance_rate"),
            state.get("season_progression"),
            now
        ))
        self.conn.commit()

    def flag_pattern(self, athlete_id, flag_type, flag_value, details):
        self.upsert_athlete(athlete_id)
        self.conn.execute("""
            INSERT INTO rider_history_flags (
                athlete_id, flag_type, flag_value, details, detected_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (athlete_id, flag_type, flag_value, details, datetime.now().isoformat()))
        self.conn.commit()

    def get_profile_summary(self, athlete_id):
        profile = self.conn.execute("""
            SELECT * FROM rider_training_state WHERE athlete_id = ?
        """, (athlete_id,)).fetchone()
        history = self.conn.execute("""
            SELECT metric_name, COUNT(*) AS points, MAX(recorded_at) AS last_seen
            FROM rider_profile_metrics
            WHERE athlete_id = ?
            GROUP BY metric_name
            ORDER BY metric_name
        """, (athlete_id,)).fetchall()
        flags = self.conn.execute("""
            SELECT flag_type, flag_value, details, detected_at
            FROM rider_history_flags
            WHERE athlete_id = ?
            ORDER BY detected_at DESC
        """, (athlete_id,)).fetchall()
        quality = self.conn.execute("""
            SELECT metric_name, AVG(confidence_score) AS avg_confidence, MAX(recorded_at) AS last_seen
            FROM rider_metric_quality
            WHERE athlete_id = ?
            GROUP BY metric_name
            ORDER BY metric_name
        """, (athlete_id,)).fetchall()
        return profile, history, flags, quality


def build_sample_state(metrics):
    load_history = metrics.get("training_load_history", [])
    compliance_history = metrics.get("compliance_history", [])
    return {
        "responder_class": metrics.get("responder_class", "unknown"),
        "masters_adjustment": metrics.get("masters_adjustment", "standard"),
        "female_cycle_awareness": metrics.get("female_cycle_awareness", "off"),
        "resource_profile": metrics.get("resource_profile", "standard"),
        "experience_band": metrics.get("experience_band", "intermediate"),
        "environmental_profile": metrics.get("environmental_profile", "neutral"),
        "rolling_atl": metrics.get("rolling_atl"),
        "rolling_ctl": metrics.get("rolling_ctl"),
        "rolling_tsb": metrics.get("rolling_tsb"),
        "cp_trend": metrics.get("cp_trend"),
        "w_prime_trend": metrics.get("w_prime_trend"),
        "durability_index": metrics.get("durability_index"),
        "hr_decoupling_trend": metrics.get("hr_decoupling_trend"),
        "rpe_delta_trend": metrics.get("rpe_delta_trend"),
        "compliance_rate": metrics.get("compliance_rate"),
        "season_progression": json.dumps({
            "load_points": len(load_history),
            "compliance_points": len(compliance_history)
        })
    }


def main():
    model = LongitudinalDataModel()
    athlete_id = "demo-athlete-001"
    model.record_session(athlete_id, "session-001", {
        "athlete_name": "Demo Rider",
        "rolling_atl": {"value": 72.4, "unit": "au", "quality": "field"},
        "rolling_ctl": {"value": 81.2, "unit": "au", "quality": "field"},
        "rolling_tsb": {"value": -8.8, "unit": "au", "quality": "field"},
        "cp_trend": {"value": 312, "unit": "w", "quality": "lab"},
        "w_prime_trend": {"value": 19800, "unit": "j", "quality": "lab"},
        "durability_index": {"value": 0.84, "unit": "ratio", "quality": "field"},
        "hr_decoupling_trend": {"value": 3.1, "unit": "pct", "quality": "field"},
        "rpe_delta_trend": {"value": 0.6, "unit": "rpe", "quality": "field"},
        "compliance_rate": {"value": 0.9, "unit": "ratio", "quality": "log"},
        "hr_series": {"value": [142, 145, 0, 147, 251, 149], "unit": "bpm", "quality": "field"},
        "training_load_history": [1, 2, 3],
        "compliance_history": [1, 1, 0]
    })
    state = build_sample_state({
        "responder_class": "positive_responder",
        "masters_adjustment": "higher_recovery_density",
        "female_cycle_awareness": "enabled",
        "resource_profile": "low_resource",
        "experience_band": "experienced",
        "environmental_profile": "heat_sensitive",
        "rolling_atl": 72.4,
        "rolling_ctl": 81.2,
        "rolling_tsb": -8.8,
        "cp_trend": 312,
        "w_prime_trend": 19800,
        "durability_index": 0.84,
        "hr_decoupling_trend": 3.1,
        "rpe_delta_trend": 0.6,
        "compliance_rate": 0.9,
        "hr_series": [142, 145, 0, 147, 251, 149],
        "training_load_history": [1, 2, 3],
        "compliance_history": [1, 1, 0]
    })
    model.update_training_state(athlete_id, state)
    model.flag_pattern(athlete_id, "responder_shift", "positive_to_flat", "Response flattened after two dense blocks.")
    profile, history, flags, quality = model.get_profile_summary(athlete_id)
    print("[OK] Longitudinal data model ready")
    print(f"Profile updated: {profile['updated_at'] if profile else 'n/a'}")
    print(f"Tracked metrics: {len(history)}")
    print(f"Flags: {len(flags)}")
    print(f"Quality metrics: {len(quality)}")


if __name__ == "__main__":
    main()

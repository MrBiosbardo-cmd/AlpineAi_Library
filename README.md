# AlpineAI Research Library

A structured, evidence-ranked knowledge library powering the Alpine AI cycling coach.

## Layer 3

- `longitudinal_data_model.py` accumulates rider-specific history for ATL/CTL/TSB, CP/W', durability, HR decoupling, RPE drift, compliance, and progression tracking.

## Layer 4

- `training_plan_generator.py` builds phase-aware, low-resource-friendly weekly plans with conservative defaults, rule citations, and confidence notes when onboarding data is sparse.
- `plan_adaptation_engine.py` revises those plans in real time when sessions are missed, stress rises, performance drops, or health status changes.
- `fatigue_overreaching_detector.py` scores converging fatigue signals and escalates to the coach when risk becomes moderate or high.

## Folder Structure

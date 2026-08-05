# Alpine AI — Coaching Metadata Schema
*Version 2.0 — Genuine Outstanding Coaching Intelligence*

Every field in this schema exists for a reason: it either drives a coaching decision,
filters a rule to the right rider, or protects the AI from giving bad advice.

---

## Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `Paper_ID` | string | Unique identifier, format `ALP-YYYY-NNNN` |
| `Title` | string | Document title |
| `Authors` | string | Semicolon-separated author names |
| `Year` | string | Publication year |
| `Domain` | string | Primary topic area (see Domain Taxonomy below) |
| `Sub_Topic` | string | Specific sub-domain (e.g. `HRV_Monitoring`) |
| `Evidence_Type` | enum | `journal_article \| systematic_review \| meta_analysis \| consensus_statement \| book \| book_chapter` |
| `Document_Type` | enum | `journal_article \| book \| book_chapter \| report \| thesis \| other` |
| `Doc_Type_Confidence` | enum | `high \| medium \| low` |
| `Manual_Review_Required` | bool | `yes \| no` — flagged when type confidence is low |
| `Evidence_Score` | int 1–5 | Quality of evidence: 5=meta-analysis, 4=RCT, 3=cohort, 2=case/opinion, 1=anecdote |
| `Source_Priority` | enum | `journal \| book` — journals outrank books for rule weight |
| `Source` | string | Journal name, book title, or publisher |

---

## Applicability Flags

These flags allow the coaching engine to filter rules to the right rider context.

| Field | Type | Description |
|-------|------|-------------|
| `Cycling_Specificity` | enum | `High \| Medium \| Low` — how cycling-specific the findings are |
| `Elite_Applicability` | enum | `High \| Medium \| Low` — relevance to elite riders |
| `Resource_Level` | enum | `Low \| Medium \| High` — equipment/lab resources needed to apply this |
| `Female_Physiology_Relevant` | enum | `yes \| no \| partial` — findings specific to female physiology |
| `Altitude_Heat_Relevant` | enum | `yes \| no \| partial` — findings on altitude or heat adaptation |
| `Youth_Applicable` | enum | `yes \| no \| partial` — findings applicable to riders under 18 |
| `Masters_Applicable` | enum | `yes \| no \| partial` — findings applicable to riders 35+ |
| `Durability_Relevant` | bool | `yes \| no` — findings about multi-hour or repeated-day performance |

---

## Core Content Fields

| Field | Type | Description |
|-------|------|-------------|
| `Main_Finding` | string | Key result in 2–3 sentences. What did the paper actually find? |
| `Practical_Application` | string | Concrete IF-THEN coaching actions derived from the finding |
| `Low_Resource_Applicability` | string | How to apply this finding using only RPE, wellness scores, distance, and time — **no power meter, no HRM** |

---

## Coaching Knowledge Nodes

These are the primary inputs to the coaching rule engine. Each field holds a pipe-separated list of declarative statements extracted from the paper.

| Field | Format | Purpose |
|-------|--------|---------|
| `Coaching_Principles` | `Principle A \| Principle B` | Durable coaching truths the paper supports (e.g. *Progressive overload before intensification*) |
| `Constraints` | `Rule A \| Rule B` | Hard rules the coach must **never** violate (e.g. *No more than 2 hard sessions per week*) |
| `Decision_Rules` | `IF X THEN Y \| IF A THEN B` | Executable IF-THEN logic for the rule engine (e.g. *IF ATL > CTL × 1.3 THEN reduce weekly load 20%*) |
| `Individualization_Factors` | `Factor A \| Factor B` | Variables that modify how the rule applies to a specific rider (e.g. *Menstrual cycle phase*, *Altitude responder status*) |
| `Recovery_Heuristics` | `Rule A \| Rule B` | Specific recovery timing guidelines (e.g. *48h minimum between VO2max efforts*, *Sleep > 7h before key sessions*) |

### Why These Five Node Types?

- **Coaching_Principles** — The "why" behind every rule. They justify prescriptions when the rider asks.
- **Constraints** — The safety net. The AI never overrides a constraint from a high-evidence paper.
- **Decision_Rules** — The engine's raw code. These are compiled into the coaching rule engine directly.
- **Individualization_Factors** — What makes coaching personal. The more factors we know, the more individualized the plan.
- **Recovery_Heuristics** — Often underspecified in generic programs. These ensure the AI prescribes recovery as precisely as load.

---

## Governance Fields

| Field | Type | Description |
|-------|------|-------------|
| `Superseded_By` | string | `Paper_ID` of a newer paper that overrides findings in this one |
| `Confidence_Ceiling` | int 1–5 | Maximum Evidence_Score applicable when the rider has **no power meter or HRM**. Reduced automatically: -1 if power measurement required, -2 if lab testing required |

---

## Search & Linkage Fields

| Field | Type | Description |
|-------|------|-------------|
| `Tags` | comma-separated | Keywords for full-text search |
| `Related_Papers` | semicolon-separated | `AuthorLastName_Year_ShortDescriptor` references to connected papers |
| `Linked_Features` | comma-separated | Alpine AI features this paper informs: `Recovery Score \| Adaptive FTP \| Fatigue Warnings \| Training Load Alerts \| Nutrition Timing Engine \| Environmental Adaptation` |

---

## Provenance Fields

| Field | Type | Description |
|-------|------|-------------|
| `PDF_Filename` | path | Relative path under `PDF Processed/` |
| `Obsidian_Path` | path | Relative path under `Notes/` |
| `Acquisition_Status` | string | `Extracted & Organized \| Manual Entry \| Needs Review` |
| `Date_Added` | ISO date | When the document was indexed |

---

## Domain Taxonomy

Preferred domain values (use these exactly for consistent rule routing):

| Domain | Description |
|--------|-------------|
| `Core_Physiology` | Energy systems, VO2max, lactate, muscle physiology |
| `Training_Prescription` | Periodization, HIIT, SIT, TID, training zones |
| `Load_Monitoring` | HRV, TSS, ACWR, RPE, fatigue tracking |
| `Recovery` | Sleep, active recovery, flexibility, recovery modalities |
| `Nutrition` | Fueling, hydration, supplements, REDs |
| `Psychology` | Motivation, anxiety, mental training, self-efficacy |
| `Cycling_Science` | Aerodynamics, power meters, bike fit, race strategy |
| `Female_Physiology` | Menstrual cycle, bone health, hormonal effects on performance |
| `Environmental` | Altitude adaptation, heat acclimatization |
| `Durability` | Multi-hour performance, repeated-day fatigue, ultra-endurance |
| `Injury_Prevention` | Overuse injuries, load management, return-to-sport |
| `Rehabilitation` | Sports injury recovery, clinical interventions |
| `Talent_Identification_Development` | Youth development, LTAD, talent identification |
| `AI_Data_Science` | Machine learning in sports, performance analytics |
| `General_Coaching_Science` | Coaching education, pedagogy |
| `Sports_Philosophy_Ethics` | Ethics, doping, fair play |

---

## Evidence Score Reference

| Score | Meaning | Examples |
|-------|---------|---------|
| 5 | Meta-analysis or systematic review with pooled data | Cochrane review, multi-study meta-analysis |
| 4 | RCT or well-designed experimental study | Randomized crossover trial, n > 20 |
| 3 | Good cohort study or observational study | Prospective cohort, n > 10, controlled conditions |
| 2 | Case study, small study, or expert opinion | n < 10, retrospective, expert consensus |
| 1 | Anecdote, editorial, or narrative opinion | Blog post level, no controls |

---

## Confidence Ceiling Logic

The `Confidence_Ceiling` prevents the AI from citing high-evidence rules in low-resource situations where the measurement tools required to apply the rule don't exist.

```
confidence_ceiling = evidence_strength
  - 1  IF findings require power meter data
  - 2  IF findings require lab testing (VO2max, lactate, DEXA)
  minimum = 1
```

**Example:** A meta-analysis (Evidence_Score=5) on VO2max testing protocols has `Confidence_Ceiling=3` because VO2max testing requires a lab (-2). The AI will not prescribe VO2max-derived training zones to a rider with no testing history.

---

## Coaching Node Format Examples

### Decision Rules
```
IF ATL > CTL * 1.3 THEN reduce weekly TSS by 20%
IF resting HR > baseline + 7bpm THEN flag recovery risk
IF weekly RPE avg > 8 for 2 consecutive weeks THEN initiate deload
```

### Constraints
```
No more than 2 sessions above threshold per week
Always schedule 48h recovery after race simulation efforts
Do not increase weekly training volume by more than 10% per week
```

### Individualization Factors
```
Menstrual cycle phase (follicular vs luteal affects recovery tolerance)
Altitude responder status (high vs low hemoglobin response)
Training history (years of consistent training > 3 = higher stress tolerance)
Age (masters riders need longer recovery between hard sessions)
```

### Recovery Heuristics
```
48h minimum between VO2max efforts
Sleep > 7h on nights before key sessions
Easy spin recommended 24h after a race
At least 1 complete rest day per week during base phase
```

---

*Schema version 2.0 — Alpine AI Research Library*
*Generated 2026-08-05*

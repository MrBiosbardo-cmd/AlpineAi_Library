#!/usr/bin/env python3
"""
Coaching Rule Engine: Converts Layer 2 knowledge nodes into decision rules.
Handles rule selection, conflict resolution, and athlete context mapping.
"""

import csv
import sqlite3
from datetime import datetime
from collections import defaultdict

KNOWLEDGE_NODES = "00_Library_Index/Knowledge_Nodes.csv"

class CoachingRuleEngine:
    """Manages conversion of knowledge nodes to coaching rules."""
    
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.setup_schema()
    
    def setup_schema(self):
        """Create rule engine tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS coaching_rules (
                rule_id TEXT PRIMARY KEY,
                node_id TEXT,
                rule_type TEXT,
                domain TEXT,
                condition TEXT,
                action TEXT,
                constraint_level TEXT,
                precedence INTEGER,
                confidence_score REAL,
                applies_to_contexts TEXT,
                date_created TEXT
            );
            
            CREATE TABLE IF NOT EXISTS rule_conflicts (
                conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id_1 TEXT,
                rule_id_2 TEXT,
                conflict_type TEXT,
                resolution_strategy TEXT,
                date_flagged TEXT
            );
            
            CREATE TABLE IF NOT EXISTS athlete_context (
                context_id TEXT PRIMARY KEY,
                athlete_id TEXT,
                sex TEXT,
                age INTEGER,
                maturity_stage TEXT,
                competitive_level TEXT,
                injury_status TEXT,
                recovery_capacity TEXT,
                constraints TEXT,
                date_created TEXT
            );
            
            CREATE TABLE IF NOT EXISTS rule_application_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT,
                context_id TEXT,
                decision TEXT,
                rationale TEXT,
                applied BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
    def load_nodes_and_convert(self):
        """Load knowledge nodes and convert them to rules."""
        rules_created = 0
        
        with open(KNOWLEDGE_NODES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                node_id = row.get("Paper_ID", "").strip('"')
                node_type = row.get("Node_Type", "").strip('"')
                node_category = row.get("Node_Category", "").strip('"')
                principle = row.get("Principle_Rule_Constraint", "").strip('"')
                description = row.get("Description", "").strip('"')
                action = row.get("Coaching_Action", "").strip('"')
                evidence_strength = row.get("Evidence_Strength", "").strip('"')
                
                # Map node type to rule type
                rule_type, constraint_level, precedence = self._map_node_to_rule(node_type)
                confidence_score = 1.0 if evidence_strength == "high" else 0.7
                
                # Build rule condition and action
                condition = f"Context: {description}"
                action_text = action
                
                rule_id = f"RULE-{node_id}"
                
                self.conn.execute("""
                    INSERT OR IGNORE INTO coaching_rules (
                        rule_id, node_id, rule_type, domain,
                        condition, action, constraint_level,
                        precedence, confidence_score, applies_to_contexts, date_created
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule_id, node_id, rule_type, node_category,
                    condition, action_text, constraint_level,
                    precedence, confidence_score, "all_contexts", datetime.now().isoformat()
                ))
                rules_created += 1
        
        self.conn.commit()
        return rules_created
    
    def _map_node_to_rule(self, node_type):
        """Map node type to rule type, constraint level, and precedence."""
        mapping = {
            "Coaching_Principle": ("principle", "should", 2),
            "Constraint": ("constraint", "must", 1),
            "Decision_Rule": ("decision", "should", 2),
            "Individualization_Factor": ("contextual", "consider", 3),
            "Recovery_Heuristic": ("heuristic", "may", 4),
            "Durability_Principle": ("principle", "should", 2),
            "Nutrition_Principle": ("principle", "should", 2),
            "Nutrition_Constraint": ("constraint", "must", 1),
            "Female_Physiology_Principle": ("principle", "should", 2),
            "Female_Physiology_Constraint": ("constraint", "must", 1),
            "Heat_Altitude_Principle": ("principle", "should", 2),
        }
        return mapping.get(node_type, ("heuristic", "may", 4))
    
    def detect_conflicts(self):
        """Detect rule conflicts and flag them for resolution."""
        conflicts = []
        
        # Query rules ordered by precedence
        cursor = self.conn.execute("""
            SELECT rule_id, domain, constraint_level, precedence
            FROM coaching_rules
            ORDER BY precedence ASC
        """)
        rules = cursor.fetchall()
        
        # Simple conflict detection: overlapping domains with conflicting constraints
        domain_rules = defaultdict(list)
        for rule in rules:
            domain_rules[rule['domain']].append(rule)
        
        for domain, domain_rule_list in domain_rules.items():
            if len(domain_rule_list) > 1:
                for i, rule1 in enumerate(domain_rule_list):
                    for rule2 in domain_rule_list[i+1:]:
                        # Check for potential conflicts
                        if rule1['constraint_level'] == "must" and rule2['constraint_level'] == "must":
                            self.conn.execute("""
                                INSERT INTO rule_conflicts (
                                    rule_id_1, rule_id_2, conflict_type, resolution_strategy, date_flagged
                                ) VALUES (?, ?, ?, ?, ?)
                            """, (
                                rule1['rule_id'], rule2['rule_id'],
                                "overlapping_constraints",
                                f"Apply rule {rule1['rule_id']} (lower precedence) first",
                                datetime.now().isoformat()
                            ))
                            conflicts.append((rule1['rule_id'], rule2['rule_id']))
        
        self.conn.commit()
        return len(conflicts)
    
    def add_athlete_context(self, context_id, sex, age, competitive_level, injury_status, recovery_capacity):
        """Add an athlete context for rule application."""
        maturity = self._compute_maturity(age)
        self.conn.execute("""
            INSERT OR IGNORE INTO athlete_context (
                context_id, athlete_id, sex, age, maturity_stage,
                competitive_level, injury_status, recovery_capacity,
                date_created
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            context_id, context_id, sex, age, maturity,
            competitive_level, injury_status, recovery_capacity,
            datetime.now().isoformat()
        ))
        self.conn.commit()
    
    def _compute_maturity(self, age):
        """Classify maturity stage based on age."""
        if age is None:
            return "unknown"
        elif age < 18:
            return "youth"
        elif age < 24:
            return "junior"
        else:
            return "senior"
    
    def select_rules_for_context(self, context_id):
        """Select applicable rules for an athlete context."""
        context = self.conn.execute(
            "SELECT * FROM athlete_context WHERE context_id = ?",
            (context_id,)
        ).fetchone()
        
        if not context:
            return []
        
        # Start with all constraint rules (must apply)
        cursor = self.conn.execute("""
            SELECT rule_id, node_id, rule_type, action, precedence, constraint_level
            FROM coaching_rules
            WHERE constraint_level = 'must'
            ORDER BY precedence ASC
        """)
        rules = list(cursor.fetchall())
        
        # Add contextual rules based on athlete profile
        if context['sex'] == 'female':
            cursor = self.conn.execute("""
                SELECT rule_id, node_id, rule_type, action, precedence, constraint_level
                FROM coaching_rules
                WHERE domain LIKE '%Female%' AND constraint_level IN ('should', 'consider')
                ORDER BY precedence ASC
            """)
            rules.extend(cursor.fetchall())
        
        # Add recovery/injury-specific rules
        if context['injury_status'] != 'none':
            cursor = self.conn.execute("""
                SELECT rule_id, node_id, rule_type, action, precedence, constraint_level
                FROM coaching_rules
                WHERE domain LIKE '%Recovery%' AND constraint_level IN ('should', 'may')
                ORDER BY precedence ASC
            """)
            rules.extend(cursor.fetchall())
        
        # Add rules based on competitive level
        if context['competitive_level'] == 'elite':
            cursor = self.conn.execute("""
                SELECT rule_id, node_id, rule_type, action, precedence, constraint_level
                FROM coaching_rules
                WHERE rule_type IN ('principle', 'decision')
                ORDER BY precedence ASC
            """)
            rules.extend(cursor.fetchall())
        
        # Convert rows to dicts
        result = []
        seen = set()
        for rule in rules:
            rule_dict = dict(rule)
            if rule_dict['rule_id'] not in seen:
                result.append(rule_dict)
                seen.add(rule_dict['rule_id'])
        return result
    
    def apply_rules(self, context_id, domain=None):
        """Apply rules to an athlete context and log decisions."""
        rules = self.select_rules_for_context(context_id)
        
        decisions = []
        for rule in rules:
            if domain and rule['rule_type'] != domain:
                continue
            
            applied = rule['constraint_level'] in ('must', 'should')
            decision = f"{rule['rule_type'].upper()}: {rule['action'][:80]}..."
            rationale = f"Applied rule {rule['rule_id']} from node {rule['node_id']}"
            
            self.conn.execute("""
                INSERT INTO rule_application_log (
                    rule_id, context_id, decision, rationale, applied
                ) VALUES (?, ?, ?, ?, ?)
            """, (rule['rule_id'], context_id, decision, rationale, applied))
            
            decisions.append({
                'rule_id': rule['rule_id'],
                'decision': decision,
                'applied': applied
            })
        
        self.conn.commit()
        return decisions
    
    def get_rule_stats(self):
        """Get summary statistics about the rule engine."""
        stats = {}
        
        # Count by rule type
        cursor = self.conn.execute("""
            SELECT rule_type, COUNT(*) as count
            FROM coaching_rules
            GROUP BY rule_type
        """)
        stats['rules_by_type'] = dict(cursor.fetchall())
        
        # Count by constraint level
        cursor = self.conn.execute("""
            SELECT constraint_level, COUNT(*) as count
            FROM coaching_rules
            GROUP BY constraint_level
        """)
        stats['rules_by_constraint'] = dict(cursor.fetchall())
        
        # Conflict count
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM rule_conflicts")
        stats['total_conflicts'] = cursor.fetchone()['count']
        
        # Average confidence
        cursor = self.conn.execute("SELECT AVG(confidence_score) as avg FROM coaching_rules")
        stats['avg_confidence'] = cursor.fetchone()['avg']
        
        return stats


def main():
    """Demo the coaching rule engine."""
    engine = CoachingRuleEngine()
    
    print("=== COACHING RULE ENGINE ===\n")
    
    # Load and convert nodes to rules
    print("1. Loading knowledge nodes and converting to rules...")
    rules_created = engine.load_nodes_and_convert()
    print(f"   Created {rules_created} coaching rules")
    
    # Detect conflicts
    print("\n2. Detecting rule conflicts...")
    conflicts = engine.detect_conflicts()
    print(f"   Detected {conflicts} potential conflicts")
    
    # Show rule stats
    print("\n3. Rule Engine Statistics:")
    stats = engine.get_rule_stats()
    print(f"   Rules by type:")
    for rule_type, count in stats['rules_by_type'].items():
        print(f"     {rule_type}: {count}")
    print(f"   Rules by constraint level:")
    for level, count in stats['rules_by_constraint'].items():
        print(f"     {level}: {count}")
    print(f"   Total conflicts: {stats['total_conflicts']}")
    print(f"   Average confidence: {stats['avg_confidence']:.2f}")
    
    # Create sample athlete contexts
    print("\n4. Creating sample athlete contexts...")
    contexts = [
        ("ATHLETE-001", "female", 24, "elite", "none", "high"),
        ("ATHLETE-002", "male", 19, "junior", "minor_injury", "medium"),
        ("ATHLETE-003", "female", 16, "youth", "none", "medium"),
    ]
    for context_id, sex, age, level, injury, recovery in contexts:
        engine.add_athlete_context(context_id, sex, age, level, injury, recovery)
        print(f"   Added context {context_id} ({sex}, age {age}, {level})")
    
    # Apply rules to contexts
    print("\n5. Applying rules to athlete contexts...")
    for context_id, _, _, _, _, _ in contexts:
        decisions = engine.apply_rules(context_id)
        applied_count = sum(1 for d in decisions if d['applied'])
        print(f"   {context_id}: {applied_count}/{len(decisions)} rules applied")
    
    # Show sample decisions
    print("\n6. Sample Decisions for ATHLETE-001 (elite female):")
    cursor = engine.conn.execute("""
        SELECT rule_id, decision, applied
        FROM rule_application_log
        WHERE context_id = 'ATHLETE-001'
        LIMIT 5
    """)
    for rule_id, decision, applied in cursor:
        status = "[APPLIED]" if applied else "[SKIPPED]"
        print(f"   {status} {decision}")
    
    print("\n[OK] Rule engine ready for deployment")


if __name__ == "__main__":
    main()

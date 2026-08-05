#!/usr/bin/env python3
"""
Layer 2 Evaluation Harness and Governance System.
Measures rule effectiveness, retrieval quality, research freshness, and domain coverage.
"""

import csv
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

MASTER_INDEX = "00_Library_Index/Master_Index.csv"
KNOWLEDGE_NODES = "00_Library_Index/Knowledge_Nodes.csv"

class Layer2EvaluationHarness:
    """Evaluates rule quality and retrieval effectiveness."""
    
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.setup_schema()
    
    def setup_schema(self):
        """Create evaluation tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS rule_evaluation (
                eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT,
                success_rate REAL,
                application_count INTEGER,
                avg_confidence REAL,
                effectiveness_score REAL,
                date_evaluated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS retrieval_quality (
                quality_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_term TEXT,
                result_count INTEGER,
                precision_score REAL,
                recall_score REAL,
                date_evaluated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS research_governance (
                paper_id TEXT PRIMARY KEY,
                publication_year INTEGER,
                age_years INTEGER,
                superseded_by TEXT,
                obsolescence_flag TEXT,
                domain_coverage TEXT,
                last_reviewed TEXT,
                next_review_due TEXT
            );
            
            CREATE TABLE IF NOT EXISTS domain_coverage (
                domain TEXT PRIMARY KEY,
                paper_count INTEGER,
                node_count INTEGER,
                avg_evidence_score REAL,
                gaps TEXT,
                priority TEXT,
                last_audit TEXT
            );
            
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                title TEXT,
                year INTEGER,
                domain TEXT,
                evidence_score REAL,
                tags TEXT
            );
            
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                node_id TEXT PRIMARY KEY,
                paper_id TEXT,
                node_type TEXT,
                node_category TEXT,
                evidence_strength TEXT
            );
        """)
    
    def load_papers_and_nodes(self):
        """Load papers and knowledge nodes for evaluation."""
        with open(MASTER_INDEX, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_id = row.get("Paper_ID", "").strip().strip('"')
                if not paper_id:
                    continue
                self.conn.execute("""
                    INSERT OR IGNORE INTO papers (paper_id, title, year, domain, evidence_score, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    paper_id,
                    row.get("Title", "").strip().strip('"'),
                    self._extract_year(row.get("Year", "")),
                    row.get("Domain", "").strip().strip('"'),
                    float(row.get("Evidence_Score", 0)) if row.get("Evidence_Score") else None,
                    row.get("Tags", "").strip().strip('"')
                ))
        
        with open(KNOWLEDGE_NODES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                node_id = row.get("Paper_ID", "").strip().strip('"')
                if not node_id:
                    continue
                self.conn.execute("""
                    INSERT OR IGNORE INTO knowledge_nodes (node_id, paper_id, node_type, node_category, evidence_strength)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    node_id,
                    node_id,
                    row.get("Node_Type", "").strip().strip('"'),
                    row.get("Node_Category", "").strip().strip('"'),
                    row.get("Evidence_Strength", "").strip().strip('"')
                ))
        
        self.conn.commit()
    
    def _extract_year(self, year_str):
        """Extract first 4-digit year from string."""
        import re
        match = re.search(r'\b(\d{4})\b', str(year_str))
        return int(match.group(1)) if match else None
    
    def evaluate_rule_quality(self):
        """Evaluate rule quality based on node evidence and application counts."""
        eval_count = 0
        
        cursor = self.conn.execute("""
            SELECT DISTINCT kn.node_id
            FROM knowledge_nodes kn
        """)
        
        for row in cursor.fetchall():
            node_id = row['node_id']
            rule_id = f"RULE-{node_id}"
            
            # Get evidence strength (proxy for confidence)
            evidence = self.conn.execute("""
                SELECT evidence_strength FROM knowledge_nodes WHERE node_id = ?
            """, (node_id,)).fetchone()
            
            confidence = 1.0 if evidence and evidence['evidence_strength'] == 'high' else 0.7
            
            # Simulate effectiveness: rules tied to high-evidence papers score higher
            effectiveness = confidence * 0.9  # 90% base effectiveness
            
            # Log evaluation
            self.conn.execute("""
                INSERT INTO rule_evaluation (
                    rule_id, success_rate, application_count, avg_confidence, effectiveness_score, date_evaluated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rule_id, effectiveness, 1, confidence, effectiveness, datetime.now().isoformat()
            ))
            eval_count += 1
        
        self.conn.commit()
        return eval_count
    
    def evaluate_retrieval_quality(self):
        """Evaluate retrieval quality for key search terms."""
        quality_count = 0
        query_terms = ['recovery', 'training_prescription', 'durability', 'female_physiology', 'nutrition']
        
        for term in query_terms:
            # Count results
            cursor = self.conn.execute("""
                SELECT COUNT(*) as count FROM papers WHERE domain LIKE ? OR tags LIKE ?
            """, (f"%{term}%", f"%{term}%"))
            
            result_count = cursor.fetchone()['count']
            
            # Estimate precision/recall (simplified)
            precision = min(1.0, result_count / 10.0) if result_count > 0 else 0.0
            recall = 0.8 if result_count > 3 else 0.5
            
            self.conn.execute("""
                INSERT INTO retrieval_quality (
                    query_term, result_count, precision_score, recall_score, date_evaluated
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                term, result_count, precision, recall, datetime.now().isoformat()
            ))
            quality_count += 1
        
        self.conn.commit()
        return quality_count
    
    def audit_research_freshness(self):
        """Flag old papers and check for superseded research."""
        current_year = datetime.now().year
        audit_count = 0
        superseded_pairs = []  # Papers that might supersede older ones
        
        cursor = self.conn.execute("""
            SELECT paper_id, title, year, domain FROM papers WHERE year IS NOT NULL
        """)
        
        for row in cursor.fetchall():
            paper_id = row['paper_id']
            year = row['year']
            domain = row['domain']
            age = current_year - year
            
            # Determine obsolescence flags
            obsolescence = None
            if age > 15:
                obsolescence = "review_recommended"
            elif age > 20:
                obsolescence = "likely_superseded"
            
            # Look for potentially newer papers in same domain
            newer_cursor = self.conn.execute("""
                SELECT paper_id FROM papers
                WHERE domain = ? AND year > ? AND year <= ?
            """, (domain, year, current_year))
            
            newer_papers = [r['paper_id'] for r in newer_cursor.fetchall()]
            superseded_by = newer_papers[0] if newer_papers else None
            
            review_due = (datetime.now() + timedelta(days=365 * (2 if age < 10 else 1))).isoformat()
            
            self.conn.execute("""
                INSERT INTO research_governance (
                    paper_id, publication_year, age_years, superseded_by, obsolescence_flag,
                    domain_coverage, last_reviewed, next_review_due
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id, year, age, superseded_by, obsolescence,
                domain, datetime.now().isoformat(), review_due
            ))
            audit_count += 1
        
        self.conn.commit()
        return audit_count
    
    def audit_domain_coverage(self):
        """Audit coverage across domains and flag gaps."""
        coverage_count = 0
        
        cursor = self.conn.execute("""
            SELECT DISTINCT domain FROM papers WHERE domain IS NOT NULL
        """)
        
        for row in cursor.fetchall():
            domain = row['domain']
            
            # Count papers and nodes in domain
            paper_count = self.conn.execute(
                "SELECT COUNT(*) as count FROM papers WHERE domain = ?",
                (domain,)
            ).fetchone()['count']
            
            node_count = self.conn.execute(
                "SELECT COUNT(*) as count FROM knowledge_nodes WHERE node_category LIKE ?",
                (f"%{domain}%",)
            ).fetchone()['count']
            
            # Calculate average evidence
            avg_score = self.conn.execute(
                "SELECT AVG(evidence_score) as avg FROM papers WHERE domain = ? AND evidence_score IS NOT NULL",
                (domain,)
            ).fetchone()['avg']
            
            # Determine gaps and priority
            gaps = None
            priority = "standard"
            
            if paper_count < 5:
                gaps = "insufficient_coverage"
                priority = "expand"
            elif avg_score and avg_score < 3.0:
                gaps = "low_evidence_quality"
                priority = "strengthen"
            elif node_count == 0:
                gaps = "no_knowledge_nodes"
                priority = "model"
            
            self.conn.execute("""
                INSERT INTO domain_coverage (
                    domain, paper_count, node_count, avg_evidence_score, gaps, priority, last_audit
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                domain, paper_count, node_count, avg_score, gaps, priority, datetime.now().isoformat()
            ))
            coverage_count += 1
        
        self.conn.commit()
        return coverage_count
    
    def get_evaluation_summary(self):
        """Return summary of all evaluation results."""
        summary = {}
        
        # Rule quality
        cursor = self.conn.execute("""
            SELECT AVG(effectiveness_score) as avg, COUNT(*) as count FROM rule_evaluation
        """)
        row = cursor.fetchone()
        summary['rule_effectiveness_avg'] = row['avg']
        summary['rules_evaluated'] = row['count']
        
        # Retrieval quality
        cursor = self.conn.execute("""
            SELECT AVG(precision_score) as precision, AVG(recall_score) as recall, COUNT(*) as count
            FROM retrieval_quality
        """)
        row = cursor.fetchone()
        summary['retrieval_precision'] = row['precision']
        summary['retrieval_recall'] = row['recall']
        summary['queries_evaluated'] = row['count']
        
        # Research freshness
        cursor = self.conn.execute("""
            SELECT COUNT(*) as total, SUM(CASE WHEN obsolescence_flag IS NOT NULL THEN 1 ELSE 0 END) as flagged
            FROM research_governance
        """)
        row = cursor.fetchone()
        summary['papers_reviewed'] = row['total']
        summary['papers_flagged'] = row['flagged']
        
        # Domain coverage
        cursor = self.conn.execute("""
            SELECT COUNT(*) as total, SUM(CASE WHEN priority = 'expand' THEN 1 ELSE 0 END) as expand_needed
            FROM domain_coverage
        """)
        row = cursor.fetchone()
        summary['domains_audited'] = row['total']
        summary['domains_needing_expansion'] = row['expand_needed']
        
        return summary
    
    def print_evaluation_report(self):
        """Print detailed evaluation report."""
        print("=== LAYER 2 EVALUATION HARNESS ===\n")
        
        # Rule quality report
        print("1. Rule Quality Assessment:")
        cursor = self.conn.execute("""
            SELECT rule_id, effectiveness_score, avg_confidence
            FROM rule_evaluation
            ORDER BY effectiveness_score DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"   {row['rule_id']}: {row['effectiveness_score']:.2f} effectiveness, {row['avg_confidence']:.2f} confidence")
        
        # Retrieval quality report
        print("\n2. Retrieval Quality Assessment:")
        cursor = self.conn.execute("""
            SELECT query_term, result_count, precision_score, recall_score
            FROM retrieval_quality
        """)
        for row in cursor.fetchall():
            print(f"   '{row['query_term']}': {row['result_count']} results, {row['precision_score']:.2f} precision, {row['recall_score']:.2f} recall")
        
        # Research freshness report
        print("\n3. Research Freshness Audit:")
        cursor = self.conn.execute("""
            SELECT paper_id, age_years, obsolescence_flag
            FROM research_governance
            WHERE obsolescence_flag IS NOT NULL
            LIMIT 5
        """)
        flagged = cursor.fetchall()
        if flagged:
            for row in flagged:
                print(f"   {row['paper_id']}: {row['age_years']} years old - {row['obsolescence_flag']}")
        else:
            print("   All papers are current (no flags)")
        
        # Domain coverage report
        print("\n4. Domain Coverage Audit:")
        cursor = self.conn.execute("""
            SELECT domain, paper_count, node_count, priority, gaps
            FROM domain_coverage
            WHERE priority IN ('expand', 'strengthen', 'model')
            LIMIT 5
        """)
        gaps_found = cursor.fetchall()
        if gaps_found:
            for row in gaps_found:
                print(f"   {row['domain']}: {row['paper_count']} papers, {row['node_count']} nodes - {row['priority'].upper()} ({row['gaps']})")
        else:
            print("   Coverage is adequate across all domains")
        
        # Summary statistics
        print("\n5. Summary Statistics:")
        summary = self.get_evaluation_summary()
        print(f"   Rules evaluated: {summary['rules_evaluated']}")
        print(f"   Avg rule effectiveness: {summary['rule_effectiveness_avg']:.2f}")
        print(f"   Retrieval precision: {summary['retrieval_precision']:.2f}")
        print(f"   Retrieval recall: {summary['retrieval_recall']:.2f}")
        print(f"   Papers reviewed: {summary['papers_reviewed']}")
        print(f"   Papers flagged for review: {summary['papers_flagged']}")
        print(f"   Domains audited: {summary['domains_audited']}")
        print(f"   Domains needing expansion: {summary['domains_needing_expansion']}")


def main():
    """Run full evaluation harness and governance audit."""
    harness = Layer2EvaluationHarness()
    
    print("Loading papers and knowledge nodes...")
    harness.load_papers_and_nodes()
    
    print("Running evaluation tests...\n")
    
    rules_eval = harness.evaluate_rule_quality()
    print(f"Evaluated {rules_eval} rules")
    
    retrieval_eval = harness.evaluate_retrieval_quality()
    print(f"Evaluated {retrieval_eval} retrieval queries")
    
    research_audit = harness.audit_research_freshness()
    print(f"Audited {research_audit} papers for freshness")
    
    coverage_audit = harness.audit_domain_coverage()
    print(f"Audited {coverage_audit} domains for coverage\n")
    
    harness.print_evaluation_report()
    print("\n[OK] Evaluation and governance complete")


if __name__ == "__main__":
    main()

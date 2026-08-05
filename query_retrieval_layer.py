#!/usr/bin/env python3
"""
Query functions for the retrieval layer.
Tests cross-linking, search, and recommendation logic.
"""

import csv
import sqlite3
import re
from collections import defaultdict

MASTER_INDEX = "00_Library_Index/Master_Index.csv"
KNOWLEDGE_NODES = "00_Library_Index/Knowledge_Nodes.csv"

def load_and_query():
    """Load data and demonstrate retrieval queries."""
    conn = sqlite3.connect(":memory:")
    
    # Create schema
    conn.execute("""
        CREATE TABLE papers (
            paper_id TEXT PRIMARY KEY,
            title TEXT,
            domain TEXT,
            evidence_score REAL,
            tags TEXT,
            related_papers TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            paper_id TEXT,
            node_type TEXT,
            node_category TEXT,
            principle TEXT,
            related_papers TEXT,
            tags TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE node_paper_links (
            node_id TEXT,
            linked_paper_id TEXT,
            link_type TEXT,
            PRIMARY KEY (node_id, linked_paper_id)
        )
    """)
    
    # Load papers
    with open(MASTER_INDEX, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row.get("Paper_ID", "").strip('"')
            conn.execute("""
                INSERT OR IGNORE INTO papers (
                    paper_id, title, domain, evidence_score, tags, related_papers
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                row.get("Title", "").strip('"'),
                row.get("Domain", "").strip('"'),
                float(row.get("Evidence_Score", 0)) if row.get("Evidence_Score") else None,
                row.get("Tags", "").strip('"'),
                row.get("Related_Papers", "").strip('"')
            ))
    
    # Load knowledge nodes
    with open(KNOWLEDGE_NODES, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row.get("Paper_ID", "").strip('"')
            conn.execute("""
                INSERT OR IGNORE INTO knowledge_nodes (
                    node_id, paper_id, node_type, node_category, principle, related_papers, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                paper_id,
                row.get("Node_Type", "").strip('"'),
                row.get("Node_Category", "").strip('"'),
                row.get("Principle_Rule_Constraint", "").strip('"'),
                row.get("Related_Papers", "").strip('"'),
                row.get("Tags", "").strip('"')
            ))
    
    conn.commit()
    
    # Query 1: Find all nodes and their types
    print("=== LAYER 2 RETRIEVAL: Node Inventory ===\n")
    cursor = conn.execute("""
        SELECT node_type, COUNT(*) as count
        FROM knowledge_nodes
        GROUP BY node_type
        ORDER BY count DESC
    """)
    for node_type, count in cursor:
        print(f"  {node_type}: {count}")
    
    # Query 2: Find nodes by category
    print("\n=== Nodes by Category ===\n")
    cursor = conn.execute("""
        SELECT node_category, COUNT(*) as count
        FROM knowledge_nodes
        GROUP BY node_category
        ORDER BY count DESC
    """)
    for category, count in cursor:
        print(f"  {category}: {count}")
    
    # Query 3: Find papers by domain
    print("\n=== Papers by Domain ===\n")
    cursor = conn.execute("""
        SELECT domain, COUNT(*) as count
        FROM papers
        GROUP BY domain
        ORDER BY count DESC
        LIMIT 10
    """)
    for domain, count in cursor:
        print(f"  {domain}: {count}")
    
    # Query 4: Highest-evidence papers
    print("\n=== Top Evidence Papers ===\n")
    cursor = conn.execute("""
        SELECT paper_id, title, evidence_score
        FROM papers
        WHERE evidence_score IS NOT NULL
        ORDER BY evidence_score DESC
        LIMIT 5
    """)
    for paper_id, title, score in cursor:
        print(f"  {paper_id}: {title[:50]}... (score: {score})")
    
    # Query 5: Node recommendations by principle
    print("\n=== Coaching Principles (with related papers) ===\n")
    cursor = conn.execute("""
        SELECT kn.node_id, kn.principle, kn.related_papers
        FROM knowledge_nodes kn
        WHERE kn.node_type = 'Coaching_Principle'
        ORDER BY kn.node_id
    """)
    for node_id, principle, related in cursor:
        related_count = len([p for p in related.split(',') if p.strip()]) if related else 0
        print(f"  {node_id}: {principle[:50]}... ({related_count} related papers)")
    
    # Query 6: Cross-domain recommendations
    print("\n=== Cross-domain Retrieval: Show papers for Durability node ===\n")
    cursor = conn.execute("""
        SELECT related_papers
        FROM knowledge_nodes
        WHERE node_id = 'ALP-2026-0072'
    """)
    row = cursor.fetchone()
    if row and row[0]:
        paper_ids = [p.strip() for p in row[0].split(',') if p.strip()]
        if paper_ids:
            placeholders = ','.join(['?' for _ in paper_ids])
            cursor = conn.execute(f"""
                SELECT paper_id, title, domain
                FROM papers
                WHERE paper_id IN ({placeholders})
            """, paper_ids)
            for paper_id, title, domain in cursor:
                print(f"  {paper_id}: {title[:50]}... ({domain})")
        else:
            print("  No linked papers found (IDs not matching)")
    else:
        print("  No related papers in node")
    
    # Query 7: Search by tag
    print("\n=== Tag-based Retrieval: 'recovery' ===\n")
    cursor = conn.execute("""
        SELECT node_id, node_type, tags
        FROM knowledge_nodes
        WHERE tags LIKE '%recovery%'
        LIMIT 5
    """)
    for node_id, node_type, tags in cursor:
        print(f"  {node_id} ({node_type}): {tags[:60]}...")
    
    print("\n[OK] Retrieval layer query demo complete")
    return conn

if __name__ == "__main__":
    conn = load_and_query()

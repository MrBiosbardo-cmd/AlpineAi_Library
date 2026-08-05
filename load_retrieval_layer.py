#!/usr/bin/env python3
"""
Load and index the retrieval layer for Layer 2.
Populates papers, knowledge_nodes, and cross-reference tables.
"""

import csv
import sqlite3
import re
from pathlib import Path

DB_PATH = "layer2_retrieval.db"
MASTER_INDEX = "00_Library_Index/Master_Index.csv"
KNOWLEDGE_NODES = "00_Library_Index/Knowledge_Nodes.csv"

def parse_year(year_str):
    """Extract first valid year from year_str, handling complex formats."""
    if not year_str:
        return None
    year_str = str(year_str).strip()
    # Try to extract the first 4-digit number
    match = re.search(r'\b(\d{4})\b', year_str)
    return int(match.group(1)) if match else None

def load_papers(conn):
    """Load papers from Master_Index.csv into the papers table."""
    count = 0
    with open(MASTER_INDEX, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT OR IGNORE INTO papers (
                    paper_id, title, authors, year, domain, sub_topic,
                    evidence_type, document_type, evidence_score,
                    main_finding, practical_application, tags,
                    related_papers, linked_features, date_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("Paper_ID", "").strip('"'),
                row.get("Title", "").strip('"'),
                row.get("Authors", "").strip('"'),
                parse_year(row.get("Year")),
                row.get("Domain", "").strip('"'),
                row.get("Sub_Topic", "").strip('"'),
                row.get("Evidence_Type", "").strip('"'),
                row.get("Document_Type", "").strip('"'),
                float(row.get("Evidence_Score", 0)) if row.get("Evidence_Score") else None,
                row.get("Main_Finding", "").strip('"'),
                row.get("Practical_Application", "").strip('"'),
                row.get("Tags", "").strip('"'),
                row.get("Related_Papers", "").strip('"'),
                row.get("Linked_Features", "").strip('"'),
                row.get("Date_Added", "").strip('"')
            ))
            count += 1
    conn.commit()
    print(f"Loaded {count} papers")

def load_knowledge_nodes(conn):
    """Load knowledge nodes from Knowledge_Nodes.csv into the knowledge_nodes table."""
    count = 0
    with open(KNOWLEDGE_NODES, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row.get("Paper_ID", "").strip('"')
            conn.execute("""
                INSERT OR IGNORE INTO knowledge_nodes (
                    node_id, paper_id, node_type, node_category,
                    principle, description, coaching_action, evidence_strength,
                    related_papers, tags, date_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,  # Use Paper_ID as node_id
                paper_id,
                row.get("Node_Type", "").strip('"'),
                row.get("Node_Category", "").strip('"'),
                row.get("Principle_Rule_Constraint", "").strip('"'),
                row.get("Description", "").strip('"'),
                row.get("Coaching_Action", "").strip('"'),
                row.get("Evidence_Strength", "").strip('"'),
                row.get("Related_Papers", "").strip('"'),
                row.get("Tags", "").strip('"'),
                row.get("Date_Added", "").strip('"')
            ))
            count += 1
    conn.commit()
    print(f"Loaded {count} knowledge nodes")

def build_cross_links(conn):
    """Build bidirectional links between nodes and related papers."""
    count = 0
    cursor = conn.execute("SELECT node_id, related_papers FROM knowledge_nodes WHERE related_papers IS NOT NULL AND related_papers != ''")
    for node_id, related_papers_str in cursor:
        if not related_papers_str:
            continue
        # Parse comma-separated paper IDs
        paper_ids = [p.strip() for p in related_papers_str.split(',')]
        for paper_id in paper_ids:
            conn.execute("""
                INSERT OR IGNORE INTO node_paper_links (
                    node_id, linked_paper_id, link_type
                ) VALUES (?, ?, ?)
            """, (node_id, paper_id, "related_paper"))
            count += 1
    conn.commit()
    print(f"Created {count} node-paper cross-links")

def create_search_index(conn):
    """Build a search index across papers and nodes by domain, node_type, and tags."""
    count = 0
    
    # Index papers by domain
    cursor = conn.execute("SELECT paper_id, domain FROM papers WHERE domain IS NOT NULL AND domain != ''")
    for paper_id, domain in cursor:
        conn.execute("""
            INSERT INTO retrieval_index (search_term, result_type, result_id, relevance_score)
            VALUES (?, ?, ?, ?)
        """, (domain.lower(), "paper", paper_id, 1.0))
        count += 1
    
    # Index papers by tags
    cursor = conn.execute("SELECT paper_id, tags FROM papers WHERE tags IS NOT NULL AND tags != ''")
    for paper_id, tags_str in cursor:
        if tags_str:
            for tag in tags_str.split(','):
                tag = tag.strip().lower()
                if tag:
                    conn.execute("""
                        INSERT INTO retrieval_index (search_term, result_type, result_id, relevance_score)
                        VALUES (?, ?, ?, ?)
                    """, (tag, "paper", paper_id, 0.8))
                    count += 1
    
    # Index nodes by node_type
    cursor = conn.execute("SELECT node_id, node_type FROM knowledge_nodes WHERE node_type IS NOT NULL AND node_type != ''")
    for node_id, node_type in cursor:
        conn.execute("""
            INSERT INTO retrieval_index (search_term, result_type, result_id, relevance_score)
            VALUES (?, ?, ?, ?)
        """, (node_type.lower(), "node", node_id, 1.0))
        count += 1
    
    # Index nodes by node_category
    cursor = conn.execute("SELECT node_id, node_category FROM knowledge_nodes WHERE node_category IS NOT NULL AND node_category != ''")
    for node_id, node_category in cursor:
        conn.execute("""
            INSERT INTO retrieval_index (search_term, result_type, result_id, relevance_score)
            VALUES (?, ?, ?, ?)
        """, (node_category.lower(), "node", node_id, 1.0))
        count += 1
    
    # Index nodes by tags
    cursor = conn.execute("SELECT node_id, tags FROM knowledge_nodes WHERE tags IS NOT NULL AND tags != ''")
    for node_id, tags_str in cursor:
        if tags_str:
            for tag in tags_str.split(','):
                tag = tag.strip().lower()
                if tag:
                    conn.execute("""
                        INSERT INTO retrieval_index (search_term, result_type, result_id, relevance_score)
                        VALUES (?, ?, ?, ?)
                    """, (tag, "node", node_id, 0.8))
                    count += 1
    
    conn.commit()
    print(f"Created {count} search index entries")

def main():
    # Connect to session database
    conn = sqlite3.connect(":memory:")
    
    # Create schema
    conn.execute("""
        CREATE TABLE papers (
            paper_id TEXT PRIMARY KEY,
            title TEXT,
            authors TEXT,
            year INTEGER,
            domain TEXT,
            sub_topic TEXT,
            evidence_type TEXT,
            document_type TEXT,
            evidence_score REAL,
            main_finding TEXT,
            practical_application TEXT,
            tags TEXT,
            related_papers TEXT,
            linked_features TEXT,
            date_added TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            paper_id TEXT,
            node_type TEXT,
            node_category TEXT,
            principle TEXT,
            description TEXT,
            coaching_action TEXT,
            evidence_strength TEXT,
            related_papers TEXT,
            tags TEXT,
            date_added TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
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
    
    conn.execute("""
        CREATE TABLE retrieval_index (
            query_id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_term TEXT,
            result_type TEXT,
            result_id TEXT,
            relevance_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("Loading retrieval layer...")
    load_papers(conn)
    load_knowledge_nodes(conn)
    build_cross_links(conn)
    create_search_index(conn)
    
    # Sample queries
    print("\n=== Sample Retrieval Queries ===\n")
    
    # Query 1: Find nodes by type
    print("Nodes by type (Principle):")
    cursor = conn.execute("SELECT node_id, principle FROM knowledge_nodes WHERE node_type = 'Coaching_Principle' LIMIT 3")
    for node_id, principle in cursor:
        print(f"  {node_id}: {principle}")
    
    # Query 2: Find papers by domain
    print("\nPapers by domain (Training_Prescription):")
    cursor = conn.execute("SELECT paper_id, title FROM papers WHERE domain = 'Training_Prescription' LIMIT 3")
    for paper_id, title in cursor:
        print(f"  {paper_id}: {title[:60]}...")
    
    # Query 3: Find papers linked to a node
    print("\nPapers linked to node ALP-2026-0072:")
    cursor = conn.execute("""
        SELECT p.paper_id, p.title FROM papers p
        JOIN node_paper_links npl ON p.paper_id = npl.linked_paper_id
        WHERE npl.node_id = 'ALP-2026-0072'
        LIMIT 5
    """)
    for paper_id, title in cursor:
        print(f"  {paper_id}: {title[:60]}...")
    
    # Query 4: Search by tag
    print("\nSearch results for 'recovery' tag:")
    cursor = conn.execute("""
        SELECT DISTINCT result_type, result_id FROM retrieval_index
        WHERE search_term = 'recovery' AND relevance_score >= 0.8
        LIMIT 5
    """)
    for result_type, result_id in cursor:
        print(f"  {result_type}: {result_id}")
    
    print("\n[OK] Retrieval layer ready for querying")

if __name__ == "__main__":
    main()

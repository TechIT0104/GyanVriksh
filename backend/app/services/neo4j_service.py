"""Neo4j graph operations: schema init, upserts, traversals, stats."""
import logging

from neo4j import GraphDatabase

from app.config import settings

logger = logging.getLogger(__name__)

_driver = None

NODE_KEYS = {
    "Equipment": "tag_id", "Document": "doc_id", "Procedure": "proc_id",
    "Regulation": "reg_id", "Incident": "incident_id", "Person": "person_id",
    "WorkOrder": "wo_id", "KnowledgeCapsule": "capsule_id", "SparePart": "part_id",
}

SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT eq_tag IF NOT EXISTS FOR (e:Equipment) REQUIRE e.tag_id IS UNIQUE",
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
    "CREATE CONSTRAINT proc_id IF NOT EXISTS FOR (p:Procedure) REQUIRE p.proc_id IS UNIQUE",
    "CREATE CONSTRAINT reg_id IF NOT EXISTS FOR (r:Regulation) REQUIRE r.reg_id IS UNIQUE",
    "CREATE CONSTRAINT inc_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE",
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE",
    "CREATE CONSTRAINT wo_id IF NOT EXISTS FOR (w:WorkOrder) REQUIRE w.wo_id IS UNIQUE",
    "CREATE CONSTRAINT kc_id IF NOT EXISTS FOR (k:KnowledgeCapsule) REQUIRE k.capsule_id IS UNIQUE",
    "CREATE CONSTRAINT part_id IF NOT EXISTS FOR (s:SparePart) REQUIRE s.part_id IS UNIQUE",
    "CREATE INDEX eq_type IF NOT EXISTS FOR (e:Equipment) ON (e.type)",
    "CREATE INDEX eq_unit IF NOT EXISTS FOR (e:Equipment) ON (e.unit)",
    "CREATE INDEX wo_date IF NOT EXISTS FOR (w:WorkOrder) ON (w.date)",
    "CREATE INDEX inc_date IF NOT EXISTS FOR (i:Incident) ON (i.date)",
    "CREATE TEXT INDEX doc_title IF NOT EXISTS FOR (d:Document) ON (d.title)",
]


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(settings.neo4j_uri,
                                       auth=(settings.neo4j_user, settings.neo4j_password))
    return _driver


def run(cypher: str, **params) -> list[dict]:
    with get_driver().session() as session:
        return [dict(r) for r in session.run(cypher, **params)]


def init_schema():
    for stmt in SCHEMA_STATEMENTS:
        run(stmt)
    logger.info("Neo4j schema initialized (%d statements)", len(SCHEMA_STATEMENTS))


def upsert_node(label: str, key_value: str, properties: dict):
    key = NODE_KEYS[label]
    props = {k: v for k, v in properties.items() if v is not None}
    run(f"MERGE (n:{label} {{{key}: $key_value}}) SET n += $props",
        key_value=key_value, props=props)


def upsert_relationship(from_label: str, from_key: str, rel: str, to_label: str, to_key: str,
                        rel_props: dict | None = None):
    fk, tk = NODE_KEYS[from_label], NODE_KEYS[to_label]
    run(
        f"MATCH (a:{from_label} {{{fk}: $from_key}}), (b:{to_label} {{{tk}: $to_key}}) "
        f"MERGE (a)-[r:{rel}]->(b) SET r += $rel_props",
        from_key=from_key, to_key=to_key, rel_props=rel_props or {},
    )


def equipment_360(tag_id: str) -> dict:
    rows = run(
        """
        MATCH (e:Equipment {tag_id: $tag})
        OPTIONAL MATCH (e)-[:HAS_MAINTENANCE_RECORD]->(wo:WorkOrder)
        OPTIONAL MATCH (e)-[:INVOLVED_IN]->(inc:Incident)
        OPTIONAL MATCH (e)-[:FOLLOWS_PROCEDURE]->(proc:Procedure)
        OPTIONAL MATCH (e)-[:GOVERNED_BY]->(reg:Regulation)
        OPTIONAL MATCH (p:Person)-[:PERFORMED]->(wo)
        OPTIONAL MATCH (kc:KnowledgeCapsule)-[:ABOUT]->(e)
        RETURN e,
               collect(DISTINCT wo) AS workorders,
               collect(DISTINCT inc) AS incidents,
               collect(DISTINCT proc) AS procedures,
               collect(DISTINCT reg) AS regulations,
               collect(DISTINCT p) AS technicians,
               collect(DISTINCT kc) AS capsules
        """,
        tag=tag_id,
    )
    if not rows:
        return {}
    row = rows[0]
    return {
        "equipment": dict(row["e"]),
        "workorders": sorted([dict(w) for w in row["workorders"]],
                             key=lambda w: str(w.get("date", "")), reverse=True),
        "incidents": [dict(i) for i in row["incidents"]],
        "procedures": [dict(p) for p in row["procedures"]],
        "regulations": [dict(r) for r in row["regulations"]],
        "technicians": [dict(t) for t in row["technicians"]],
        "capsules": [dict(k) for k in row["capsules"]],
    }


def subgraph(tag_id: str, depth: int = 2) -> dict:
    rows = run(
        f"""
        MATCH path = (e:Equipment {{tag_id: $tag}})-[*1..{min(depth, 3)}]-(n)
        WITH nodes(path) AS ns, relationships(path) AS rs
        UNWIND ns AS node UNWIND rs AS rel
        RETURN collect(DISTINCT {{id: elementId(node), labels: labels(node), props: properties(node)}}) AS nodes,
               collect(DISTINCT {{source: elementId(startNode(rel)), target: elementId(endNode(rel)), type: type(rel)}}) AS links
        """,
        tag=tag_id,
    )
    return rows[0] if rows else {"nodes": [], "links": []}


def full_graph(limit: int = 500) -> dict:
    rows = run(
        """
        MATCH (n) WITH n LIMIT $limit
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN collect(DISTINCT {id: elementId(n), labels: labels(n), props: properties(n)}) AS nodes,
               collect(DISTINCT CASE WHEN r IS NULL THEN NULL ELSE
                 {source: elementId(startNode(r)), target: elementId(endNode(r)), type: type(r)} END) AS links
        """,
        limit=limit,
    )
    if not rows:
        return {"nodes": [], "links": []}
    out = rows[0]
    out["links"] = [l for l in out["links"] if l is not None]
    return out


def cliff_data() -> dict:
    """Raw data for the Knowledge Cliff Risk analytic: every person with the
    equipment they know, work orders they've done, and knowledge capsules they've
    recorded; plus every equipment with its knowledgeable people and capsule count."""
    persons = run(
        """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:KNOWS_ABOUT]->(e:Equipment)
        OPTIONAL MATCH (p)-[:PERFORMED]->(wo:WorkOrder)
        OPTIONAL MATCH (p)-[:SHARED_KNOWLEDGE]->(kc:KnowledgeCapsule)
        RETURN p.person_id AS id, p.name AS name, p.designation AS designation,
               p.department AS department, p.expertise AS expertise,
               p.years_experience AS years, p.retirement_date AS retirement,
               collect(DISTINCT e.tag_id) AS equipment,
               count(DISTINCT wo) AS workorders,
               count(DISTINCT kc) AS capsules
        """
    )
    equipment = run(
        """
        MATCH (e:Equipment)
        OPTIONAL MATCH (e)<-[:KNOWS_ABOUT]-(p:Person)
        OPTIONAL MATCH (kc:KnowledgeCapsule)-[:ABOUT]->(e)
        RETURN e.tag_id AS tag, e.type AS type, e.name AS name,
               collect(DISTINCT {name: p.name, retirement: p.retirement_date}) AS experts,
               count(DISTINCT kc) AS capsules
        """
    )
    return {"persons": persons, "equipment": equipment}


def stats() -> dict:
    node_rows = run("MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS count")
    rel_rows = run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count")
    return {
        "nodes": {r["label"]: r["count"] for r in node_rows},
        "relationships": {r["type"]: r["count"] for r in rel_rows},
        "total_nodes": sum(r["count"] for r in node_rows),
        "total_relationships": sum(r["count"] for r in rel_rows),
    }

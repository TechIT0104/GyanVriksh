"""Load the Bharat Chemicals Limited Unit 3 synthetic dataset:
equipment, persons, work orders, incidents into Neo4j; SOPs/audits/capsule
transcripts through the full ingestion path (direct index, no Kafka needed);
knowledge capsules into Neo4j + Qdrant."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.db_models import Base, Chunk, Document, SessionLocal, engine
from app.services import embedding_service, neo4j_service, qdrant_service
from app.services.ner_service import extract_entities
from app.utils.chunker import chunk_pages

DATA = Path(__file__).resolve().parent.parent / "data/demo_dataset"


def load_graph_entities():
    equipment = json.loads((DATA / "equipment.json").read_text())
    for e in equipment:
        neo4j_service.upsert_node("Equipment", e["tag_id"], e)
    print(f"Equipment nodes: {len(equipment)}")

    persons = json.loads((DATA / "persons.json").read_text())
    for p in persons:
        neo4j_service.upsert_node("Person", p["person_id"], p)
    print(f"Person nodes: {len(persons)}")

    wos = json.loads((DATA / "work_orders/work_orders.json").read_text())
    name_to_id = {p["name"]: p["person_id"] for p in persons}
    for w in wos:
        neo4j_service.upsert_node("WorkOrder", w["wo_id"], w)
        neo4j_service.upsert_relationship("Equipment", w["equipment_tag"],
                                          "HAS_MAINTENANCE_RECORD", "WorkOrder", w["wo_id"])
        pid = name_to_id.get(w["technician"])
        if pid:
            neo4j_service.upsert_relationship("Person", pid, "PERFORMED", "WorkOrder", w["wo_id"])
            neo4j_service.upsert_relationship("Person", pid, "KNOWS_ABOUT",
                                              "Equipment", w["equipment_tag"])
        if w.get("procedure"):
            neo4j_service.upsert_node("Procedure", w["procedure"], {"proc_id": w["procedure"]})
            neo4j_service.upsert_relationship("WorkOrder", w["wo_id"], "FOLLOWED",
                                              "Procedure", w["procedure"])
            neo4j_service.upsert_relationship("Equipment", w["equipment_tag"],
                                              "FOLLOWS_PROCEDURE", "Procedure", w["procedure"])
    print(f"WorkOrder nodes: {len(wos)}")

    incidents = json.loads((DATA / "incidents/incidents.json").read_text())
    for i in incidents:
        neo4j_service.upsert_node("Incident", i["incident_id"], i)
        neo4j_service.upsert_relationship("Equipment", i["equipment_tag"],
                                          "INVOLVED_IN", "Incident", i["incident_id"])
    print(f"Incident nodes: {len(incidents)}")

    # Procedure -> Regulation links from the "Regulatory Basis" declared in each SOP
    proc_reg = {
        "SOP-MAINT-047": ["OISD-116-S5.3", "OISD-116-S5.3.2"],
        "SOP-MAINT-012": ["OISD-116-S5.3", "OISD-116-S5.4"],
        "SOP-CS-012": ["OISD-105-S4.3", "OISD-105-S4.4", "FACTORIES-ACT-1948-S36"],
        "SOP-PTW-003": ["OISD-145-S3.2"],
        "SOP-MAINT-055": ["OISD-116-S7.1"],
        "SOP-MAINT-062": ["OISD-116-S5.3"],
        "SOP-INST-021": ["OISD-117-S6.2"],
        "SOP-EM-001": ["OISD-141-S6.1"],
        "SOP-SD-003": ["OISD-117-S6.2"],
        "SOP-SU-004": ["OISD-117-S6.2"],
    }
    for proc, regs in proc_reg.items():
        for reg in regs:
            neo4j_service.upsert_relationship("Procedure", proc, "REQUIRED_BY", "Regulation", reg)
            for tag in ("P-101", "P-102", "P-201") if proc == "SOP-MAINT-047" else []:
                neo4j_service.upsert_relationship("Equipment", tag, "GOVERNED_BY", "Regulation", reg)
    # Incident-procedure learning links
    neo4j_service.upsert_relationship("Incident", "INC-2024-0089", "LED_TO_UPDATE", "Procedure", "SOP-CS-012")
    neo4j_service.upsert_relationship("Incident", "INC-2025-0047", "LED_TO_UPDATE", "Procedure", "SOP-MAINT-047")


def index_text_documents():
    """Index SOPs, audits and work-order/incident summaries directly (bypasses Kafka
    so demo data loads without workers running)."""
    db = SessionLocal()
    docs: list[tuple[str, str, str]] = []  # (doc_id, doc_type, text)
    for f in sorted((DATA / "procedures").glob("*.txt")):
        docs.append((f.stem, "SOP", f.read_text()))
    for f in sorted((DATA / "audits").glob("*.txt")):
        docs.append((f.stem, "AUDIT_REPORT", f.read_text()))

    wos = json.loads((DATA / "work_orders/work_orders.json").read_text())
    wo_text = "\n\n".join(
        f"Work order {w['wo_id']} dated {w['date']} ({w['type']}) on equipment {w['equipment_tag']}: "
        f"{w['description']}. Technician: {w['technician']}. Time taken: {w['time_taken_hrs']} hours. "
        f"Parts used: {', '.join(w['parts_used']) or 'none'}. Cost: INR {w['cost_inr']}. "
        f"Findings: {w['findings']} Procedure followed: {w.get('procedure', 'n/a')}."
        for w in wos)
    docs.append(("WO-HISTORY-UNIT3", "MAINTENANCE_REPORT", wo_text))

    incidents = json.loads((DATA / "incidents/incidents.json").read_text())
    inc_text = "\n\n".join(
        f"Incident {i['incident_id']} dated {i['date']} ({i['type']}, severity {i['severity']}) "
        f"involving {i['equipment_tag']}: {i['description']} Root cause: {i['root_cause']} "
        f"Corrective action: {i['corrective_action']} Reported by: {i['reported_by']}."
        for i in incidents)
    docs.append(("INC-HISTORY-UNIT3", "INCIDENT_REPORT", inc_text))

    try:
        for doc_id, doc_type, text in docs:
            existing = db.query(Document).filter(Document.file_id == doc_id).first()
            if existing:
                db.query(Chunk).filter(Chunk.document_id == existing.id).delete()
                db.delete(existing)
                db.commit()
            doc = Document(file_id=doc_id, original_name=f"{doc_id}.txt", doc_type=doc_type,
                           storage_path=f"local://demo/{doc_id}", uploader="demo-loader",
                           status="INDEXED", page_count=1)
            db.add(doc)
            db.commit()

            chunks = chunk_pages([{"page": 1, "text": text}])
            texts = [c["text"] for c in chunks]
            vectors = embedding_service.embed(texts)
            points, entity_total = [], 0
            for ch, vec in zip(chunks, vectors):
                entities = extract_entities(ch["text"])
                entity_total += len(entities)
                tags = sorted({e["text"].upper() for e in entities if e["label"] == "EQUIPMENT_TAG"})
                chunk_id = f"{doc_id}-c{ch['chunk_index']}"
                db.add(Chunk(chunk_id=chunk_id, document_id=doc.id, page_number=1,
                             chunk_index=ch["chunk_index"], text=ch["text"],
                             meta={"entities": entities, "equipment_tags": tags}))
                points.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)),
                               "dense": vec["dense"], "sparse": vec["sparse"],
                               "payload": {"chunk_id": chunk_id, "file_id": doc_id, "page": 1,
                                           "text": ch["text"], "doc_type": doc_type,
                                           "equipment_tags": tags}})
            doc.chunk_count = len(chunks)
            doc.entity_count = entity_total
            db.commit()
            qdrant_service.upsert_chunks("chunks", points)
            neo4j_service.upsert_node("Document", doc_id, {"doc_id": doc_id, "type": doc_type,
                                                           "title": doc_id})
            print(f"Indexed {doc_id}: {len(chunks)} chunks, {entity_total} entities")
    finally:
        db.close()


def load_knowledge_capsules():
    """Pre-scripted capsules: create verified KnowledgeCapsule nodes + index transcripts."""
    capsule_meta = [
        {"file": "KC-TRANSCRIPT-01-RameshKumar-P101.txt", "capsule_id": "KC-2026-0012",
         "expert": "Ramesh Kumar", "person_id": "EMP-0234", "recorded_date": "2026-06-20",
         "duration_seconds": 847, "equipment": ["P-101", "FI-101", "V-201"],
         "category": "FAILURE_PRECURSOR",
         "insight_text": "P-101 seal gives 10-15 days warning: slight bearing-housing vibration "
                         "(~4 mm/s) plus faint suction whistling together mean imminent seal failure. "
                         "Check suction strainer every morning before startup (overnight sediment). "
                         "FI-101 reads 8% low due to orifice edge wear — add 8% to its readings.",
         "timestamp_sec": 154},
        {"file": "KC-TRANSCRIPT-02-JPSharma-Startup.txt", "capsule_id": "KC-2026-0013",
         "expert": "J.P. Sharma", "person_id": "EMP-0198", "recorded_date": "2026-06-22",
         "duration_seconds": 612, "equipment": ["C-401", "HE-303", "P-201"],
         "category": "OPERATING_TIP",
         "insight_text": "Never exceed 25°C/hour on HE-303 reboiler heat-up (tube joint leaks in 2019 "
                         "and 2025 both from fast heat-up). Establish C-401 reflux before feed; DP above "
                         "0.4 bar means flooding. After P-201 trips, check auto/manual selector first.",
         "timestamp_sec": 45},
        {"file": "KC-TRANSCRIPT-03-Venkatesan-Instruments.txt", "capsule_id": "KC-2026-0014",
         "expert": "S. Venkatesan", "person_id": "EMP-0102", "recorded_date": "2026-06-25",
         "duration_seconds": 498, "equipment": ["FI-101", "C-401"],
         "category": "CALIBRATION_INSIGHT",
         "insight_text": "FI-101 drifts 7-8% low every ~6 months since 2021 (orifice edge erosion); "
                         "permanent fix requires plate replacement at shutdown — apply +8% correction "
                         "until then. LT-401 impulse line chokes every monsoon; flush preventively in "
                         "September-October.",
         "timestamp_sec": 30},
    ]
    points = []
    for c in capsule_meta:
        transcript = (DATA / "knowledge_capsules" / c["file"]).read_text()
        neo4j_service.upsert_node("KnowledgeCapsule", c["capsule_id"], {
            "capsule_id": c["capsule_id"], "expert": c["expert"],
            "recorded_date": c["recorded_date"], "duration_seconds": c["duration_seconds"],
            "audio_path": f"local://demo/audio/{c['file']}", "transcript": transcript,
            "insight_text": c["insight_text"], "category": c["category"],
            "timestamp_sec": c["timestamp_sec"], "confidence": "EXPERT_VERIFIED",
            "verified": True, "verified_by": "Plant Manager"})
        neo4j_service.upsert_relationship("Person", c["person_id"], "SHARED_KNOWLEDGE",
                                          "KnowledgeCapsule", c["capsule_id"])
        for tag in c["equipment"]:
            neo4j_service.upsert_relationship("KnowledgeCapsule", c["capsule_id"], "ABOUT",
                                              "Equipment", tag)
            neo4j_service.upsert_relationship("Person", c["person_id"], "KNOWS_ABOUT",
                                              "Equipment", tag)
        text = f"Expert knowledge capsule {c['capsule_id']} from {c['expert']}: {c['insight_text']}\n\nTranscript: {transcript}"
        vec = embedding_service.embed([text])[0]
        points.append({"id": str(uuid.uuid5(uuid.NAMESPACE_URL, c["capsule_id"])),
                       "dense": vec["dense"], "sparse": vec["sparse"],
                       "payload": {"chunk_id": c["capsule_id"], "file_id": c["capsule_id"],
                                   "page": 1, "text": text, "doc_type": "KNOWLEDGE_CAPSULE",
                                   "equipment_tags": c["equipment"]}})
    qdrant_service.upsert_chunks("audio_clips", points)
    qdrant_service.upsert_chunks("chunks", points)
    print(f"Knowledge capsules: {len(capsule_meta)}")


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("=== Loading Bharat Chemicals Limited Unit 3 demo dataset ===")
    load_graph_entities()
    index_text_documents()
    load_knowledge_capsules()
    stats = neo4j_service.stats()
    print(f"\nGraph totals: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
    print("Demo dataset loaded.")

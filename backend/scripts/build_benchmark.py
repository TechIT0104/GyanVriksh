"""Build the 100-question GyanVriksh benchmark from the demo dataset.
Writes data/benchmark_questions.json with ground-truth answers and categories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA = Path(__file__).resolve().parent.parent / "data/demo_dataset"
OUT = Path(__file__).resolve().parent.parent / "data/benchmark_questions.json"

HAND_WRITTEN = [
    {"q": "When was P-101 last serviced and what was done?",
     "truth": "15-Mar-2026, mechanical seal replacement (WO-2026-0831) by Ramesh Kumar",
     "category": "FACTUAL_LOOKUP"},
    {"q": "Does SOP-MAINT-047 comply with OISD-116 section 5.3.2?",
     "truth": "Partial compliance — Step 1 says 'Issue PTW' but does not specify that a qualified safety officer (minimum Grade-B HSE) must sign it",
     "category": "COMPLIANCE_CHECK"},
    {"q": "Which equipment has the same failure mode as P-101?",
     "truth": "P-201 (2 mechanical seal failures 2025-2026, same seal spec SK-101-A); P-301 has none because it uses AESSEAL MG1",
     "category": "CROSS_ENTITY_REASONING"},
    {"q": "Who are the experts on P-101 and when do they retire?",
     "truth": "Ramesh Kumar (multiple seal WOs + capsule KC-2026-0012), retires 31-Mar-2029",
     "category": "KNOWLEDGE_CLIFF"},
    {"q": "What is the correct gas testing requirement before confined space entry?",
     "truth": "Per SOP-CS-012 Section 6.2 and OISD-105 §4.3: O2 19.5-23.5%, LEL <5%, H2S <10ppm, CO <25ppm; test not more than 30 minutes before entry; repeat after >15 minute interruption",
     "category": "PROCEDURE_QUERY"},
    {"q": "Is FI-101 accurate?",
     "truth": "No — it reads approximately 8% low due to orifice edge wear. Per Ramesh Kumar and S. Venkatesan (knowledge capsules) add 8% to readings; permanent fix is plate replacement at shutdown",
     "category": "KNOWLEDGE_CAPSULE"},
    {"q": "What warning signs appear before a P-101 seal failure?",
     "truth": "Slight bearing-housing vibration (~4 mm/s) plus faint whistling from suction side, appearing 10-15 days before failure (Ramesh Kumar capsule KC-2026-0012)",
     "category": "KNOWLEDGE_CAPSULE"},
    {"q": "Why do P-101 seals keep failing?",
     "truth": "Sustained operation above 70°C with a seal spec marginal for thermal cycling; contributing: clogged suction strainer causing cavitation stress. Root cause per INC-2025-0047",
     "category": "FAILURE_ANALYSIS"},
    {"q": "What should be checked before starting P-101 in the morning?",
     "truth": "Suction strainer (overnight sediment clogging) and V-201 level above 40% for NPSH, per SOP-SU-004 and Ramesh Kumar's capsule",
     "category": "PROCEDURE_QUERY"},
    {"q": "What was the near-miss in V-203 and what changed after it?",
     "truth": "Dec-2024 (INC-2024-0089): gas detector alarmed at 8% LEL during entry; gas test was 45 min old. Gas test 30-min validity now strictly enforced and continuous monitoring mandatory for sludge-history vessels",
     "category": "FAILURE_ANALYSIS"},
    {"q": "What is the maximum heat-up rate for HE-303 and why?",
     "truth": "25°C/hour per SOP-SU-004; fast heat-up caused tube-to-tubesheet leaks in 2019 and 2025 (J.P. Sharma capsule)",
     "category": "KNOWLEDGE_CAPSULE"},
    {"q": "How should a hydrocarbon leak from a pump seal be handled?",
     "truth": "Per SOP-EM-001: raise alarm, switch to standby pump, isolate leaking pump, depressurise to flare, cordon 15m, eliminate ignition sources; leaks >10L logged as incident with RCA in 7 days",
     "category": "PROCEDURE_QUERY"},
    {"q": "Which regulation governs PTW countersignature and what does it require?",
     "truth": "OISD-116 §5.3.2 (rotating equipment) and OISD-145 §3.2: permits signed/countersigned by a qualified safety officer, minimum Grade-B HSE",
     "category": "COMPLIANCE_CHECK"},
    {"q": "What did the Feb-2026 internal audit find about SOP-MAINT-047?",
     "truth": "AUDIT-2026-INT-01: 3 of 25 cold work permits not countersigned by HSE officer; SOP-MAINT-047 Step 1 doesn't specify signatory authority — recommends adding Grade-B HSE countersignature",
     "category": "COMPLIANCE_CHECK"},
    {"q": "What is P-101's maintenance interval and why was it changed?",
     "truth": "90 days, reduced from 180 after the Jul-2025 seal failure incident INC-2025-0047",
     "category": "FACTUAL_LOOKUP"},
    {"q": "Which experts retire within 3 years and what knowledge is at risk?",
     "truth": "J.P. Sharma (Sep-2027, startup/shutdown expertise, capsule KC-2026-0013 captured), S. Venkatesan (Jun-2028, instrumentation, KC-2026-0014), Ramesh Kumar (Mar-2029, rotating equipment, KC-2026-0012)",
     "category": "KNOWLEDGE_CLIFF"},
    {"q": "What happens if C-401 differential pressure crosses 0.4 bar during startup?",
     "truth": "Indicates column flooding — reduce feed and wait, per J.P. Sharma's capsule KC-2026-0013",
     "category": "KNOWLEDGE_CAPSULE"},
    {"q": "Why did P-201 cause a feed interruption in January 2026?",
     "truth": "INC-2026-0011: P-201 tripped on seal failure and standby didn't auto-start because selector switch was in manual; 40-minute interruption",
     "category": "FAILURE_ANALYSIS"},
    {"q": "What is the vibration alert limit for pumps and where is it defined?",
     "truth": "4.5 mm/s RMS alert (trip review 7.1 mm/s) per SOP-MAINT-012",
     "category": "PROCEDURE_QUERY"},
    {"q": "What corrective action was recommended for the HE-303 tube leaks?",
     "truth": "6 tubes plugged (WO-2025-0489); daily cooling water chloride monitoring; metallurgy upgrade study — chloride stress corrosion at tube-to-tubesheet joints",
     "category": "FAILURE_ANALYSIS"},
]


def generated_questions():
    qs = []
    wos = json.loads((DATA / "work_orders/work_orders.json").read_text())
    for w in wos:
        qs.append({"q": f"What work was done on {w['equipment_tag']} on {w['date']}?",
                   "truth": f"{w['description']} ({w['wo_id']}), technician {w['technician']}. Findings: {w['findings']}",
                   "category": "FACTUAL_LOOKUP"})
        qs.append({"q": f"Who performed work order {w['wo_id']} and what were the findings?",
                   "truth": f"{w['technician']}; findings: {w['findings']}",
                   "category": "FACTUAL_LOOKUP"})
    incidents = json.loads((DATA / "incidents/incidents.json").read_text())
    for i in incidents:
        qs.append({"q": f"What was the root cause of incident {i['incident_id']}?",
                   "truth": i["root_cause"], "category": "FAILURE_ANALYSIS"})
        qs.append({"q": f"What corrective action followed incident {i['incident_id']}?",
                   "truth": i["corrective_action"], "category": "FAILURE_ANALYSIS"})
    equipment = json.loads((DATA / "equipment.json").read_text())
    for e in equipment[:10]:
        qs.append({"q": f"Where is {e['tag_id']} located and what is its criticality?",
                   "truth": f"{e['location']}, {e['unit']}; criticality {e['criticality']}",
                   "category": "FACTUAL_LOOKUP"})
    return qs


if __name__ == "__main__":
    questions = HAND_WRITTEN + generated_questions()
    questions = questions[:100]
    for i, q in enumerate(questions, 1):
        q["id"] = f"Q{i:03d}"
    OUT.write_text(json.dumps(questions, indent=2))
    from collections import Counter
    print(f"Benchmark written: {len(questions)} questions -> {OUT}")
    print(Counter(q["category"] for q in questions))

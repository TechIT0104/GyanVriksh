"""Generate 5,000+ BIO-annotated synthetic industrial sentences for NER training.

Template-based (no API needed): entity slots are filled from realistic vocabularies,
so BIO labels are exact by construction — no offset errors like LLM generation.
Output: train.txt / dev.txt / test.txt in CoNLL format + labels.txt
"""
import random

random.seed(42)

EQUIPMENT_TAGS = [f"{p}-{n}" for p in ["P", "V", "HE", "C", "K", "FI", "PI", "TI", "LT", "PSV"]
                  for n in [101, 102, 103, 104, 105, 201, 202, 203, 204, 205, 301, 302, 303, 401, 402]]
EQUIPMENT_TYPES = ["centrifugal pump", "gear pump", "heat exchanger", "shell and tube exchanger",
                   "pressure vessel", "knockout drum", "distillation column", "reciprocating compressor",
                   "reboiler", "surge drum", "flow meter", "relief valve", "storage tank", "reactor"]
PARAMS = ["45°C", "80°C", "120°C", "8 bar", "12 bar", "18 bar", "120 SLPM", "45 m³/h", "pH 7.2",
          "4.5 mm/s", "75°C", "2.5 kg/cm²", "30 ppm", "5% LEL", "0.3 bar", "250°C", "19.5% oxygen"]
REG_REFS = ["OISD-116 §4.2", "OISD-116 §5.3.2", "OISD-105 §4.3", "OISD-118 §4.3", "OISD-137 §5.1",
            "OISD-141 §6.1", "OISD-145 §3.2", "Factory Act Section 36", "Factory Act S.31",
            "PESO-2016", "OISD-117 §6.2", "IS 2825"]
PERSONS = ["Ramesh Kumar", "J.P. Sharma", "Arjun Mehta", "Sunil Yadav", "Kavita Rao",
           "S. Venkatesan", "Priya Deshmukh", "Anil Gupta", "Mohammed Irfan", "Deepak Verma",
           "R. Krishnan", "Suresh Patil", "Vikram Singh", "Nitin Joshi"]
DATES = ["15-Mar-2026", "22-Jul-2025", "03-Dec-2024", "Q3 FY26", "next shutdown", "12-Jun-2026",
         "January 2026", "28-Feb-2025", "Q1 FY25", "last annual turnaround", "05-Apr-2024"]
LOCATIONS = ["Unit 3", "Unit 4", "Bay 7", "North Tank Farm", "Feed Section", "Compressor Shed",
             "Column Section", "South Tank Farm", "Bay 2", "Product Section", "Unit 5"]
FAILURE_MODES = ["seal failure", "cavitation", "corrosion", "bearing wear", "vibration",
                 "spring fatigue", "fouling", "tube leak", "erosion", "stress corrosion cracking",
                 "valve plate wear", "impeller damage", "gasket failure"]
ACTIONS = ["replaced the impeller", "tightened the gland", "flushed the line", "replaced the seal kit",
           "calibrated the transmitter", "plugged the leaking tubes", "cleaned the strainer",
           "realigned the coupling", "replaced valve plates", "greased the bearings",
           "performed eddy current testing", "renewed the gasket"]
MATERIALS = ["SS304", "SS316L", "CS-ASTM A36", "CS-ASTM A516", "Inconel 625", "SS316", "Monel 400"]
PROC_REFS = ["SOP-MAINT-047", "SOP-CS-012", "PTW-2026-0831", "SOP-PTW-003", "WO-2026-0114",
             "SOP-INST-021", "SOP-EM-001", "PTW-2025-1102", "SOP-MAINT-062", "SOP-SU-004"]
HAZARDS = ["HAZMAT Zone 1", "flammable liquid", "H2S zone", "Zone 2 hazardous area",
           "confined space", "toxic gas area"]

SLOTS = {
    "TAG": ("EQUIPMENT_TAG", EQUIPMENT_TAGS), "TYPE": ("EQUIPMENT_TYPE", EQUIPMENT_TYPES),
    "PARAM": ("PROCESS_PARAM", PARAMS), "REG": ("REGULATORY_REF", REG_REFS),
    "PERSON": ("PERSON", PERSONS), "DATE": ("DATE", DATES), "LOC": ("LOCATION", LOCATIONS),
    "FAIL": ("FAILURE_MODE", FAILURE_MODES), "ACT": ("ACTION_TAKEN", ACTIONS),
    "MAT": ("MATERIAL", MATERIALS), "PROC": ("PROCEDURE_REF", PROC_REFS),
    "HAZ": ("HAZARD_CLASS", HAZARDS),
}

TEMPLATES = [
    "{PERSON} {ACT} on {TAG} on {DATE} after {FAIL} was detected in {LOC} .",
    "The {TYPE} {TAG} in {LOC} showed {FAIL} at {PARAM} during inspection on {DATE} .",
    "Per {REG} , maintenance of {TAG} requires a permit under {PROC} signed before work in {HAZ} .",
    "{TAG} operating at {PARAM} exceeded the limit specified in {PROC} ; {PERSON} was informed on {DATE} .",
    "Inspection by {PERSON} found {FAIL} on the {TYPE} ; material of construction is {MAT} .",
    "Work order for {TAG} closed on {DATE} : {ACT} following {PROC} in {LOC} .",
    "{REG} mandates gas testing before entry into {HAZ} near {TAG} in {LOC} .",
    "The {TYPE} was fabricated from {MAT} and operates at {PARAM} in {LOC} .",
    "{PERSON} reported {FAIL} on {TAG} at {PARAM} ; corrective action per {PROC} scheduled for {DATE} .",
    "Compliance audit on {DATE} against {REG} flagged {TAG} in {LOC} for missing records .",
    "During shutdown {PERSON} {ACT} on the {TYPE} {TAG} as required by {REG} .",
    "{FAIL} recurred on {TAG} within 90 days ; {PERSON} recommended a design review on {DATE} .",
    "The permit {PROC} for work in {HAZ} was countersigned by {PERSON} per {REG} .",
    "Vibration of {PARAM} recorded on {TAG} by {PERSON} during the {DATE} survey in {LOC} .",
    "Replacement {TYPE} in {MAT} was installed at {LOC} on {DATE} following repeated {FAIL} .",
]


def fill(template: str):
    tokens, labels = [], []
    for word in template.split():
        if word.startswith("{") and word.endswith("}"):
            label, vocab = SLOTS[word[1:-1]]
            value_tokens = random.choice(vocab).split()
            for i, vt in enumerate(value_tokens):
                tokens.append(vt)
                labels.append(("B-" if i == 0 else "I-") + label)
        else:
            tokens.append(word)
            labels.append("O")
    return tokens, labels


def main(n=5500):
    sentences = [fill(random.choice(TEMPLATES)) for _ in range(n)]
    random.shuffle(sentences)
    n_train, n_dev = int(n * 0.8), int(n * 0.1)
    splits = {"train.txt": sentences[:n_train],
              "dev.txt": sentences[n_train:n_train + n_dev],
              "test.txt": sentences[n_train + n_dev:]}
    for fname, sents in splits.items():
        with open(fname, "w") as f:
            for tokens, labels in sents:
                for t, l in zip(tokens, labels):
                    f.write(f"{t}\t{l}\n")
                f.write("\n")
        print(f"{fname}: {len(sents)} sentences")
    labels = sorted({l for _, ls in sentences for l in ls})
    with open("labels.txt", "w") as f:
        f.write("\n".join(labels))
    print(f"labels.txt: {len(labels)} labels")


if __name__ == "__main__":
    main()

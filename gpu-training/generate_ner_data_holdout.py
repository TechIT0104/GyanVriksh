"""Generate NER training data with a GENUINE held-out evaluation split.

Why this exists: the original generate_ner_data.py builds train/dev/test as a
random 80/10/10 split of sentences drawn from the SAME 15 templates and the
SAME closed vocabularies. That means test sentences share sentence skeletons
and entity surface forms with training sentences -- a model can hit 1.00 F1
by memorizing template + vocab patterns without generalizing at all.

This script instead holds out:
  - 3 of 15 sentence templates entirely (never seen during training)
  - ~20% of each vocabulary list's values (never seen during training)

...and builds THREE separate held-out test tiers so you can see exactly what
degrades, if anything:
  - test_holdout_structural.txt : held-out templates,  familiar vocab
  - test_holdout_vocab.txt      : familiar templates,  held-out vocab
  - test_holdout_both.txt       : held-out templates,  held-out vocab (hardest)

train.txt / dev.txt only ever use the 12 non-held-out templates and the
~80% "train" slice of each vocab list, so there is zero leakage into any of
the three held-out test files by construction.

Coverage check: every one of the 12 entity types still appears in at least
TWO of the 12 training templates (not just one -- see the module-level
comment near HOLDOUT_TEMPLATE_IDX for why that threshold matters).

v2 fixes two problems found by evaluating v1's model on this same held-out
split:
  - HAZARD_CLASS and MATERIAL and ACTION_TAKEN each only ever appear in 3
    of the 15 templates total. v1 happened to hold out 2 of HAZARD_CLASS's
    3 templates, leaving it with a single training context -- it never had
    a chance to learn the concept independent of one exact sentence shape,
    and its held-out F1 collapsed to 0.2-0.4. Fixed by holding out at most
    one template from each of these three fragile trios.
  - LOCATION's vocabulary mixed a numeric pattern ("Unit 3", "Bay 7") with
    fixed proper nouns ("North Tank Farm") in a list of only 11 values --
    too small/heterogeneous to learn a rule, so the model mostly memorized
    strings and scored 0.000 F1 on unseen location values. Fixed by
    expanding the numbered sub-pattern to 22 values so there's an actual
    compositional rule to learn (same reason EQUIPMENT_TAG generalizes).
    The 6 fixed named areas remain a closed set by nature (real plants do
    have a fixed, known list of tank farms/sections) -- expect those to
    still need dictionary updates rather than true generalization.

v3 fix: after v2, HAZARD_CLASS still collapsed on unseen values (0.175 F1)
even though structural generalization was fixed (1.000 F1). Root cause was
different from v1/v2's template-coverage bug: HAZARD_CLASS only had 6
possible values total, so a 20% vocab holdout left exactly ONE value ever
appearing in the held-out test -- a phrase sharing zero tokens with
training data, with no shared structural pattern (unlike EQUIPMENT_TAG's
letter-dash-number format) to generalize from. This is expanded to 20
real OISD/Factory-Act-style hazard categories so there's enough training
diversity for the held-out slice to be recognizable, not memorized.
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
LOCATIONS = ([f"Unit {n}" for n in range(1, 13)] + [f"Bay {n}" for n in range(1, 11)] +
             ["North Tank Farm", "South Tank Farm", "Feed Section", "Compressor Shed",
              "Column Section", "Product Section"])
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
HAZARDS = ["HAZMAT Zone 0", "HAZMAT Zone 1", "HAZMAT Zone 2", "flammable liquid", "H2S zone",
           "confined space", "toxic gas area", "explosive atmosphere", "high noise zone",
           "radiation exposure zone", "LPG storage zone", "corrosive chemical zone",
           "oxygen deficient zone", "high voltage zone", "pressurized gas storage",
           "benzene exposure zone", "asbestos handling zone", "Class A petroleum store",
           "Class B petroleum store", "ammonia storage zone"]

FULL_SLOTS = {
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

# Three entity types appear in only 3 of the 15 templates each:
#   ACTION_TAKEN  -> templates {0, 5, 10}
#   HAZARD_CLASS  -> templates {2, 6, 12}
#   MATERIAL      -> templates {4, 7, 14}
# These trios are disjoint, so holding out exactly one template from each
# (10, 12, 7) leaves every entity type with >= 2 training templates --
# empirically the threshold where held-out F1 stays high (MATERIAL and
# PROCEDURE_REF both held at 1.000 in the v1 run with 2 templates each;
# HAZARD_CLASS collapsed with only 1).
HOLDOUT_TEMPLATE_IDX = {7, 10, 12}
TRAIN_TEMPLATES = [t for i, t in enumerate(TEMPLATES) if i not in HOLDOUT_TEMPLATE_IDX]
HOLDOUT_TEMPLATES = [TEMPLATES[i] for i in HOLDOUT_TEMPLATE_IDX]


def split_vocab(vocab, holdout_frac=0.2, seed=42):
    rnd = random.Random(seed)
    items = vocab[:]
    rnd.shuffle(items)
    n_hold = max(1, round(len(items) * holdout_frac))
    holdout = sorted(items[:n_hold])
    train = sorted(items[n_hold:])
    return train, holdout


TRAIN_SLOTS, HOLDOUT_SLOTS = {}, {}
for key, (label, vocab) in FULL_SLOTS.items():
    tr, ho = split_vocab(vocab)
    TRAIN_SLOTS[key] = (label, tr)
    HOLDOUT_SLOTS[key] = (label, ho)


def fill(template: str, slots: dict, rnd: random.Random):
    tokens, labels = [], []
    for word in template.split():
        if word.startswith("{") and word.endswith("}"):
            label, vocab = slots[word[1:-1]]
            value_tokens = rnd.choice(vocab).split()
            for i, vt in enumerate(value_tokens):
                tokens.append(vt)
                labels.append(("B-" if i == 0 else "I-") + label)
        else:
            tokens.append(word)
            labels.append("O")
    return tokens, labels


def write_conll(fname, sentences):
    with open(fname, "w") as f:
        for tokens, labels in sentences:
            for t, l in zip(tokens, labels):
                f.write(f"{t}\t{l}\n")
            f.write("\n")
    print(f"{fname}: {len(sentences)} sentences")


def generate(n, templates, slots, seed):
    rnd = random.Random(seed)
    return [fill(rnd.choice(templates), slots, rnd) for _ in range(n)]


def main():
    # In-distribution train/dev: familiar templates, familiar vocab only.
    train = generate(4400, TRAIN_TEMPLATES, TRAIN_SLOTS, seed=1001)
    dev = generate(550, TRAIN_TEMPLATES, TRAIN_SLOTS, seed=1002)
    write_conll("train.txt", train)
    write_conll("dev.txt", dev)

    # Three genuinely held-out test tiers -- zero overlap with train/dev
    # by construction (disjoint template pools and/or disjoint vocab pools).
    test_structural = generate(200, HOLDOUT_TEMPLATES, TRAIN_SLOTS, seed=2001)
    test_vocab = generate(200, TRAIN_TEMPLATES, HOLDOUT_SLOTS, seed=2002)
    test_both = generate(200, HOLDOUT_TEMPLATES, HOLDOUT_SLOTS, seed=2003)
    write_conll("test_holdout_structural.txt", test_structural)
    write_conll("test_holdout_vocab.txt", test_vocab)
    write_conll("test_holdout_both.txt", test_both)

    # Legacy-style in-distribution test, kept only as an "easy" reference
    # point to show the gap vs. the real held-out numbers.
    test_easy = generate(550, TRAIN_TEMPLATES, TRAIN_SLOTS, seed=1003)
    write_conll("test.txt", test_easy)

    all_labels = sorted({l for sents in [train, dev, test_structural, test_vocab, test_both, test_easy]
                          for _, ls in sents for l in ls})
    with open("labels.txt", "w") as f:
        f.write("\n".join(all_labels))
    print(f"labels.txt: {len(all_labels)} labels")

    print("\nHeld-out templates (never in train/dev):")
    for t in HOLDOUT_TEMPLATES:
        print(" ", t)
    print("\nHeld-out vocab values (never in train/dev):")
    for key, (label, vocab) in HOLDOUT_SLOTS.items():
        print(f"  {label}: {vocab}")


if __name__ == "__main__":
    main()

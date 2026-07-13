"""Evaluate a trained NER model separately on each held-out test tier, so you
can see exactly where performance holds up and where it doesn't -- instead of
one aggregate number that hides the difference between memorization and
generalization.

Run after train_ner.py has produced ./gyanvriksh-ner/final :

    python eval_holdout.py --model ./gyanvriksh-ner/final

Evaluates, in order (easiest to hardest):
    test.txt                        - in-distribution (same templates+vocab as train)
    test_holdout_structural.txt      - new sentence templates, familiar vocab
    test_holdout_vocab.txt           - familiar templates, new entity values
    test_holdout_both.txt            - new templates AND new entity values
    test_wild.txt                    - hand-written, not template-based at all (if present)
"""
import argparse
import os

import numpy as np
import torch
from seqeval.metrics import f1_score, classification_report
from transformers import AutoModelForTokenClassification, AutoTokenizer


def _open_text(path):
    # train.txt/dev.txt/test*.txt were written with Windows' default locale
    # encoding (cp1252); test_wild.txt was authored as UTF-8. Try UTF-8 first
    # (it's a strict superset check via decode) and fall back to cp1252 so
    # either kind of file reads correctly without corrupting the other.
    raw = open(path, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    return text.splitlines()


def read_conll(path):
    sentences, labels, tokens, tags = [], [], [], []
    for line in _open_text(path):
        line = line.rstrip("\n")
        if not line:
            if tokens:
                sentences.append(tokens)
                labels.append(tags)
                tokens, tags = [], []
            continue
        t, l = line.split("\t")
        tokens.append(t)
        tags.append(l)
    if tokens:
        sentences.append(tokens)
        labels.append(tags)
    return sentences, labels


def evaluate_file(path, model, tokenizer, id2label, device, batch_size=32):
    sents, gold_labels = read_conll(path)
    all_true, all_pred = [], []
    model.eval()
    with torch.no_grad():
        for i in range(0, len(sents), batch_size):
            batch_tokens = sents[i:i + batch_size]
            batch_tags = gold_labels[i:i + batch_size]
            enc = tokenizer(batch_tokens, truncation=True, is_split_into_words=True,
                             max_length=256, padding=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits
            preds = torch.argmax(logits, dim=-1).cpu().numpy()
            for b, tags in enumerate(batch_tags):
                word_ids = tokenizer(batch_tokens[b], truncation=True, is_split_into_words=True,
                                      max_length=256).word_ids()
                seen = set()
                tp, tl = [], []
                for pos, wid in enumerate(word_ids):
                    if wid is None or wid in seen:
                        continue
                    seen.add(wid)
                    tl.append(tags[wid])
                    tp.append(id2label[preds[b][pos]])
                all_true.append(tl)
                all_pred.append(tp)
    return all_true, all_pred


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="./gyanvriksh-ner/final")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForTokenClassification.from_pretrained(args.model).to(device)
    id2label = model.config.id2label

    files = [
        ("IN-DISTRIBUTION  (test.txt)", "test.txt"),
        ("HELD-OUT: new templates       (test_holdout_structural.txt)", "test_holdout_structural.txt"),
        ("HELD-OUT: new entity values   (test_holdout_vocab.txt)", "test_holdout_vocab.txt"),
        ("HELD-OUT: new templates+values(test_holdout_both.txt)", "test_holdout_both.txt"),
        ("HAND-WRITTEN, non-template    (test_wild.txt)", "test_wild.txt"),
    ]

    summary = []
    for label, fname in files:
        if not os.path.exists(fname):
            print(f"\n[skip] {fname} not found")
            continue
        true, pred = evaluate_file(fname, model, tokenizer, id2label, device)
        f1 = f1_score(true, pred)
        summary.append((label, f1))
        print(f"\n{'=' * 90}\n{label}\n{'=' * 90}")
        print(classification_report(true, pred, digits=3))

    print(f"\n{'=' * 60}\nSUMMARY (micro F1)\n{'=' * 60}")
    for label, f1 in summary:
        print(f"  {f1:.3f}   {label}")


if __name__ == "__main__":
    main()

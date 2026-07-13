"""Fine-tune BERT for industrial NER on the generated CoNLL data.

Run on the GPU server:  python train_ner.py --base bert-base-uncased --epochs 5
Output: ./gyanvriksh-ner/ (best checkpoint) — copy this folder back to
        backend/models/ner_model on your laptop and set NER_BACKEND=bert.
"""
import argparse

import numpy as np
import torch
from datasets import Dataset
from seqeval.metrics import f1_score, classification_report
from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                          DataCollatorForTokenClassification, Trainer,
                          TrainingArguments)


def read_conll(path):
    sentences, labels, tokens, tags = [], [], [], []
    for line in open(path):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="bert-base-uncased")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    label_list = [l.strip() for l in open("labels.txt")]
    label2id = {l: i for i, l in enumerate(label_list)}
    id2label = {i: l for l, i in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base, num_labels=len(label_list), id2label=id2label, label2id=label2id)

    def encode(split):
        sents, labs = read_conll(split)
        ds = Dataset.from_dict({"tokens": sents, "tags": labs})

        def tokenize(batch):
            enc = tokenizer(batch["tokens"], truncation=True, is_split_into_words=True,
                            max_length=256)
            all_labels = []
            for i, tags in enumerate(batch["tags"]):
                word_ids = enc.word_ids(batch_index=i)
                ids, prev = [], None
                for wid in word_ids:
                    if wid is None:
                        ids.append(-100)
                    elif wid != prev:
                        ids.append(label2id[tags[wid]])
                    else:
                        ids.append(-100)
                    prev = wid
                all_labels.append(ids)
            enc["labels"] = all_labels
            return enc

        return ds.map(tokenize, batched=True, remove_columns=["tokens", "tags"])

    train_ds, dev_ds, test_ds = encode("train.txt"), encode("dev.txt"), encode("test.txt")

    def compute_metrics(p):
        preds = np.argmax(p.predictions, axis=2)
        true_labels, true_preds = [], []
        for pred, lab in zip(preds, p.label_ids):
            tl, tp = [], []
            for pi, li in zip(pred, lab):
                if li != -100:
                    tl.append(id2label[li])
                    tp.append(id2label[pi])
            true_labels.append(tl)
            true_preds.append(tp)
        return {"f1": f1_score(true_labels, true_preds)}

    training_args = TrainingArguments(
        output_dir="./gyanvriksh-ner",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=32,
        warmup_steps=200,
        weight_decay=0.01,
        learning_rate=2e-5,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        fp16=torch.cuda.is_available(),
        logging_steps=50,
    )

    trainer = Trainer(model=model, args=training_args,
                      train_dataset=train_ds, eval_dataset=dev_ds,
                      data_collator=DataCollatorForTokenClassification(tokenizer),
                      compute_metrics=compute_metrics)
    trainer.train()

    print("\n=== TEST SET EVALUATION ===")
    preds = trainer.predict(test_ds)
    pred_ids = np.argmax(preds.predictions, axis=2)
    true_labels, true_preds = [], []
    for pred, lab in zip(pred_ids, preds.label_ids):
        tl, tp = [], []
        for pi, li in zip(pred, lab):
            if li != -100:
                tl.append(id2label[li])
                tp.append(id2label[pi])
        true_labels.append(tl)
        true_preds.append(tp)
    print(classification_report(true_labels, true_preds))

    trainer.save_model("./gyanvriksh-ner/final")
    tokenizer.save_pretrained("./gyanvriksh-ner/final")
    print("\nModel saved to ./gyanvriksh-ner/final")
    print("Copy it back with:")
    print("  scp -r kmpooja@<gpu-ip>:~/gyanvriksh-gpu/gyanvriksh-ner/final backend/models/ner_model")


if __name__ == "__main__":
    main()

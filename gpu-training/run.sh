#!/bin/bash
# One-command NER training on the GPU server.
set -e
echo "=== GyanVriksh NER training ==="
pip install -r requirements.txt --quiet
python generate_ner_data.py
python train_ner.py --base bert-base-uncased --epochs 5
echo "Done. Trained model in ./gyanvriksh-ner/final"

# GyanVriksh — GPU Training Bundle

Fine-tunes the industrial NER model (BERT, 12 entity types, BIO tagging) on 5,500
synthetic annotated sentences. Runs on the college GPU server.

## Steps (from your Windows laptop)

1. Copy this folder to the GPU server:
   ```
   scp -r gpu-training <GPU_USER>@<GPU_HOST>:~/gyanvriksh-gpu
   ```
2. SSH in and run:
   ```
   ssh <GPU_USER>@<GPU_HOST>
   cd ~/gyanvriksh-gpu
   bash run.sh
   ```
   Training takes ~10-20 minutes on a modern GPU. The script prints per-entity
   F1 scores on the held-out test set at the end (report these as your NER benchmark).
3. Copy the trained model back to your laptop:
   ```
   scp -r <GPU_USER>@<GPU_HOST>:~/gyanvriksh-gpu/gyanvriksh-ner/final backend/models/ner_model
   ```
4. In `.env`, set `NER_BACKEND=bert`. Restart the workers. Done — NER now runs
   locally with zero API cost.

Until you do this, the system uses the GPT-4o NER backend (`NER_BACKEND=gpt4o`),
which works fine for the demo.

## Optional: run Whisper on the GPU too
Whisper large-v3 transcription is ~4x faster on GPU. If your demo laptop struggles,
transcribe recordings on the server:
```
pip install openai-whisper
whisper recording.wav --model large-v3 --word_timestamps True --output_format json
```
and upload the JSON transcript via the verification API.

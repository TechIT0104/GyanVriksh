# GyanVriksh — How To Run

AI for Industrial Knowledge Intelligence · ET AI Hackathon 2026 · Problem Statement 8

> **Demo build.** Runs on a small **synthetic** dataset (Bharat Chemicals "Unit-3")
> with databases in local Docker — not connected to any real plant. All security
> controls are fully implemented (see `SECURITY.md`); production would add TLS and a
> secrets manager.

---

## Prerequisites

- **Docker Desktop** (running, WSL2 backend on Windows)
- **Python 3.11**
- **Node.js 20+**
- ~16 GB RAM recommended
- **Ollama** with any instruct model (e.g. `mistral`) for the free, fully-local mode
  — *or* an OpenAI API key for GPT-4o mode

---

## 1. One-time setup

From the `gyanvriksh` folder:

```powershell
# a. configure environment (or leave as-is for local Ollama mode)
copy backend\.env.example backend\.env

# b. start infrastructure (Kafka, Neo4j, Qdrant, Postgres, Redis, MinIO)
.\start-infra.bat

# c. set up the backend: venv, dependencies, DB migrations, seed demo data
.\setup-backend.bat
```

`setup-backend.bat` creates the Python venv, installs dependencies, runs Alembic
migrations, initialises Neo4j / Qdrant / Kafka, and loads the demo dataset
(Bharat Chemicals Unit-3).

> **Slow/flaky network?** pip and npm are already configured with long timeouts
> and retries. If a download drops, just re-run the same command — it resumes.

---

## 2. Run the app

Open **two** terminals in the `gyanvriksh` folder:

```powershell
# Terminal 1 — backend (FastAPI on http://127.0.0.1:8000)
.\start-backend.bat
```

```powershell
# Terminal 2 — frontend (Vite on http://localhost:5173)
.\start-frontend.bat
```

Open **http://localhost:5173** and log in with a demo account:

| Role | Email | Password |
|------|-------|----------|
| Maintenance Engineer | engineer@bharatchem.in | gyanvriksh |
| Plant Manager | manager@bharatchem.in | gyanvriksh |
| Field Technician | tech@bharatchem.in | gyanvriksh |
| Compliance Auditor | auditor@bharatchem.in | gyanvriksh |
| Admin | admin@bharatchem.in | gyanvriksh |

**Try it:** ask *"Why do P-101 seals keep failing, and what does OISD-116 say?"*
in **Ask GyanVriksh**, then open **Knowledge Graph** — the evidence nodes light up.
Press the speaker icon on any answer to hear it read aloud.

> **Equipment-QR feature:** it uses one package added after the first setup. If the
> **Equipment QR** page is blank, run once inside `frontend`: `npm install`. Then
> print the stickers and scan one from a phone (via the tunnel URL below) to open
> that machine's voice-first view.

---

## 3. LLM mode

- **Local & free (default):** leave `OPENAI_API_KEY` as the placeholder in
  `backend\.env`. Ensure an Ollama model is installed (`ollama list`); the code
  auto-detects it. Set `OLLAMA_MODEL` to your model name.
- **Cloud (GPT-4o):** paste a real `sk-...` key into `OPENAI_API_KEY`.

> On a CPU the local model is slower (~30s/answer). A GPU or GPT-4o is much faster.

---

## 4. Access from anywhere (optional, for a live demo)

The app is full-stack (needs the local backend + databases), so it cannot be
hosted on static GitHub Pages. To expose your **running local app** publicly:

```powershell
cloudflared tunnel --url http://localhost:5173
```

This prints a public `https://...trycloudflare.com` URL. Stop it with `Ctrl+C`
after the demo (login uses default demo credentials).

---

## 5. Optional

```powershell
# Reproduce the evaluation (resumable; ~1–1.5 hr on CPU for 100 questions)
.\backend\venv\Scripts\activate
python backend\scripts\run_benchmark.py 100

# Fine-tune the industrial NER model on a GPU server
#   see gpu-training\README.md
```

---

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| Backend: `connection refused ... 5432` | Docker/infra not up — run `.\start-infra.bat` |
| `docker-desktop` missing in `wsl -l -v` | Quit Docker Desktop fully, reopen; let engine start |
| Frontend loads but login says "Not Found" | Ensure backend is running; proxy targets `127.0.0.1` |
| `cloudflared` not recognised | Open a new terminal, or use its full install path |

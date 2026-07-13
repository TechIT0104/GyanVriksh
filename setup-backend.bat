@echo off
cd backend
python -m venv venv
call venv\Scripts\activate

REM This machine's connection is slow/flaky. pip's default 15s timeout makes
REM downloads (and even index lookups) fail with read timeouts, which show up
REM as the misleading "No matching distribution found". Give pip a long
REM timeout + many retries for EVERY pip call in this script.
set PIP_DEFAULT_TIMEOUT=300
set PIP_RETRIES=10

python -m pip install "pip==24.2" "setuptools==70.3.0" "wheel==0.43.0"

echo.
echo === Core dependencies (required) ===
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo *** pip install of requirements.txt FAILED - stopping here. Fix the error above and re-run. ***
    exit /b 1
)

echo.
echo === Optional ML dependencies (OCR, embeddings, Whisper transcription) ===
echo === Installed individually so one failure doesn't block the others. ===
echo === App runs fine without these; only scanned-doc OCR / audio transcription ===
echo === / BGE-M3 embeddings need them (embeddings fall back automatically). ===

pip install paddlepaddle==2.6.2
if errorlevel 1 echo WARNING: paddlepaddle failed to install - scanned PDF/image OCR will be unavailable.

pip install paddleocr==2.7.3
if errorlevel 1 echo WARNING: paddleocr failed to install - scanned PDF/image OCR will be unavailable.

pip install FlagEmbedding==1.2.10
if errorlevel 1 echo WARNING: FlagEmbedding failed to install - will fall back to MiniLM embeddings.

pip install sentence-transformers
if errorlevel 1 echo WARNING: sentence-transformers failed to install - embedding fallback unavailable too, embed() will error.

pip install librosa==0.10.2 noisereduce==3.0.2
if errorlevel 1 echo WARNING: librosa/noisereduce failed to install - audio preprocessing will be unavailable.

pip install --no-build-isolation openai-whisper==20231117
if errorlevel 1 (
    echo WARNING: openai-whisper failed to install even with --no-build-isolation.
    echo          Knowledge Preservation Mode transcription will be unavailable until this is resolved.
)

echo.
echo === Database migrations and initialization ===
alembic upgrade head
if errorlevel 1 (
    echo.
    echo *** alembic migration FAILED - stopping here. Is Postgres running? ***
    exit /b 1
)

python scripts\init_neo4j.py
if errorlevel 1 (
    echo.
    echo *** init_neo4j.py FAILED - stopping here. Is Neo4j running? ***
    exit /b 1
)

python scripts\init_qdrant.py
if errorlevel 1 (
    echo.
    echo *** init_qdrant.py FAILED - stopping here. Is Qdrant running? ***
    exit /b 1
)

python scripts\init_kafka.py
if errorlevel 1 (
    echo.
    echo *** init_kafka.py FAILED - stopping here. Is Kafka running? ***
    exit /b 1
)

python scripts\load_regulations.py
if errorlevel 1 (
    echo.
    echo *** load_regulations.py FAILED - stopping here. ***
    exit /b 1
)

python scripts\load_demo_data.py
if errorlevel 1 (
    echo.
    echo *** load_demo_data.py FAILED - stopping here. ***
    exit /b 1
)

echo.
echo Setup complete - all required steps succeeded. Run start-backend.bat next.
echo (Check above for any WARNING lines about optional ML packages.)

@echo off
echo Starting GyanVriksh infrastructure (Kafka, Neo4j, Qdrant, Postgres, Redis, MinIO)...
docker-compose -f docker-compose.infra.yml up -d
echo.
echo Waiting 30s for services to become healthy...
timeout /t 30 /nobreak >nul
docker-compose -f docker-compose.infra.yml ps
echo.
echo Neo4j browser:  http://localhost:7474  (neo4j / gyanvriksh123)
echo Qdrant UI:      http://localhost:6333/dashboard
echo MinIO console:  http://localhost:9001  (minioadmin / minioadmin)

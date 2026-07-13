"""SQLAlchemy ORM models — PostgreSQL metadata store."""
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text, create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.config import settings

Base = declarative_base()
engine = create_engine(settings.postgres_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def utcnow():
    return datetime.now(timezone.utc)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="maintenance_engineer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    file_id = Column(String(64), unique=True, index=True, nullable=False)
    original_name = Column(String(512), nullable=False)
    doc_type = Column(String(64), default="UNKNOWN")  # SOP / MAINTENANCE_REPORT / REGULATION / INCIDENT / AUDIO ...
    storage_path = Column(String(1024), nullable=False)
    uploader = Column(String(255))
    upload_time = Column(DateTime(timezone=True), default=utcnow)
    status = Column(String(32), default="QUEUED")  # QUEUED / OCR / NER / EMBEDDING / INDEXED / ERROR
    status_detail = Column(String(512), default="")
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    entity_count = Column(Integer, default=0)
    error = Column(Text, default="")

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    chunk_id = Column(String(80), unique=True, index=True, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    page_number = Column(Integer, default=1)
    chunk_index = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    meta = Column(JSON, default=dict)

    document = relationship("Document", back_populates="chunks")


class ExtractedTable(Base):
    __tablename__ = "extracted_tables"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    page_number = Column(Integer)
    table_json = Column(JSON)


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"
    id = Column(Integer, primary_key=True)
    check_id = Column(String(64), unique=True, index=True)
    procedure_id = Column(String(128))
    regulations = Column(JSON)          # list of regulation ids checked
    user_email = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    summary = Column(JSON)              # {compliant: n, partial: n, non_compliant: n}
    gaps = Column(JSON)                 # list of gap dicts
    report_text = Column(Text)


class PreservationSession(Base):
    __tablename__ = "preservation_sessions"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, index=True)
    expert_name = Column(String(255))
    equipment_focus = Column(String(64), default="")
    audio_path = Column(String(1024), default="")
    duration_seconds = Column(Float, default=0)
    status = Column(String(32), default="RECORDING")  # RECORDING / TRANSCRIBING / VERIFYING / PUBLISHED
    transcript = Column(Text, default="")
    word_timestamps = Column(JSON, default=list)
    insights = Column(JSON, default=list)  # extracted insight cards
    created_at = Column(DateTime(timezone=True), default=utcnow)


class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), index=True)
    query = Column(Text)
    answer = Column(Text)
    confidence = Column(String(16))
    citations = Column(JSON, default=list)
    response_time_ms = Column(Integer)
    feedback = Column(Integer, default=0)  # 1 up, -1 down, 0 none
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_email = Column(String(255))
    action = Column(String(255))
    detail = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class MaintenanceAlert(Base):
    __tablename__ = "maintenance_alerts"
    id = Column(Integer, primary_key=True)
    equipment_tag = Column(String(64), index=True)
    alert_type = Column(String(64))  # HEALTH_SCORE / OVERDUE / PATTERN
    message = Column(Text)
    severity = Column(String(16), default="MEDIUM")
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

"""GyanVriksh — FastAPI application entrypoint."""
import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth.jwt import create_token, get_current_user, hash_password, verify_password
from app.auth.models import LoginRequest, TokenResponse, UserOut
from app.config import settings
from app.models.db_models import Base, User, engine, get_db
from app.security import SecurityHeadersMiddleware, check_login_rate, warn_if_insecure

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("gyanvriksh")

app = FastAPI(
    title="GyanVriksh — Tree of Knowledge",
    description="AI-Powered Industrial Knowledge Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.api.v1 import admin, compliance, copilot, documents, graph, maintenance, preserve  # noqa: E402

API = "/api/v1"
app.include_router(documents.router, prefix=f"{API}/documents", tags=["documents"])
app.include_router(copilot.router, prefix=f"{API}/copilot", tags=["copilot"])
app.include_router(compliance.router, prefix=f"{API}/compliance", tags=["compliance"])
app.include_router(maintenance.router, prefix=f"{API}/maintenance", tags=["maintenance"])
app.include_router(preserve.router, prefix=f"{API}/preserve", tags=["preserve"])
app.include_router(graph.router, prefix=f"{API}/graph", tags=["graph"])
app.include_router(admin.router, prefix=f"{API}/admin", tags=["admin"])

# WebSocket routers (documents status + copilot stream register their own WS routes)
app.include_router(documents.ws_router)
app.include_router(copilot.ws_router)

DEFAULT_USERS = [
    ("manager@bharatchem.in", "gyanvriksh", "Priya Deshmukh", "plant_manager"),
    ("engineer@bharatchem.in", "gyanvriksh", "Arjun Mehta", "maintenance_engineer"),
    ("tech@bharatchem.in", "gyanvriksh", "Sunil Yadav", "field_technician"),
    ("auditor@bharatchem.in", "gyanvriksh", "Kavita Rao", "compliance_auditor"),
    ("admin@bharatchem.in", "gyanvriksh", "Admin", "admin"),
]


@app.on_event("startup")
def startup():
    warn_if_insecure(settings)
    Base.metadata.create_all(engine)
    from app.models.db_models import SessionLocal
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            for email, pw, name, role in DEFAULT_USERS:
                db.add(User(email=email, password_hash=hash_password(pw), name=name, role=role))
            db.commit()
            logger.info("Seeded %d default users", len(DEFAULT_USERS))
    finally:
        db.close()


@app.post(f"{API}/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    check_login_rate(request.client.host if request.client else "unknown")
    user = db.query(User).filter(User.email == body.email, User.is_active == True).first()  # noqa: E712
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return TokenResponse(
        access_token=create_token(user.id, user.email, user.role, user.name),
        role=user.role,
        name=user.name,
    )


@app.get(f"{API}/auth/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    u = db.query(User).get(int(user["sub"]))
    if not u:
        raise HTTPException(404, "User not found")
    return u


@app.get("/health")
def health():
    return {"status": "ok", "service": "gyanvriksh-api"}

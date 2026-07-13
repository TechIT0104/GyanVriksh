"""Role-based access control. Roles per README page 1."""
from fastapi import Depends, HTTPException, status

from app.auth.jwt import get_current_user

ROLES = ["plant_manager", "maintenance_engineer", "field_technician", "compliance_auditor", "admin"]

# Which roles may access which feature areas
PERMISSIONS: dict[str, list[str]] = {
    "documents": ["plant_manager", "maintenance_engineer", "admin", "compliance_auditor"],
    "copilot": ROLES,  # everyone
    "compliance": ["plant_manager", "compliance_auditor", "admin"],
    "maintenance": ["plant_manager", "maintenance_engineer", "field_technician", "admin"],
    "preserve": ["plant_manager", "maintenance_engineer", "admin"],
    "graph": ["plant_manager", "maintenance_engineer", "compliance_auditor", "admin"],
    "admin": ["admin"],
}


def require(area: str):
    """Dependency factory: require(area) -> raises 403 unless user's role is allowed."""

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in PERMISSIONS.get(area, []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Role '{user['role']}' cannot access {area}")
        return user

    return checker

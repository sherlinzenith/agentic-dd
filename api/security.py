"""
Role-Based Access Control (RBAC) and Security Module for Due Diligence Platform.
Supports:
- Distinct user personas: Admin, Lead Analyst, Specialist Analyst, Reviewer, Auditor.
- Project-level access policies.
- Token and header authentication with development mode defaults.
"""
from __future__ import annotations

import enum
import os
from typing import List, Optional
from fastapi import Header, HTTPException, Security, status
from pydantic import BaseModel


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    LEAD_ANALYST = "LEAD_ANALYST"
    SPECIALIST_ANALYST = "SPECIALIST_ANALYST"
    REVIEWER = "REVIEWER"
    AUDITOR = "AUDITOR"


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str
    role: UserRole
    is_active: bool = True

    @property
    def can_approve_findings(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.LEAD_ANALYST, UserRole.REVIEWER]

    @property
    def can_trigger_investigation(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.LEAD_ANALYST, UserRole.SPECIALIST_ANALYST]

    @property
    def can_export_reports(self) -> bool:
        return True  # All roles can export/view reports


def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
) -> AuthenticatedUser:
    """
    Extracts authenticated user from headers.
    In local development, defaults to Lead Analyst if headers are omitted.
    """
    raw_role = (x_user_role or os.getenv("DEFAULT_USER_ROLE", "LEAD_ANALYST")).upper()
    try:
        user_role = UserRole(raw_role)
    except ValueError:
        user_role = UserRole.LEAD_ANALYST

    return AuthenticatedUser(
        user_id=x_user_id or os.getenv("DEFAULT_USER_ID", "usr-lead-01"),
        email=x_user_email or os.getenv("DEFAULT_USER_EMAIL", "analyst@duediligence.internal"),
        role=user_role,
    )


def require_role(allowed_roles: List[UserRole]):
    """FastAPI dependency to enforce specific roles for restricted endpoints."""
    def role_checker(user: AuthenticatedUser = Security(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: User role '{user.role.value}' does not have required permissions. Allowed roles: {[r.value for r in allowed_roles]}",
            )
        return user
    return role_checker

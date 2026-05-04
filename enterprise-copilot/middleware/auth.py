"""
Authentication and RBAC middleware for the Enterprise Copilot FastAPI application.
Simplified to use a direct Header injection (X-Employee-ID) instead of JWT.
"""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

import db.crud as crud
from db.database import get_db
from db.models import User


def get_current_user(
    x_employee_id: str = Header(..., alias="X-Employee-ID", description="The employee ID simulating the login session."),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts the X-Employee-ID header,
    then returns the corresponding User object from the database.

    Args:
        x_employee_id: Injected by FastAPI from headers.
        db: SQLAlchemy session injected by FastAPI.

    Returns:
        The authenticated User ORM object.

    Raises:
        HTTPException 401 if header is missing.
        HTTPException 404 if the user no longer exists in the DB.
    """
    if not x_employee_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide X-Employee-ID header.",
        )

    user = crud.get_user_by_employee_id(db, x_employee_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with Employee ID '{x_employee_id}' not found.")

    return user


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory that enforces role-based access control.

    Usage:
        @router.get("/admin/users", dependencies=[Depends(require_role("admin"))])

    Args:
        *allowed_roles: One or more role strings that are permitted to access the endpoint.

    Returns:
        A FastAPI dependency function that validates the current user's role.
    """
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        """Inner dependency: raises 403 if the user's role is not in allowed_roles."""
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}. Your role: {current_user.role}.",
            )
        return current_user

    return _dependency

"""
Common API dependencies.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.core.security import get_current_active_user
from app.core.context import get_organization_id


async def get_current_user_with_org(
    current_user: dict = Depends(get_current_active_user),
    org_id: UUID = Depends(get_organization_id)
) -> tuple[dict, UUID]:
    """Get current user with organization context."""
    return current_user, org_id


async def get_db_with_context(
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_organization_id)
) -> tuple[AsyncSession, UUID]:
    """Get database session with organization context."""
    # Set organization context for RLS
    await db.execute(f"SELECT set_organization_context('{org_id}')")
    return db, org_id

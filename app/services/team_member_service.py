from fastapi import HTTPException,status,Depends
from sqlalchemy import select
from app.models.team_model import TeamMember,Team
from app.core.db import db_dependency
from app.models.user_model import User
from app.core.dependencies import get_current_user
from app.services.permission_service import PermissionService


class TeamMemberService:
    async def add_member(
            self,
            team_id: int,
            user_id: int,
            db: db_dependency,
            current_user: User = Depends(get_current_user)
    ):
        permission = PermissionService().has_permission(
            role=current_user.role,
            resource_type="team",
            action="update"
            )

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
            )

        team = await db.scalar(
            select(Team).where(
                Team.id == team_id,
                Team.is_deleted == False,
                Team.is_active == True,
                Team.workspace_id == current_user.workspace_id,

            )
        )

        user = await db.scalar(
            select(User).where(
                User.id == user_id,
            )
        )
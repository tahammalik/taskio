from logging import getLogger
from sqlalchemy import select
from fastapi import HTTPException, status,Depends
from app.core.db import db_dependency
from app.core.dependencies import get_current_user
from app.models.team_model import Team
from app.models.user_model import User
from app.schemas.team_schema import CreateTeam
from app.services.permission_service import PermissionService

logger = getLogger(__name__)

class TeamService:
    def __init__(self):
        pass

    async def create_team(self, group_data: CreateTeam, db: db_dependency):
        new_group = Team(
            team_name=group_data.team_name,
            description=group_data.description
        )

        try:
            db.add(new_group)
            await db.commit()
            await db.refresh(new_group)
            return new_group
        except Exception as e:
            await db.rollback()
            logger.error("DB ERROR: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )
    async def get_team(self,
                    role:str,
                    workspace_id:int,
                    user_id: int | None = None,
                    current_user: User = Depends(get_current_user),
                    db: db_dependency = None
                ):
        permission = PermissionService().has_permission(role=role,resource_type="team",action="read")
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if role == "admin":
            team = await db.scalars(
                select(Team).where(
                    Team.workspace_id == workspace_id,
                    Team.is_active == True,
                    Team.is_delete == False,
                )
            )
        elif role == "member":
            team = await db.scalars(
                select(Team).where(
                    Team.workspace_id == workspace_id,
                    Team.leader_id == user_id,
                    Team.is_active == True,
                    Team.is_delete == False,
                )
            )
        else:
            team = await db.scalars(
                select(Team).where(
                    Team.id == current_user.team_id,
                    Team.is_active == True,
                    Team.is_delete == False,
                )
            )

        return team

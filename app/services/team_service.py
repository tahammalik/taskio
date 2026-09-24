from logging import getLogger
from sqlalchemy import select,update
from fastapi import HTTPException, status,Depends
from app.core.db import db_dependency
from app.core.dependencies import get_current_user
from app.models.team_model import Team,TeamHistory
from app.models.user_model import User
from app.schemas.team_schema import CreateTeam,TeamUpdate
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
                status_code=status.HTTP_403_FORBIDDEN,
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
    async def delete(
            team_id: int,
            db: db_dependency,
            role:str,
            current_user: User = Depends(get_current_user)
        ):

        permission = PermissionService().has_permission(role=role,resource_type="team",action="delete")

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
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found",
            )
        try:
            await db.execute(
                update(Team)
                .where(Team.id == team_id, Team.workspace_id == current_user.workspace_id)
                .values({"is_active": False, "is_deleted": True})
            )
            await db.commit()
            logger.info(f"team deleted : {team.team_name}")
            return {"message": "Team deleted successfully"}
        except Exception as e:
            await db.rollback()
            logger.error(f"DB ERROR: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def update(
            team_id:int,
            role:str,
            update_data:TeamUpdate,
            db:db_dependency,
            current_user: User = Depends(get_current_user)
    ):
        permission = PermissionService().has_permission(role=role,resource_type="team",action="update")

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
            )

        team = await db.scalar(
            select(Team).where(
                Team.id == team_id,
                Team.is_deleted == False,
                Team.is_active == True,
                Team.workspace_id == current_user.workspace_id,
            )
        )

        update_dict = update_data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided to update"
            )

        history_entries = []
        for field,new_value in update_dict.items():
            old_value = getattr(team,field)
            if old_value != new_value:
                history_entries.append(
                    TeamHistory(
                        team_id = team_id,
                        changed_by = current_user.id,
                        field_name=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None
                    )
                )
        for key,value in update_dict.items():
            setattr(team,key,value)
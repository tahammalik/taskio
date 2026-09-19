from fastapi import HTTPException
from app.core.db import db_dependency
from app.models.invitation_model import Invitation
from app.models.user_model import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class InvitationService:
    def __init__(self):
        pass

    async def invite_user(self,
        invite:CreateInvitation,
        current_user:User,
        db:db_dependency
    ) -> Invitation:
        workspace = await db.scalar(
            select(Workspace).where(
                Workspace.id == current_user.workspace_id,
                Workspace.is_active == True
            )
        )
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
        existing_invite = await db.scalar(
            select(Invitation).where(
                Invitation.email == invite.email,
                Invitation.status == "pending"
            )
        )

        if existing_invite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An invitation for this user already exists"
            )
        # generate a unique token for the invitation
        token = Invitation.generate_token()
        # First add invitation to the database
        new_invitation = Invitation(
            email=invite.email,
            role=invite.role,
            workspace_id=current_user.workspace_id,
            invited_by=current_user.id,
            token=token,
            status="pending",
            expires_at=Invitation.default_expiry()
        )
        try:
            db.add(new_invitation)
            await db.commit()
            #await db.refresh(new_invitation)
        except Exception as e:
            await db.rollback()
            logger.error("DB ERROR: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )

        await send_invite_email(
            receiver_email=invite.email,
            token=token,
            workspace_name=workspace.name
        )

        return ResponseInvitation(**new_invitation.__dict__)

    async def get_invitation_by_token(self,token:str,db:db_dependency):
        invitation = await db.scalar(
            select(Invitation).where(
                Invitation.token == token
            )
        )

        if not invitation:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if invitation.status != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invitation is no longer valid")
        if invitation.expires_at < datetime.now(timezone.utc):
            invitation.status = "expired"
            try:
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.exception("Failed to expire invitation, ERROR: %s", e)
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invitation expired"
                )
            raise HTTPException(
                status=400,
                detail="Invitation not found"
            )
        return invitation


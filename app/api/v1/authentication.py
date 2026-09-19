"""
This is file handle authentication router
"""
import jwt
from typing import Annotated
from sqlalchemy import select, update
from fastapi import APIRouter, Depends, HTTPException, status,Response,Request
from fastapi.security import OAuth2PasswordRequestForm
from app.core.db import db_dependency
from app.core.dependencies import get_current_user
from app.core.logging_config import get_logger
from app.core.security import (create_access_token,
                               hash_password,
                               create_refresh_token,
                               is_refresh_token_valid_and_revoke,
                               decode_token,
                               revoke_refresh_token)
from app.models.invitation_model import Invitation
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserResponse
from app.services.authentication_service import authenticate_user,is_email_exist,is_username_exist
from app.core.config import SecretConfig
from datetime import datetime, timezone

# from app.core.dependencies import require_role, get_current_user

logger = get_logger(__name__)
secrets = SecretConfig()

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# Signup endpoint for creating a new user
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(user_data: UserCreate, db: db_dependency):
    invitation = None

    if user_data.token:
        invitation = await db.scalar(
            select(Invitation).where(
                Invitation.token == user_data.token,
            )
        )

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation token",
            )
        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is {invitation.status}",
            )
        if invitation.expires_at < datetime.now(timezone.utc):
            invitation.status = "expired"
            await db.commit()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")
        
        if invitation.email != user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match the invitation",
            )

    # Check if the email or username already exists
    if await is_email_exist(user_data.email, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    if await is_username_exist(user_data.username, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=hash_password(user_data.password),
        role=invitation.role if invitation else "user",
        workspace_id=invitation.workspace_id if invitation else None,
    )


    try:
        db.add(new_user)
        await db.flush()  # Flush to get the new user's ID
        if invitation:
            invitation.status = "accepted"

        await db.commit()
        db.refresh(new_user)  # Refresh to get the updated state of the new user
        logger.info(f"user created {new_user.username}")
        return new_user

    except Exception as e:
        await db.rollback()
        logger.error(f"DB ERROR: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


@router.post("/login",status_code=status.HTTP_200_OK)
async def login(response:Response,form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):

    user = await authenticate_user(form_data.username, form_data.password, db=db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = await create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(data={"sub": str(user.id)})

    response.set_cookie(
        key="refresh_token",
        secure=True,
        value=refresh_token,
        httponly=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")

    payload = await decode_token(refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(401, "Invalid refresh token")

    jti = payload.get("jti")
    username = payload.get("sub")

    # This atomically checks and revokes the token
    if not await is_refresh_token_valid_and_revoke(jti):
        raise HTTPException(401, "Refresh token invalid or already used")

    # Generate new tokens
    new_access = await create_access_token(data={"sub": username})
    new_refresh = await create_refresh_token(data={"sub": username})

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60
    )
    return {"access_token": new_access, "token_type": "bearer"}

@router.post("/logout")
async def logout(request:Request,response:Response):
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = await decode_token(token,expected_type="refresh")
            await revoke_refresh_token(payload["jti"])
        except Exception:
            pass
    response.delete_cookie("refresh_token")
    return {"detail":"logout"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Get current authenticated user information
    """
    return current_user

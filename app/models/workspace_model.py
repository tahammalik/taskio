from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func,UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

class Workspace(Base):
    __tablename__ = 'workspaces'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_by: Mapped[Optional[int]] = mapped_column(Integer,
                                                      ForeignKey('users.id', use_alter=True,
                                                                 name='fk_workspace_created_by'
                                                                ),
                                                      nullable=True
                                                    )

    projects = relationship('Project', back_populates='workspace')
    users = relationship('User', foreign_keys='User.workspace_id', back_populates='workspace')
    teams = relationship('Team', foreign_keys='Team.workspace_id', back_populates='workspace')
    invitations = relationship("Invitation", back_populates="workspace", cascade="all, delete-orphan")
    related_workspace = relationship('WorkspaceMembership', back_populates='user_workspace')

class WorkspaceMembership(Base):
    __tablename__ = 'workspacemembership'

    id: Mapped[int] = mapped_column(primary_key=True,index=True)
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey('users.id'),nullable=False)
    workspace_id: Mapped[int] = mapped_column(Integer,ForeignKey('workspaces.id'), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now()) 

    __table_args__ = (
    UniqueConstraint(
        "user_id",
        "workspace_id",
        name="uq_user_workspace"
        ),
    )

    user = relationship('User',
                        foreign_keys=[user_id],
                        back_populates='workspacemembar'
                    )
    user_workspace = relationship(
        'Workspace',
        foreign_keys=[workspace_id],
        back_populates='related_workspace'
    )
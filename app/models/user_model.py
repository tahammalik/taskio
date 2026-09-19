from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default='user')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    workspace_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('workspaces.id'), default=None)
    team_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    # Relations
    workspace = relationship('Workspace', foreign_keys=[workspace_id], back_populates='users')
    created_tasks = relationship('Task', foreign_keys='Task.created_by', back_populates='creator_manager')
    assigned_tasks = relationship('Task', foreign_keys='Task.assign_to', back_populates='assigned_employee')
    led_teams = relationship('Team', back_populates='leader')
    teams = relationship('Team', secondary='team_members', back_populates='members')
    project_history = relationship('ProjectHistory', back_populates='user')
    project_initiator = relationship('Project',back_populates='initiator')
    workspacemembar = relationship('WorkspaceMembership',back_populates='user')


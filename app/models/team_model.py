from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func,Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

class TeamMember(Base):
    __tablename__ = 'team_members'

    team_id: Mapped[int] = mapped_column(Integer, ForeignKey('teams.id'), primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), primary_key=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class Team(Base):
    __tablename__ = 'teams'

    __table_args__ = (
        UniqueConstraint('team_name', 'workspace_id', name='uq_team_name_workspace'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    team_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    workspace_id: Mapped[int] = mapped_column(Integer, ForeignKey('workspaces.id'), nullable=False)
    leader_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)

    workspace = relationship('Workspace', foreign_keys=[workspace_id], back_populates='teams')
    leader = relationship('User', back_populates='led_teams')
    tasks = relationship('Task', back_populates='team', cascade='all, delete-orphan')
    projects = relationship('Project', secondary='project_teams', back_populates='teams')
    members = relationship('User', secondary='team_members', back_populates='teams')
    history = relationship()

class TeamHistory(Base):

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, index=True)

    team = relationship('Team',back_populates='history')
    user = relationship('User', back_populates='team_history')
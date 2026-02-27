"""SQLAlchemy models for the Organization module.

Only settings and deletion requests live in Postgres.
Organisation metadata, members, and invitations are stored in Keycloak.
"""

from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from datetime import datetime

from sqlalchemy import JSON, Text, String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class OrgBaseSQLModel(BaseSQLModel):
    """Base SQL Model for the Organization schema."""

    __abstract__ = True
    __table_args__ = {"schema": "Organization"}


class OrgSettings(WithCreateUpdateTimestamp, OrgBaseSQLModel):
    """Per-organization settings stored in Postgres."""

    __tablename__ = "Settings"

    org_id: Mapped[str] = mapped_column(
        String(128), primary_key=True, nullable=False
    )
    rate_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        doc="Requests per minute. NULL inherits global default.",
    )
    extra: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Additional flat key-value settings.",
    )


class OrgMetadata(WithCreateUpdateTimestamp, OrgBaseSQLModel):
    """Persisted organization metadata for invariants and auditing."""

    __tablename__ = "Metadata"

    org_id: Mapped[str] = mapped_column(
        String(128), primary_key=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )


class OrgDeletionRequest(WithCreateUpdateTimestamp, WithID, OrgBaseSQLModel):
    """Tracks an organization deletion request with a 30-day cancel window."""

    __tablename__ = "DeletionRequests"

    org_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        init=False,
    )
    cancel_before: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cancelled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )


class OrgProject(WithCreateUpdateTimestamp, WithID, OrgBaseSQLModel):
    """A project inside an organization, stored in Postgres."""

    __tablename__ = "Projects"

    org_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class OrgInvitation(
    WithCreateUpdateTimestamp, WithUUID, WithID, OrgBaseSQLModel
):
    """Tracks an invitation and its intended permissions.

    The Keycloak invite flow handles the actual email;
    this record stores the permissions to apply on acceptance.
    """

    __tablename__ = "Invitations"

    org_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    invited_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default=None
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Org permissions to apply when the user accepts.",
    )
    token: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        default=None,
        init=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        init=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        init=False,
    )

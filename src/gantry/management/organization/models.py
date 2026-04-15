"""SQLAlchemy models for the Organization module.

Only settings and deletion requests live in Postgres.
Organisation metadata, members, and invitations are stored in Keycloak.
"""

from gantry.db.base import BaseSQLModel
from gantry.db.utils import WithID, WithCreateUpdateTimestamp

from datetime import datetime

from sqlalchemy import JSON, String, Integer, DateTime, BigInteger, func
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
    spending_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
        doc="Monthly spending limit as a scaled integer. NULL means unlimited.",
    )
    extra: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Additional flat key-value settings.",
    )


class OrgDeletionRequest(WithID, OrgBaseSQLModel):
    """Tracks an organization deletion request."""

    __tablename__ = "DeletionRequests"

    org_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        init=False,
    )

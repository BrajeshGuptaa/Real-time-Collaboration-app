from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Index, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    snapshot_version: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_blob: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ops = relationship("Operation", back_populates="document", cascade="all, delete-orphan")


class Operation(Base):
    __tablename__ = "ops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    client_id: Mapped[str] = mapped_column(String(255), index=True)
    logical_ts: Mapped[int] = mapped_column(BigInteger, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    applied_to_version: Mapped[int] = mapped_column(Integer)

    document = relationship("Document", back_populates="ops")


Index("ix_ops_doc_ts", Operation.document_id, Operation.logical_ts)

import os
from shared.database import Base
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

SCHEMA = os.getenv("DATABASE_SCHEMA")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": SCHEMA}


    status: Mapped[str] = mapped_column(String, default="pending")
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.file_metadata.id"))
    result_data: Mapped[dict] = mapped_column(JSONB, default=None,nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    file: Mapped["FileMetaData"] = relationship(back_populates="jobs")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": SCHEMA}

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.jobs.id"), index=True
    )
    service: Mapped[str] = mapped_column(String(255))
    routing_key: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class FileMetaData(Base):
    __tablename__ = "file_metadata"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255),nullable=False)
    type: Mapped[str] = mapped_column(String(20),nullable=False)
    upload_id: Mapped[str] = mapped_column(String, index=True,nullable=False)
    storage_location: Mapped[str] = mapped_column(String(255),nullable=False)
    bucket :Mapped[str] = mapped_column(String, default="uploads")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="file")

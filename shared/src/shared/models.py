import os
from shared.database import Base
from sqlalchemy import Column, String,Text,ForeignKey
from sqlalchemy.dialects.postgresql import UUID,TIMESTAMP,JSONB
from sqlalchemy.sql import func
import uuid

SCHEMA = os.getenv("DATABASE_SCHEMA")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(String, index=True,nullable=False)  # Links tasks to the same uploaded file
    job_type = Column(String, nullable=False)  # 'virus_scan' OR 'image_process'
    status = Column(String, default="pending")
    result_data = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": SCHEMA}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.jobs.id"), index=True, nullable=False
    )
    service = Column(String(255), nullable=False)
    routing_key = Column(String(255),nullable=False)
    action = Column(Text,nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
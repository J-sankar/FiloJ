import os
from shared.database import Base
from sqlalchemy import String,  ForeignKey,Boolean,DateTime
from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

SCHEMA = os.getenv("DATABASE_SCHEMA")
class Developer(Base):
    __tablename__ = "developers"
    __table_args__ = {"schema": SCHEMA}
    id         : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email      : Mapped[str]       = mapped_column(String(255), unique=True, nullable=False, index=True)
    password   : Mapped[str]       = mapped_column(String(255), nullable=False)
    name       : Mapped[str]       = mapped_column(String(255), nullable=False)
    plan       : Mapped[str]       = mapped_column(String(50), default="free")
    is_active  : Mapped[bool]      = mapped_column(Boolean, default=True)
    created_at : Mapped[datetime]  = mapped_column(server_default=func.now())
    updated_at : Mapped[datetime]  = mapped_column(server_default=func.now(), onupdate=func.now())
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="developer")
    api_keys   :  Mapped[list["ApiKey"]] = relationship(back_populates="developer")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": SCHEMA}
    id           : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token        : Mapped[str]       = mapped_column(String, unique=True, nullable=False, index=True)
    developer_id : Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.developers.id"))
    is_revoked   : Mapped[bool]      = mapped_column(Boolean, default=False)
    expires_at   : Mapped[datetime]  = mapped_column(DateTime(timezone=True),nullable=False)
    created_at   : Mapped[datetime]  = mapped_column(server_default=func.now())
    developer: Mapped["Developer"] = relationship(back_populates="refresh_tokens")


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": SCHEMA}

    id           : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key_hash     : Mapped[str]       = mapped_column(String, unique=True, nullable=False, index=True)
    display_prefix: Mapped[str]      = mapped_column(String(255), nullable=False)
    name         : Mapped[str]       = mapped_column(String(255), nullable=False)  # "production", "test"
    developer_id : Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.developers.id"))
    is_active    : Mapped[bool]      = mapped_column(Boolean, default=True)
    last_used_at : Mapped[datetime]  = mapped_column(nullable=True)
    created_at   : Mapped[datetime]  = mapped_column(server_default=func.now())

    developer: Mapped["Developer"] = relationship(back_populates="api_keys")
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    original_url: Mapped[str] = mapped_column(String, nullable=False)

    short_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
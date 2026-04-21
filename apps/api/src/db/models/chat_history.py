from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    pac_code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    references: Mapped[list] = mapped_column(JSON, default=list)
    robot_config: Mapped[dict] = mapped_column(JSON, default=dict)
    entry_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="troubleshooting"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

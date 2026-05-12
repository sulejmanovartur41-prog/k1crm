from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    child_name: Mapped[str] = mapped_column(String(100))
    child_birth_date: Mapped[date] = mapped_column(Date)
    parent_name: Mapped[str] = mapped_column(String(100))
    parent_phone: Mapped[str] = mapped_column(String(20))
    passport_data: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, inactive
    # Группа, к которой прикреплён ученик — для фильтрации списков посещаемости.
    # NULL = не прикреплён к группе (новый клиент).
    group_name: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

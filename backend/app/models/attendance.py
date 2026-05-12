from datetime import datetime
from sqlalchemy import DateTime, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Attendance(Base):
    __tablename__ = "attendance"
    # Одна запись посещаемости на ученика в уроке. Без этого constraint
    # параллельные mark-запросы (учитель + админ) создают дубли.
    __table_args__ = (
        UniqueConstraint("lesson_id", "client_id", name="uq_attendance_lesson_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    present: Mapped[bool] = mapped_column(Boolean, default=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    marked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

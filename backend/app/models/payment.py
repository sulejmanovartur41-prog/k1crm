from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"
    # Одна оплата на (клиент, период). Без constraint два менеджера случайно
    # фиксируют одну и ту же оплату дважды — БД отдаёт IntegrityError, ручкой
    # 409 на клиенте.
    __table_args__ = (
        UniqueConstraint("client_id", "period_from", "period_to", name="uq_payment_client_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    period_from: Mapped[date] = mapped_column(Date)
    period_to: Mapped[date] = mapped_column(Date)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending, paid, overdue, blocked
    method: Mapped[str | None] = mapped_column(String(20))  # cash, qr
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

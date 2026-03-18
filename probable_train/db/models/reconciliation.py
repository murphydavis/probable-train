from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from probable_train.db import ProbableTrainBase


# # for any potential global changes
# class ProbableTrainBase(DeclarativeBase):
#     type_annotation_map = {
#         datetime: TIMESTAMP(timezone=True),
#         Decimal: Numeric(12, 2),
#     }


class Account(ProbableTrainBase):
    __tablename__ = "account"

    id: Mapped[str] = mapped_column(primary_key=True)
    create_ts: Mapped[datetime] = mapped_column(insert_default=datetime.utcnow)


class Position(ProbableTrainBase):
    """
    information from bank position reports
    """

    __tablename__ = "position"

    id: Mapped[int] = mapped_column(primary_key=True)
    # id: Mapped[Annotated[int, mapped_column(primary_key=True)]]
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    custodian: Mapped[Optional[str]]  # not sure if this is fk
    market_value = Mapped[Decimal]
    report_date: Mapped[date]
    share_qty: Mapped[int]
    ticker: Mapped[str]


class Trade(ProbableTrainBase):
    """
    information from trade files after normalized by ingest
    """

    __tablename__ = "trade"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    custodian: Mapped[str]  # not sure if this is fk
    market_value = Mapped[Decimal]
    settlement_date: Mapped[date]
    share_qty: Mapped[int]
    ticker: Mapped[str]
    trade_date: Mapped[Optional[date]]

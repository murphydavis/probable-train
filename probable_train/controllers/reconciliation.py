"""
Controller for file ingest logic and associated helpers
"""

# TODO: get proper logic for this report
from collections import defaultdict

from flask import jsonify
from sqlalchemy import and_, select

from probable_train.db import db_session
from probable_train.db.models.reconciliation import Account, Position, Trade


def get_reconciliation_report(report_date):
    accounts = db_session.query(Account).all()
    reconciliation_report = {}
    account_report = {}
    for account in accounts:
        account_report[account.id] = defaultdict(dict)

        stmt = (
            select(Position)
            .where(
                and_(
                    Position.account_id == account.id,
                    Position.report_date <= report_date,
                )
            )
            .order_by(Position.report_date)
        )
        positions = db_session.execute(stmt).scalars().all()
        for position in positions:
            account_report[account.id][position.ticker]["position"] = {
                "shares": position.share_qty,
                "market_value": position.market_value,
                "custodian": position.custodian,
            }
        # TODO: I have made the assumption that the most recent bank position
        # for a given ticker is "canonical"/the source of truth. I know this isn't
        # a fully correct implementation, given I can also at this point have
        # duplicate values, but I will set that aside for the moment.

        stmt = (
            select(Trade)
            .where(
                and_(
                    Trade.account_id == account.id, Trade.settlement_date <= report_date
                )
            )
            .order_by(Trade.settlement_date)
        )
        trades = db_session.execute(stmt).scalars().all()
        for trade in trades:
            account_report[account.id][trade.ticker]["trades"] = trade
        # ASSUMPTION: the SUM of all trades settled up to a given date is what matters
        # This may be naive but that's the operating idea of this implementation

        # reconciliation_report[account.id] = {
        #     'positions': positions,
        #     'trades': trades,
        # }
        print(account.id)

    return jsonify(reconciliation_report)

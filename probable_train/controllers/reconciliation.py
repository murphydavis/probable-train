"""
Controller for file ingest logic and associated helpers
"""

# TODO: get proper logic for this report
from flask import jsonify
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import outerjoin

from probable_train.db import db_session
from probable_train.db.models.reconciliation import Account, Position, Trade


def get_reconciliation_report(report_date):
    # Single query joining all tables with COALESCE to get position and trade data
    stmt = (
        select(
            Account.id.label("account_id"),
            func.coalesce(Position.ticker, Trade.ticker).label("ticker"),
            Position.share_qty.label("position_shares"),
            Position.market_value.label("position_market_value"),
            Position.custodian.label("position_custodian"),
            Trade.share_qty.label("trade_shares"),
            Trade.market_value.label("trade_market_value"),
            Trade.custodian.label("trade_custodian"),
            Trade.trade_date,
            Position.report_date,
            Trade.settlement_date,
        )
        .select_from(
            outerjoin(
                Account,
                Position,
                and_(
                    Account.id == Position.account_id,
                    Position.report_date == report_date,
                ),
            )
        )
        .outerjoin(
            Trade,
            and_(
                Account.id == Trade.account_id,
                Trade.ticker == Position.ticker,
                Trade.settlement_date == report_date,
            ),
        )
        .where(or_(Position.account_id.isnot(None), Trade.account_id.isnot(None)))
    )

    results = db_session.execute(stmt).all()

    # Group by account and ticker to build reconciliation report
    reconciliation_report = {}

    for row in results:
        account_id = row.account_id
        ticker = row.ticker

        if account_id not in reconciliation_report:
            reconciliation_report[account_id] = {}

        # Determine reconciliation status and build coalesced report
        has_position = row.position_shares is not None
        has_trade = row.trade_shares is not None

        ticker_report = {
            "ticker": ticker,
            "has_position": has_position,
            "has_trade": has_trade,
            "position_shares": row.position_shares if has_position else None,
            "position_market_value": str(row.position_market_value)
            if has_position
            else None,
            "position_custodian": row.position_custodian if has_position else None,
            "trade_shares": row.trade_shares if has_trade else None,
            "trade_market_value": str(row.trade_market_value) if has_trade else None,
            "trade_custodian": row.trade_custodian if has_trade else None,
            "trade_date": row.trade_date.isoformat()
            if has_trade and row.trade_date
            else None,
        }

        # Reconciliation status
        if has_position and has_trade:
            ticker_report["reconciliation_status"] = "both_exist"
        elif has_position and not has_trade:
            ticker_report["reconciliation_status"] = "position_only"
        elif not has_position and has_trade:
            ticker_report["reconciliation_status"] = "trade_only"

        reconciliation_report[account_id][ticker] = ticker_report

    return jsonify(reconciliation_report)
